from typing import Any, TYPE_CHECKING, Mapping, Optional, Literal
from .request import ValueRenderOption, ValueInputOption, JsonDict, DateTimeOption
from copy import deepcopy
import re


A1_ADDR_ROW_COL_RE = re.compile(r"([A-Za-z]+)?([1-9]\d*)?$")
MAGIC_NUMBER = 64
IntOrInf = int | float
DataType = int | float | bool | str

# TYPE_CHECKING is True only when type checking
if TYPE_CHECKING:
    from .client import Client, AsyncClient


def dispatch_data_to_type(
    data: DataType,
) -> Literal["numberValue", "stringValue", "boolValue", "formulaValue"]:
    if isinstance(data, (int, float)):
        return "numberValue"
    elif isinstance(data, bool):
        return "boolValue"
    elif isinstance(data, str):
        if data.startswith("="):
            return "formulaValue"
        return "stringValue"
    else:
        raise ValueError("Unsupported data type")


def range_name2sheet_name(range_name: str) -> str:
    return range_name.split("!")[0]


# These following three helper functions are sourced from gspread.utils(MIT License).
def absolute_range_name(sheet_name: str, range_name: Optional[str] = None) -> str:
    """Returns the absolute path of a specified range."""
    sheet_name = "'{}'".format(sheet_name.replace("'", "''"))

    if range_name:
        return "{}!{}".format(sheet_name, range_name)
    else:
        return sheet_name


def _a1_to_rowcol_unbounded(label: str) -> tuple[IntOrInf, IntOrInf]:
    """Translates a cell's address in A1 notation to a tuple of integers."""
    m = A1_ADDR_ROW_COL_RE.match(label)
    if m:
        column_label, row = m.groups()

        col: IntOrInf
        if column_label:
            col = 0
            for i, c in enumerate(reversed(column_label.upper())):
                col += (ord(c) - MAGIC_NUMBER) * (26**i)
        else:
            col = float("inf")

        if row:
            row = int(row)
        else:
            row = float("inf")
    else:
        raise ValueError(f"Incorrect label: {label}")

    return (row, col)


def a1_range_to_grid_range(name: str, sheet_id: Optional[int] = None) -> dict[str, int]:
    """Converts a range defined in A1 notation to a dict representing a `GridRange`_."""
    if "!" in name:
        name = name.split("!")[-1]
    start_label, _, end_label = name.partition(":")

    start_row_index, start_column_index = _a1_to_rowcol_unbounded(start_label)

    end_row_index, end_column_index = _a1_to_rowcol_unbounded(end_label or start_label)

    if start_row_index > end_row_index:
        start_row_index, end_row_index = end_row_index, start_row_index

    if start_column_index > end_column_index:
        start_column_index, end_column_index = end_column_index, start_column_index

    grid_range = {
        "startRowIndex": start_row_index - 1,
        "endRowIndex": end_row_index,
        "startColumnIndex": start_column_index - 1,
        "endColumnIndex": end_column_index,
    }

    filtered_grid_range: dict[str, int] = {
        key: value for (key, value) in grid_range.items() if isinstance(value, int)
    }

    if sheet_id is not None:
        filtered_grid_range["sheetId"] = sheet_id

    return filtered_grid_range


def update_spreadsheet_properties_request(locale, timezone) -> JsonDict:
    properties = {"locale": locale, "timeZone": timezone}
    return {
        "updateSpreadsheetProperties": {
            "properties": properties,
            "fields": "(locale,timeZone)",
        }
    }


def add_sheet_request(title: str, id: Optional[int] = None) -> JsonDict:
    """Return a addSheet request body.

    Reference: https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request#AddSheetRequest
    """
    properties = {"title": title}
    if id:
        properties["sheetId"] = id

    return {"addSheet": {"properties": properties}}


def repeat_cell_request(
    range_name: str, id: int, cell_format: Mapping[str, Any]
) -> JsonDict:
    """Return a repeatCell request body.

    Reference: https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/request#RepeatCellRequest
    """
    grid_range = a1_range_to_grid_range(range_name, id)
    return {
        "repeatCell": {
            "range": grid_range,
            "cell": {"userEnteredFormat": cell_format},
            "fields": "userEnteredFormat(%s)" % ",".join(cell_format.keys()),
        }
    }


