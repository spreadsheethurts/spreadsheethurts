from itertools import product
from multiprocessing import shared_memory
import multiprocessing
from typing import Optional, Tuple, Callable
from math import ceil
import os
import time

import numpy as np
import pandas as pd
from rich.console import Console
from rich import get_console
from rich.panel import Panel
from rich.columns import Columns
from rich.box import DOUBLE_EDGE

from wizard.feature import (
    load_all_features,
    load_discard_features,
    load_general_features,
    load_weird_features,
)
from wizard.base import Serializable
from wizard.sheet import Sheet
from wizard.utils import print_series, print_dataframe, timeit, read_key, PoolHolder
from wizard.cell import Cell
from wizard.software import Software

# the default syscall 'spawn' will not work when shared memory is used
if multiprocessing.get_start_method() != "fork":
    multiprocessing.set_start_method("fork", force=True)


class ReportMeta(Serializable):
    """Data structure for storing the meta information."""

    equivalent: bool
    identical_encoding_count: int
    input_encoding: pd.Series
    cluster_sizes: list[int]
    cluster_samples_with_output_encoding: Optional[list[pd.DataFrame]]


class IndistinguishableItem(Serializable):
    """Data structure for managing multiple clusters of output encodings corresponding to the same input encoding.

    Args:
        ncluster: The number of clusters.
        cluster_sizes: The size of each cluster.
        samples: The input-output samples for each cluster.
    """

    ncluster: int
    cluster_sizes: list[int]
    samples: list[pd.DataFrame]


class Result(Serializable):
    """Result of the equivalence checker."""

    distinguishable: bool
    items: list[IndistinguishableItem]


