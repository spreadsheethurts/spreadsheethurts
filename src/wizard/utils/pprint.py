from typing import Optional

from rich.table import Table
from rich import print_json, get_console  # noqa: F401
from rich.console import Console
import pandas as pd


def print_dataframe(
    df: pd.DataFrame,
    title: Optional[str] = None,
    console: Console = None,
    show_header: bool = True,
):
    """Prints a DataFrame object in a rich table."""

    def markup_boolean(item) -> str:
        if item is False:
            return "[red]False[/]"

        return "[green]True[/]"

    def single_level_dataframe(df: pd.DataFrame) -> Table:
        assert df.columns.nlevels == 1, "Dataframe must have a single level index"

        table = Table(
            show_lines=True, show_header=show_header, highlight=True, title_style="bold"
        )
        table.add_column("Index", justify="center")

        for column in df.columns:
            table.add_column(str(column), justify="center")

        for idx, row in df.iterrows():
            # 1-based index
            table.add_row(
                str(idx + 1),
                *[
                    markup_boolean(item) if isinstance(item, bool) else item
                    for item in row
                ],
            )
        return table

    def multi_level_dataframe(df: pd.DataFrame) -> Table:
        if df.columns.nlevels == 1:
            return single_level_dataframe(df)

        table = Table(show_header=show_header, title_style="bold")
        subtables = []

        outermost = set(df.columns.get_level_values(0))
        for column in outermost:
            table.add_column(str(column), justify="center")
            subtables.append(multi_level_dataframe(df[column]))
        table.add_row(*subtables)
        return table

    table = multi_level_dataframe(df)
    table.title = title
    if not console:
        console = get_console()
    console.print(table, justify="center")


def print_series(
    series: pd.Series, title: Optional[str] = None, console: Console = None
):
    """Prints a Series object in a rich table."""
    print_dataframe(series.to_frame().T, title=title, console=console)