class Spreadsheet:
    def __init__(
        self, uid, client: "Client", sheet_name_to_ids: Optional[dict[str, int]] = None
    ):
        self.client = client
        self.uid = uid
        self._sheet_name_to_ids: Optional[dict[str, int]] = sheet_name_to_ids

    def get_sheet_name_to_ids(self) -> dict[str, int]:
        response = self.client._get(self.uid, "sheets(properties(sheetId,title))")
        self._sheet_name_to_ids = {
            sheet["properties"]["title"]: sheet["properties"]["sheetId"]
            for sheet in response["sheets"]
        }

        return deepcopy(self._sheet_name_to_ids)

    def get_data_by_single_request(
        self, formula=False
    ) -> Mapping[str, list[list[Any]]]:
        """A single API call retrieves all sheet values from the spreadsheet.

        This method requires only one API call but returns a large JSON payload, sacrificing payload size for fewer API calls.
        """
        value_format = "userEnteredValue" if formula else "effectiveValue"
        response = self.client._get(
            self.uid,
            f"sheets(properties(sheetId,title),data.rowData(values({value_format})))",
        )
        sheets = {
            sheet["properties"]["title"]: [
                [list(column["effectiveValue"].values())[0]]
                for row in sheet["data"][0]["rowData"]
                for column in row["values"]
            ]
            for sheet in response["sheets"]
        }

        self._sheet_name_to_ids = {
            sheet["properties"]["title"]: sheet["properties"]["sheetId"]
            for sheet in response["sheets"]
        }

        return sheets

    def get_data_by_multiple_requests(
        self, formula=False
    ) -> Mapping[str, list[list[Any]]]:
        """Get all sheets values in the spreadsheet.

        Args:
            formula (bool):  Indicates whether to return user-entered formulas or calculated values. If cell A1 contains 0 and A2 contains the formula =A1+1,
                            then A2 will display =A1+1 when formula is true; otherwise, it will show 2.

        Returns:
            Mapping[str, list[list[Any]]]: A dictionary of sheet names to their values.

        The Sheet API call count is as follows:
        - 1 intrinsic Sheets Read API call to retrive metadata.
        - 1 intrinsic Sheets Read API call to obtain actual values.
        """

        # Get sheet titles
        titles = self.get_sheet_name_to_ids().keys()

        # Get datas
        ranges = [absolute_range_name(title) for title in titles]
        value_render_option = (
            ValueRenderOption.formula if formula else ValueRenderOption.unformatted
        )
        return self.client._values_batch_get(self.uid, ranges, value_render_option, DateTimeOption.serial_number)

    def update(
        self,
        range_values: Mapping[str, list[str] | list[list[str]]],
        range_format: Optional[Mapping[str, JsonDict]] = None,
        locale: Literal["en_US", "zh_CN"] = "en_US",
        timezone: Literal["America/New_York", "Asia/Shanghai"] = "America/New_York",
    ) -> None:
        """Update range values and formats.

        This method provides a batch approach for entering data into Google Sheets (multiple sheets or multiple cells within a sheet;
        see Google Sheets API Concepts for more details). It allows you to set the format of the range, just like in the Google Sheets UI.
        The method automatically creates new sheets if they don’t already exist and treats all values as strings, similar to manual entry.
        A common use case is setting the format to Text to prevent Google Sheets from automatically converting values to its internal data types.

        References:
        Range: https://developers.google.com/sheets/api/guides/concepts#cell
        Cell format: https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets/cells#CellFormat
        API Reference: https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/batchUpdate

        The API calls are as follows:
        - 1 intrinsic Sheets Write API call to batch update values.
        - 1 additional Sheets Write API call if new sheets need to be created or if formatting needs to be updated.
        - 1 additional Sheets Read API call if the internal state isn't updated. Spreadsheets created via `client.create` automatically update their
        state, avoiding this call.
        """
        # maintain internal state(sheet_name -> sheet_id)
        if not self._sheet_name_to_ids:
            self.get_sheet_name_to_ids()

        sheet_name2id, requests, id = (
            {},
            [update_spreadsheet_properties_request(locale, timezone)],
            len(self._sheet_name_to_ids),
        )
        for range_name in range_values.keys():
            sheet_name = range_name2sheet_name(range_name)
            if (
                sheet_name not in self._sheet_name_to_ids
                and sheet_name not in sheet_name2id
            ):
                id += 1
                sheet_name2id[sheet_name] = id
                requests.append(add_sheet_request(sheet_name, id))

        if range_format:
            for range_name, cell_format in range_format.items():
                id = sheet_name2id.get(
                    range_name2sheet_name(range_name)
                ) or self._sheet_name_to_ids.get(range_name2sheet_name(range_name))

                requests.append(
                    repeat_cell_request(
                        range_name,
                        id,
                        cell_format,
                    )
                )

        # commits possible cell format changes and new sheets
        if requests:
            self.client._batch_update(self.uid, requests)
            self._sheet_name_to_ids.update(sheet_name2id)

        self.client._values_batch_update(
            self.uid, range_values, ValueInputOption.user_entered
        )