class EquivalentClassChecker:
    """A class for assessing feature set quality through equivalence class checking.

    A high-quality feature set should distinguish input-output examples stored in a sheet, as evaluated by software.

    Input is encoded using the feature set, and output is encoded using the software's type system.The key idea is
    that equivalent input encodings should yield equivalent output encodings. Input encodings are equivalent if their
    vectors are identical, while output encodings are software-agnostic due to the type system.
    """

    def __init__(
        self,
        software: Software,
        sheet: Sheet,
        nsamples: int = 10,
        seed: Optional[int] = None,
        console: Optional[Console] = None,
    ) -> None:
        # Filter out rows where all cells have content None
        mask = ~sheet.sheet.map(lambda cell: cell.content is None).all(axis=1)
        self.sheet = Sheet(
            title=sheet.title,
            sheet=sheet.sheet[mask].reset_index(drop=True),
            parent=sheet.parent,
        )
        self.nsamples = nsamples if nsamples < sheet.nrows else sheet.nrows
        self.seed = seed
        if not console:
            console = get_console()

        self.console = console
        self.software = software

        self.shared_memory: Optional[shared_memory.SharedMemory] = None
        self.pool: Optional[PoolHolder] = None
        self.shared_array: Optional[np.ndarray] = None

        self.output_shms: list[shared_memory.SharedMemory] = []

        self.output_encoding: Optional[pd.DataFrame] = None
        self.discard_feature_names = set(
            load_discard_features(self.software.name).keys()
        )
        self.general_feature_names = set(
            load_general_features(self.software.name).keys()
        )

        self.weird_feature_names = set(load_weird_features(self.software.name).keys())

    def validate(self, parallel: bool = False) -> Result:
        """Validate the equivalence of the sheet based on the current feature set without generating a TUI report.

        If parallel is True, the input and output shared memory will be created and initialized. For memory safety, you
        should call close() when you are done.
        """
        return self.check(report=False, parallel=parallel)

    def _initiate_input_shared_resource(self):
        """Initialize the shared memory and process pool for parallel processing."""
        if not self.pool:
            self.pool = PoolHolder()
            # create and fill the shared memory with the sheet values
            # 1. create shared input array
            input_array = self.sheet.sheet.values[:, :-1]
            self.shared_memory = shared_memory.SharedMemory(
                create=True, size=input_array.nbytes
            )
            self.shared_array = np.ndarray(
                input_array.shape,
                dtype=input_array.dtype,
                buffer=self.shared_memory.buf,
            )
            np.copyto(self.shared_array, input_array)

    def _initiate_output_shared_resource(self, fsize: int):
        name = f"output_shm_{os.getpid()}_{time.time()}"
        shape = (self.sheet.nrows, (self.sheet.ncols - 1) * fsize)
        size = np.prod(shape) * np.dtype(bool).itemsize

        try:
            shm = shared_memory.SharedMemory(name=name, create=True, size=size)
            arr = np.ndarray(shape=shape, dtype=bool, buffer=shm.buf)
        except Exception:
            if shm:
                shm.close()
            try:
                shm.unlink()
            except FileNotFoundError:
                pass
            raise

        self.output_shms.append(shm)
        return shm, arr

    def check(self, report: bool = True, parallel: bool = False) -> Result:
        """Check the equivalence of the sheet based on the current feature set.

        Args:
            report: Whether to generate a TUI report for quick response.
            parallel: Whether to use parallel processing. Recommended for very large sheet.
        """

        if parallel:
            # lazy initialization
            self._initiate_input_shared_resource()
            (input_encoding, output_encoding) = self.encode_parallel()
        else:
            (input_encoding, output_encoding) = self.encode()

        # Categorize and identify identical input encodings.
        # 'uniq_input_encodings' is a list of unique tuples of input encoding.
        # 'category_codes' is a list of indices of 'uniqs' that each row of input encoding corresponds to.
        category_codes, uniq_input_encodings = pd.factorize(
            input_encoding.apply(lambda row: tuple(row), axis=1)
        )

        metas: list[ReportMeta] = []
        for category_code, uniq_input_encoding in enumerate(uniq_input_encodings):
            meta = self._equivalence_check(
                pd.Series(uniq_input_encoding, index=input_encoding.columns),
                output_encoding[category_codes == category_code],
            )
            if not meta.equivalent:
                # The linter will complain about using "== True", so use "== 1" instead.
                truth_input_encoding: pd.Series = meta.input_encoding[
                    meta.input_encoding == 1
                ]

                # skip this meta if at least one feature is discard feature while the rest are general features
                # or at least one feature is weird feature
                feature_names = set(truth_input_encoding.index.get_level_values(1))
                if (
                    feature_names
                    <= (self.discard_feature_names | self.general_feature_names)
                    and feature_names & self.discard_feature_names
                    or feature_names & self.weird_feature_names
                ):
                    continue

                metas.append(meta)

        if report:
            self.report(metas)

        distinguishable = len(metas) == 0
        items = []
        for meta in metas:
            samples = meta.cluster_samples_with_output_encoding
            for sample in samples:
                sample.drop(columns=self.software.types, inplace=True)
            items.append(
                IndistinguishableItem(
                    ncluster=len(meta.cluster_sizes),
                    cluster_sizes=meta.cluster_sizes,
                    samples=samples,
                )
            )

        return Result(distinguishable=distinguishable, items=items)

    def _equivalence_check(
        self, input_encoding: pd.Series, output_encoding: pd.DataFrame, sample=True
    ) -> ReportMeta:
        """Check the equivalence of output encodings.

        If the output encodings are not equivalent, make the best effort to determine the reason by sampling data.
        """

        # Clusters the output encodings based on the criteria defined by the software.
        # 1. Identical encodings are equivalent.
        # 2. Equivalence of output encodings is determined by the software.
        # 3. Merge those equivalent clusters together util no more equivalent clusters.
        # 4. Collect samples for each cluster to generate a report meta.

        codes, uniq_encodings = pd.factorize(
            output_encoding.apply(lambda row: tuple(row), axis=1)
        )

        clusters = [
            [(code, pd.Series(uniq, index=output_encoding.columns))]
            for code, uniq in enumerate(uniq_encodings)
        ]

        # merges the clusters with identical output encodings
        while True:
            changed = False
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    if self.software.is_encoding_eq(
                        clusters[i][0][1], clusters[j][0][1]
                    ):
                        changed = True
                        break
                if changed:
                    break

            if changed:
                clusters[i] += clusters[j]
                clusters.pop(j)
            else:
                break

        # If there is only one cluster, sampling is not necessary.
        if len(clusters) == 1:
            sample = False

        # collect samples for each cluster
        cluster_samples_with_output_encoding, cluster_counts = [], []
        if sample:
            # New sampling strategy: To better investigate rare cases, sample an equal
            # number of items from each cluster, irrespective of the cluster's size.
            n_clusters = len(clusters)
            samples_per_cluster = int(ceil(self.nsamples / n_clusters)) if n_clusters > 0 else 0

            for categoried_encodings in clusters:
                identical_cluster_samples_with_output_encoding = []
                
                # Calculate the total size of this final (merged) cluster to proportionally
                # distribute the `samples_per_cluster` among its constituent sub-clusters.
                final_cluster_indices = [output_encoding[codes == code].index for code, _ in categoried_encodings]
                final_cluster_size = sum(len(idx) for idx in final_cluster_indices)
                cluster_counts.append(final_cluster_size)

                for i, (code, categoried_encoding) in enumerate(categoried_encodings):
                    index = final_cluster_indices[i]
                    
                    if final_cluster_size > 0:
                        ratio = len(index) / final_cluster_size
                        nsample = int(ceil(samples_per_cluster * ratio))
                    else:
                        nsample = 0
                    
                    sample_df = self._sample(index, nsample=nsample)
                    
                    if not sample_df.empty:
                        encoding_frame = pd.concat(
                            [categoried_encoding] * len(sample_df), axis=1
                        ).T
                        encoding_frame.set_index(sample_df.index, inplace=True)
                        sample_with_output_encoding = pd.concat(
                            (sample_df, encoding_frame), axis=1
                        )
                        identical_cluster_samples_with_output_encoding.append(
                            sample_with_output_encoding
                        )

                if identical_cluster_samples_with_output_encoding:
                    cluster_samples_with_output_encoding.append(
                        pd.concat(identical_cluster_samples_with_output_encoding, axis=0)
                    )
                else:
                    empty_df_cols = self.sheet.sheet.columns.tolist() + output_encoding.columns.tolist()
                    cluster_samples_with_output_encoding.append(pd.DataFrame(columns=empty_df_cols))
        else:
            cluster_samples_with_output_encoding = None
            for categoried_encodings in clusters:
                cluster_count = 0
                for code, categoried_encoding in categoried_encodings:
                    cluster_count += (codes == code).sum()
                cluster_counts.append(cluster_count)

        meta = ReportMeta(
            equivalent=len(clusters) == 1,
            identical_encoding_count=len(output_encoding),
            input_encoding=input_encoding,
            cluster_sizes=cluster_counts,
            cluster_samples_with_output_encoding=cluster_samples_with_output_encoding,
        )
        return meta

    def _sample(self, index: pd.Index, nsample: int):
        """Samples nsample items from the indexed data."""
        if nsample > len(index):
            nsample = len(index)

        if nsample <= 0:
            return self.sheet.sheet.loc[pd.Index([])]

        sampled_indices = index.to_series().sample(nsample, random_state=self.seed)
        return self.sheet.sheet.loc[sampled_indices]

    def loop(self, parallel: bool = False):
        """Continue looping until the current feature set distinguish the sheet."""

        done = self.check(parallel=parallel).distinguishable
        while not done:
            self.console.clear()
            self.console.print(
                "[bold]Wait for feature updates. Press [cyan]q[/] to [cyan]exit[/]; any other key to [cyan]continue[/]...[/bold]",
                end="",
            )
            if read_key() == "q":
                self.console.print("\n[bold][Q]uit key pressed. Exiting...[/]")
                break

            done = self.check(parallel=parallel).distinguishable

        if done:
            self.console.print(
                rf"[bold]Congradulations! All {len(self.sheet.sheet)} inputs are divisible![/bold]"
            )

    @staticmethod
    def _encode_input_parallel(
        input_shm_name: str,
        input_dtype,
        input_shape,
        col: int,
        output_shm_name: str,
        output_dtype,
        output_shape,
        output_col_idx_in_flat_array: int,
        encoder: Callable[[Cell], bool],
    ):
        """Encode the entire column of the input array using the specified encoder."""
        try:
            input_shm = shared_memory.SharedMemory(name=input_shm_name)
            input_arr = np.ndarray(
                shape=input_shape, dtype=input_dtype, buffer=input_shm.buf
            )

            column_data = input_arr[:, col - 1]
            vectorized_encoder = np.vectorize(encoder)
            encoding = vectorized_encoder(column_data)

            output_shm = shared_memory.SharedMemory(name=output_shm_name)
            output_arr = np.ndarray(
                shape=output_shape, dtype=output_dtype, buffer=output_shm.buf
            )
            output_arr[:, output_col_idx_in_flat_array] = encoding
        except Exception:
            raise
        finally:
            if input_shm:
                input_shm.close()
            if output_shm:
                output_shm.close()

    def _encode_output(self) -> pd.DataFrame:
        """Encode the output cells utilizing the software's type system.

        The output encoder is rarely altered, thanks to the software's type system, and its encoding is cached,
        enhancing performance during subsequent fine-tuning of the input encoder.
        """
        if self.output_encoding is None:
            self.output_encoding = pd.DataFrame(
                [
                    self.software.encode_type(cell).T
                    for cell in self.sheet.sheet.iloc[:, -1]
                ],
            )
            self.output_encoding.reset_index(drop=True, inplace=True)
        return self.output_encoding

    def _refresh_features(self):
        self.discard_feature_names = set(
            load_discard_features(self.software.name).keys()
        )
        self.general_feature_names = set(
            load_general_features(self.software.name).keys()
        )
        self.weird_feature_names = set(load_weird_features(self.software.name).keys())
        return load_all_features(self.software.name)

    @timeit
    def encode(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Encode the cells using feature sets."""
        # Encodes inputs using feature sets and encodes outputs using the software type system.

        # 1. Encodings input cells
        features = self._refresh_features()
        # Establishes a multi-index using column indices(1-based) and feature names.
        input_columns = pd.MultiIndex.from_tuples(
            product(range(1, self.sheet.ncols), features.keys())
        )
        input_encoding = pd.DataFrame(columns=input_columns, dtype=bool)

        for col in range(1, self.sheet.ncols):
            for name, encoder in features.items():
                input_encoding[(col, name)] = self.sheet.sheet.iloc[:, col - 1].map(
                    encoder.evaluate_cell
                )

        return (input_encoding, self._encode_output())

    @timeit
    def encode_parallel(self) -> pd.DataFrame:
        """Encode the cells in parallel, with a granularity of columns."""
        features = self._refresh_features()
        self._initiate_input_shared_resource()
        shm, arr = self._initiate_output_shared_resource(len(features))
        columns = pd.MultiIndex.from_tuples(
            product(range(1, self.sheet.ncols), features.keys())
        )

        col_mapping = {(col, name): i for i, (col, name) in enumerate(columns)}
        input_tasks = []

        for col in range(1, self.sheet.ncols):
            for name, encoder in features.items():
                output_col_idx = col_mapping[(col, name)]
                task = self.pool.submit(
                    self._encode_input_parallel,
                    self.shared_memory.name,
                    self.shared_array.dtype,
                    self.shared_array.shape,
                    col,
                    shm.name,
                    arr.dtype,
                    arr.shape,
                    output_col_idx,
                    encoder.evaluate_cell,
                )
                input_tasks.append(task)

        for task in input_tasks:
            task.get()

        input_encoding = pd.DataFrame(arr, columns=columns, dtype=bool)
        return (input_encoding, self._encode_output())

    def report(self, metas: list[ReportMeta]):
        """Generates a TUI report based on the provided meta.

        The report includes the following information:
            1. Basic information about the sheet.
            2. Basic information about the indistinguishable items wrapped in meta.
            3. Indistinguishable input encodings.
            4. Samples from each cluster.
        """
        for i, meta in enumerate(metas, 1):
            self.console.clear()
            emph = lambda x: f"[underline][bold]{x}[/bold][/underline]"  # noqa: E731
            highlight = lambda x: f"[red][bold]{x}[/bold][/red]"  # noqa: E731

            if parent := self.sheet.parent:
                self.console.print(
                    emph(
                        f"Analyzing spreadsheet {highlight(parent.uid)} titled {highlight(parent.title)} with {highlight(self.sheet.nrows)} rows."
                    )
                )
            self.console.rule(
                title=emph(f"Report {i}/{len(metas)}"), style="bold white"
            )
            self.console.print(
                f"A total of {emph(meta.identical_encoding_count)} indivisible inputs, "
                f"forming {emph(len(meta.cluster_sizes))} clusters with counts {emph(meta.cluster_sizes)}."
            )

            features = (
                meta.input_encoding.index.get_level_values(1).drop_duplicates().tolist()
            )
            self.console.print(f"There are {len(features)} features: {features}")

            # The linter will complain about using "== True", so use "== 1" instead.
            truth_input_encoding: pd.Series = meta.input_encoding[
                meta.input_encoding == 1
            ]

            # only one truth input encoding
            if len(truth_input_encoding.index.get_level_values(0)) == 1:
                truth_input_encoding = truth_input_encoding.droplevel(0)
                panels = [
                    Panel(highlight(index), expand=True, box=DOUBLE_EDGE)
                    for index in truth_input_encoding.index
                ]
                self.console.rule(
                    emph("Truth feature for indistinguishable inputs"),
                    characters="═",
                    style="bold white",
                )
                self.console.print(Columns(panels), justify="center")
            # if no truth input is encoded, treat inputs as plain text
            elif len(truth_input_encoding) == 0:
                self.console.rule(
                    emph("Truth feature for indistinguishable inputs"),
                    characters="═",
                    style="bold white",
                )
                self.console.print(highlight("Text"), justify="center")
            else:
                print_series(
                    truth_input_encoding,
                    title="Truth of indistinguishable input encodings",
                    console=self.console,
                )

            self.console.rule(
                emph("Samples from each output cluster"),
                characters="═",
                style="bold white",
            )
            for i, cluster in enumerate(meta.cluster_samples_with_output_encoding):
                print_dataframe(
                    cluster,
                    title=f"Samples from cluster {i+1}",
                    console=self.console,
                )

            self.console.print("Press any key to continue...", end="")
            read_key()

    def close(self):
        if self.pool:
            self.shared_memory.close()

            for shm in self.output_shms:
                shm.close()

            self.pool.shutdown()
            self.pool = None
            self.shared_memory = None
            self.shared_array = None
            self.output_shms = []
