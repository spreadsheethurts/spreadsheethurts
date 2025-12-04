from pathlib import Path
import shutil
from zipfile import ZipFile
import platform
import logging
from typing import Annotated

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from rich.logging import RichHandler
from rich.progress import track
import typer

os = platform.system()

if os == "Darwin":  # MacOS
    from appscript import app, k
    from math import ceil

    # Used only for type hinting.
    # The WorkBook and Excel object is created dynamically by the `appscript` module,
    # so the actual class cannot be used directly for type hints.
    class WorkBookMock:
        def file_format(self): ...

        def close(self, saving, saving_in): ...

        def full_name(self) -> str: ...

        def save(self): ...

    class ExcelMock:
        def open(self, path: str | list[str]): ...

        def quit(self): ...

        def workbooks(self) -> list[WorkBookMock]: ...

    # This should be a Singleton
    class ExcelFormulaEvaluator:
        # the system launch only one excel instance, be careful to use this class in multi-threading
        def __init__(
            self,
            working_directory: Path,
            max_batch_num: int,
            logger: logging.Logger,
            column: int = 2,  # one-based
        ) -> None:
            self.logger = logger
            self.column = column

            self.logger.info("Starting Excel...")
            self.excel: ExcelMock = app("Microsoft Excel")
            self.excel.activate()
            self.max_batch_num = max_batch_num
            self.working_directory = working_directory
            # Excel on macOS has strict permission controls; opening a new workbook will prompt for permission even if the file is writable.
            # As a workaround, we create several empty workbooks initially and reuse their paths, since Excel will not ask for permission
            # when opening the same files.
            self.empty_book_paths = [
                self.working_directory / f"empty_{i}.xlsx" for i in range(max_batch_num)
            ]

            self._delete_empty_workbooks(self.working_directory, "empty_*.xlsx")
            self.make_empty_workbooks(self.empty_book_paths)

        def _delete_empty_workbooks(self, directory: Path, pattern: str):
            for path in directory.glob(pattern):
                path.unlink(missing_ok=True)

        def make_empty_workbooks(self, paths: list[Path]):
            """Create empty workbooks at the specified paths."""

            for _ in range(len(paths)):
                self.excel.make(new=k.workbook)

            for path, workbook in zip(paths, self.excel.workbooks()):
                workbook.save(
                    in_=str(path),
                    as_=workbook.file_format(),
                )

            for workbook in self.excel.workbooks():
                workbook.close()

        def _evaluate(self, paths: list[Path] | Path):
            file_mapping: dict[Path, Path] = {
                empty: original for original, empty in zip(paths, self.empty_book_paths)
            }
            # Rename the original files to the empty files.
            for empty, original in file_mapping.items():
                original.rename(empty)
            # Open the empty files to avoid permission prompts from Excel.
            self.excel.open([str(path) for path in file_mapping.keys()])

            for workbook in self.excel.workbooks():
                # triggers the type conversion using the "Text to Columns" command
                for worksheet in workbook.sheets():
                    # The column index in the Columns function is one-based
                    column = worksheet.columns[self.column]
                    column.text_to_columns(
                        destination=column.cells[1],
                        data_type=k.delimited,
                        text_qualifier=k.text_qualifier_none,
                    )

                # Save the workbook to the original file paths to avoid overwrite prompts for permission.
                workbook.save(
                    in_=str(file_mapping[Path(workbook.full_name())]),
                    as_=workbook.file_format(),
                )

            for workbook in self.excel.workbooks():
                workbook.close()

        def evaluate(self, paths: list[Path] | Path):
            """Evaluate the formulas to get results in the Excel file.

            Excel on macOS has strict permission controls; opening a new workbook will prompt for permission even if the file is
            writable. Additionally, Excel will ask for permission when overwriting an existing file. As a workaround, we create
            several empty workbooks initially and reuse their paths. After evaluation, we move the evaluated results back to the
            original files. This approach addresses the permission granting issues when automating Excel on macOS.
            """

            paths = [paths] if isinstance(paths, Path) else paths
            paths = [path.absolute() for path in paths]
            round = ceil(len(paths) / self.max_batch_num)

            self.logger.info(f"Evaluating {len(paths)} files in {round} rounds.")
            for i in track(range(round), description="Evaluating files..."):
                start = i * self.max_batch_num
                end = min((i + 1) * self.max_batch_num, len(paths))
                self._evaluate(paths[start:end])

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            self.excel.quit()