class AsyncSpreadsheet:
    def __init__(
        self,
        uid,
        client: "AsyncClient",
        sheet_name_to_ids: Optional[dict[str, int]] = None,
    ):
        self.client = client
        self.uid = uid
        self._sheet_name_to_ids: Optional[dict[str, int]] = sheet_name_to_ids

    async def get_sheet_name_to_ids(self) -> dict[str, int]:
        """Asynchronous version of Spreadsheet.get_sheet_name_to_ids."""
        response = await self.client._get(self.uid, "sheets(properties(sheetId,title))")
        self._sheet_name_to_ids = {
            sheet["properties"]["title"]: sheet["properties"]["sheetId"]
            for sheet in response["sheets"]
        }

        return deepcopy(self._sheet_name_to_ids)

    async def get1(self, formula=False) -> Mapping[str, list[list[Any]]]:
        """Asynchronous version of Spreadsheet.get1."""
        value_format = "userEnteredValue" if formula else "effectiveValue"
        response = await self.client._get(
            self.uid,
            f"sheets(properties(sheetId,title),data.rowData(values({value_format})))",
        )
        sheets = {
            sheet["properties"]["title"]: [
                [list(column["effectiveValue"].values())[0]]
                for row in sheet["data"][0]["rowData"]
                for column in row["values"]
            ]
            for sheet in response["sheets"]
        }

        self._sheet_name_to_ids = {
            sheet["properties"]["title"]: sheet["properties"]["sheetId"]
            for sheet in response["sheets"]
        }

        return sheets

    async def get(self, formula=False) -> Mapping[str, list[list[Any]]]:
        """Asynchronous version of Spreadsheet.get."""

        # Get sheet titles
        titles = (await self.get_sheet_name_to_ids()).keys()

        # Get datas
        ranges = [absolute_range_name(title) for title in titles]
        value_render_option = (
            ValueRenderOption.formula if formula else ValueRenderOption.unformatted
        )
        response = await self.client._values_batch_get(
            self.uid, ranges, value_render_option
        )

        value_ranges = response["valueRanges"]
        sheets = {
            range_name2sheet_name(value_range["range"]): value_range["values"]
            for value_range in value_ranges
        }

        return sheets

    async def update(
        self,
        range_values: Mapping[str, list[str] | list[list[str]]],
        range_format: Optional[Mapping[str, JsonDict]] = None,
        locale: Literal["en_US", "zh_CN"] = "en_US",
        timezone: Literal["America/New_York", "Asia/Shanghai"] = "America/New_York",
    ) -> None:
        """Asynchronous version of Spreadsheet.update."""
        # maintain internal state(sheet_name -> sheet_id)
        if not self._sheet_name_to_ids:
            await self.get_sheet_name_to_ids()

        sheet_name2id, requests, id = (
            {},
            [update_spreadsheet_properties_request(locale, timezone)],
            len(self._sheet_name_to_ids),
        )
        for range_name in range_values.keys():
            sheet_name = range_name2sheet_name(range_name)
            if (
                sheet_name not in self._sheet_name_to_ids
                and sheet_name not in sheet_name2id
            ):
                id += 1
                sheet_name2id[sheet_name] = id
                requests.append(add_sheet_request(sheet_name, id))

        if range_format:
            for range_name, cell_format in range_format.items():
                if (id := sheet_name2id.get(range_name2sheet_name(range_name))) or (
                    id := self._sheet_name_to_ids.get(range_name2sheet_name(range_name))
                ):
                    requests.append(
                        repeat_cell_request(
                            range_name,
                            id,
                            cell_format,
                        )
                    )
                else:
                    raise ValueError(
                        f"range name {range_name} does not exist in the original spreadsheet or newly created sheets."
                    )

        # commits possible cell format changes and new sheets
        if requests:
            await self.client._batch_update(self.uid, requests)
            self._sheet_name_to_ids.update(sheet_name2id)

        await self.client._values_batch_update(
            self.uid, range_values, ValueInputOption.user_entered
        )