elif os == "Windows":  # Windows
    from typing import Self
    import win32com.client as win32

    # Used only for type hinting.
    # The WorkSheet, WorkBook, and Excel object is created dynamically by the 'pywin32' module,
    # so the actual class cannot be used directly for type hints.
    # These method signatures and fields are not accurate in all cases, but they are sufficient for type hinting.
    class Range:
        # Reference from https://learn.microsoft.com/en-us/office/vba/api/excel.range.texttocolumns
        def TextToColumns(
            self,
            dest: Self,
            dt: int = 1,
            qual: int = -4142,
            Tab=False,
            Semicolon=False,
            Comma=False,
            Space=False,
            Other=False,
        ): ...

        def Cells(self, row: int) -> Self: ...

    class WorkSheetMock:
        def Columns(self, idx: int) -> Range:
            """Return the range corresponding to the index(one-based)."""

    class WorkBookMock:
        def Open(self, path: str) -> Self: ...

        def Save(self): ...

        def Close(self): ...

        @property
        def Worksheets(self) -> list[WorkSheetMock]: ...

    class ExcelMock:
        Visible: bool
        Workbooks: WorkBookMock

        def Quit(self): ...

    # This should be a Singleton
    class ExcelFormulaEvaluator:
        def __init__(
            self,
            working_directory: Path,
            max_batch_num: int,
            logger: logging.Logger,
            column: int = 2,
        ) -> None:
            self.logger = logger
            self.column = column

            self.logger.info("Starting Excel...")
            self.excel: ExcelMock = win32.Dispatch("Excel.Application")
            self.excel.Visible = True

        def evaluate(self, paths: list[Path] | Path):
            """Evaluate the formulas to get results in the Excel file."""

            # Excel on Windows has less strict requirements for saving files,
            # so the evaluated results can be saved directly to the original file.
            paths = [paths] if isinstance(paths, Path) else paths

            self.logger.info(f"Evaluating {len(paths)} files.")

            for path in track(paths, description="Evaluating files..."):
                wb = self.excel.Workbooks.Open(path.absolute())

                for ws in wb.Worksheets:
                    column: Range = ws.Columns(self.column)
                    column.TextToColumns(
                        column.Cells(1),
                        1,
                        -4142,
                        Tab=False,
                        Semicolon=False,
                        Comma=False,
                        Space=False,
                        Other=False,
                    )

                wb.Save()
                wb.Close()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.excel.Quit()

else:
    raise ValueError(f"Unsupported OS: {os}, only Windows and MacOS are supported.")


def main(
    column: Annotated[
        int, typer.Option("--column", "-c", help="The column to evaluate (one based).")
    ] = 2,
    host: Annotated[
        str, typer.Option("--host", "-h", help="The host to bind to.")
    ] = "0.0.0.0",
    port: Annotated[
        int, typer.Option("--port", "-p", help="The port to bind to.")
    ] = 8000,
    directory: Annotated[
        str,
        typer.Option(
            "--directory",
            "-d",
            help="The directory to store the evaluated files.",
        ),
    ] = "server_datasets",
    max_batch_num: Annotated[
        int,
        typer.Option(
            "--max-batch-num",
            "-m",
            help="The maximum number of files to evaluate in a batch.",
        ),
    ] = 20,
):
    """A web server dedicated to evaluating Excel files."""

    logging.basicConfig(
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True)],
    )

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    wd = Path.cwd() / directory
    wd.mkdir(exist_ok=True)
    # singleton evaluator
    evaluator = ExcelFormulaEvaluator(wd, max_batch_num, logger, column=column)
    server_app = FastAPI()

    @server_app.get("/")
    async def root():
        return {"message": "Excel Server"}

    @server_app.post("/evaluate")
    async def evaluate(file: UploadFile = File(...)):
        """Evaluate the formulas in the uploaded Excel file and return the evaluated file."""
        path: Path = wd / file.filename
        with path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        evaluator.evaluate(path)

        return FileResponse(path, filename=file.filename)

    @server_app.post("/evaluate_batch")
    async def evaluate_batch(files: list[UploadFile] = File(...)):
        """Evaluate a batch of Excel files and return a zip file containing the evaluated files."""
        paths = [wd / file.filename for file in files]
        for path, file in zip(paths, files):
            with open(path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

        evaluator.evaluate(paths)
        zipped_basename = "evaluated_files.zip"
        zipped_path = wd / zipped_basename

        with ZipFile(zipped_path, "w") as zipf:
            for path in paths:
                zipf.write(path, arcname=path.name)

        return FileResponse(
            zipped_path, media_type="application/zip", filename=zipped_basename
        )

    import uvicorn

    uvicorn.run(server_app, host=host, port=port)


if __name__ == "__main__":
    typer.run(main)
