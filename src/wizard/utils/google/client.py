from typing import Optional, Mapping, Any, Self, Literal
from datetime import datetime
from copy import deepcopy
import urllib3
import json
import asyncio
import threading
import time
import re
from collections import deque, defaultdict
import os

from pydantic import field_validator
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import AuthorizedSession
from google.auth.transport._aiohttp_requests import (
    AuthorizedSession as AsyncAuthorizedSession,
)
import backoff

from .spreadsheet import Spreadsheet, AsyncSpreadsheet
from .request import (
    RequestParam,
    ValueRenderOption,
    DateTimeOption,
    ValueInputOption,
    QuotaExceeded,
    APIError,
    JsonDict,
)

from wizard.base import Serializable

GOOGLE_SHEET_MIME_TYPE = "application/vnd.google-apps.spreadsheet"
DRIVE_FILES_API_V3_URL = "https://www.googleapis.com/drive/v3/files"

SPREADSHEET_URL_BASE = "https://sheets.googleapis.com/v4/spreadsheets"
SPREADSHEET_URL = SPREADSHEET_URL_BASE + "/{uid}"
SPREADSHEET_VALUES_BATCH_GET_URL = SPREADSHEET_URL_BASE + "/{uid}/values:batchGet"
SPREADSHEET_VALUES_BATCH_UPDATE_URL = SPREADSHEET_URL_BASE + "/{uid}/values:batchUpdate"
SPREADSHEET_BATCH_UPDATE_URL = SPREADSHEET_URL_BASE + "/{uid}:batchUpdate"


def sheet_name2range_name(sheet_name: str) -> str:
    return "'{}'".format(sheet_name.replace("'", "''"))


def range_name2sheet_name(range_name: str) -> str:
    return range_name.split("!")[0]


class SpreadsheetInfo(Serializable):
    id: str
    name: str
    createdTime: datetime
    modifiedTime: datetime

    @field_validator("createdTime", "modifiedTime", mode="before")
    def parse_time(cls, data: str) -> datetime:
        return datetime.fromisoformat(data)


def _create(title: str, folder_id: Optional[str] = None) -> RequestParam:
    json = {"name": title, "mimeType": GOOGLE_SHEET_MIME_TYPE}
    params = {"supportsAllDrives": "true"}

    if folder_id is not None:
        json["parents"] = [folder_id]

    return RequestParam(
        method="post", url=DRIVE_FILES_API_V3_URL, body=json, params=params
    )


def _remove(uid: str) -> RequestParam:
    url = f"{DRIVE_FILES_API_V3_URL}/{uid}"
    params = {"supportsAllDrives": "true"}
    return RequestParam(method="delete", url=url, params=params)


def _values_batch_get(
    uid: str,
    ranges: list[str],
    value_render_option: ValueRenderOption = ValueRenderOption.unformatted,
    datetime_option: DateTimeOption = DateTimeOption.formatted_string,
) -> RequestParam:
    params = {
        "ranges": ranges,
        "valueRenderOption": value_render_option,
        "dateTimeRenderOption": datetime_option,
    }

    return RequestParam(
        method="get",
        url=SPREADSHEET_VALUES_BATCH_GET_URL.format(uid=uid),
        params=params,
    )


def _batch_update(uid: str, requests: list[Any]) -> RequestParam:
    body = {
        "requests": requests,
        "includeSpreadsheetInResponse": "false",
        "responseIncludeGridData": "false",
    }
    return RequestParam(
        method="post",
        url=SPREADSHEET_BATCH_UPDATE_URL.format(uid=uid),
        body=body,
    )


def _values_batch_update(
    uid: str,
    range_values: Mapping[str, list[Any]],
    value_input_option: ValueInputOption = ValueInputOption.user_entered,
) -> RequestParam:
    body = {
        "valueInputOption": value_input_option,
        "data": [
            {"range": key, "values": values} for key, values in range_values.items()
        ],
        "includeValuesInResponse": "false",
    }
    return RequestParam(
        method="post",
        url=SPREADSHEET_VALUES_BATCH_UPDATE_URL.format(uid=uid),
        body=body,
    )


class Client:
    """A sync client with general capabilities: creating, listing, and removing Google Drive spreadsheet files, as well as retrieving and updating spreadsheet data."""

    def __init__(
        self,
        auth: Credentials,
        gzip: bool = True,
        sheet_rate_limit: int = 55,
        drive_rate_limit: int = 12000,
    ):
        self.auth = auth
        self.session = AuthorizedSession(self.auth)
        self.headers = (
            {
                "Accept-Encoding": "gzip",
                "User-Agent": "wizard (gzip)",
            }
            if gzip
            else {"User-Agent": "wizard"}
        )
        self.monitor = APIRateMonitor(sheet_rate_limit, drive_rate_limit)

    @classmethod
    def from_credential_path(cls, file: Optional[str] = None) -> Self:
        if file is None:
            try:
                file = os.environ["GOOGLE_CREDENTIAL_PATH"]
            except KeyError:
                raise ValueError(
                    "GOOGLE_CREDENTIAL_PATH environment variable is not set"
                )

        # Access Google Drive and Google Sheets
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
        creds = Credentials.from_service_account_file(file).with_scopes(scopes)
        return cls(creds)

    def request(
        self,
        param: RequestParam,
    ) -> Optional[JsonDict]:
        """Sends an HTTP request using the provided parameters and returns the response Json object if applicable.

        Returns:
            Mapping[str, Any]: The JSON response from the server.

        Raises:
            ValueError: If the response status is not OK (i.e., response.ok is False).
        """
        if param.headers:
            headers = deepcopy(self.headers)
            headers.update(param.headers)
        else:
            headers = self.headers

        self.monitor.record_request(param.url)
        response = self.session.request(
            method=param.method,
            url=param.url,
            data=param.data,
            json=param.body,
            params=param.params,
            headers=headers,
        )

        if response.ok:
            try:
                json = response.json()
                return json
            except Exception:
                return None
        else:
            error = response.json()["error"]
            # Status code 429/403 indicates that the quota has been exceeded.
            # Reference: https://cloud.google.com/docs/quotas/troubleshoot#exceeding-quota-values
            # Reference: https://developers.google.com/drive/api/guides/limits
            if error["code"] == 429 or error["code"] == 403:
                raise QuotaExceeded(error)
            else:
                raise APIError(error)

    def create(self, title: str, folder_id: Optional[str] = None) -> Spreadsheet:
        """Creates a new spreadsheet file with the specified title within a designated folder.

        Note: Two spreadsheets can have the same title, but each one has a unique UID that distinguishes it from others.
        """
        response = self.request(_create(title, folder_id))
        uid = response["id"]
        return Spreadsheet(uid, self, {"Sheet1": 0})

    def remove(self, uid: str):
        """Removes the spreadsheet with the specified uid."""
        self.request(_remove(uid))

    def open(self, uid: str) -> Spreadsheet:
        return Spreadsheet(uid, self)

    def _get(self, uid: str, fields: str):
        params = {"fields": fields}
        request = RequestParam(
            method="get",
            url=SPREADSHEET_URL.format(uid=uid),
            params=params,
        )
        response = self.request(request)
        return response

    def _values_batch_get(
        self,
        uid: str,
        ranges: list[str],
        value_render_option: ValueRenderOption = ValueRenderOption.unformatted,
        datetime_option: DateTimeOption = DateTimeOption.serial_number,
    ) -> Mapping[str, list[list[Any]]]:
        response = self.request(
            _values_batch_get(uid, ranges, value_render_option, datetime_option)
        )
        value_ranges = response["valueRanges"]
        sheets = {
            range_name2sheet_name(value_range["range"]): (
                value_range["values"] if "values" in value_range else [[]]
            )
            for value_range in value_ranges
        }
        return sheets

    def _batch_update(self, uid: str, requests: list[Any]):
        return self.request(_batch_update(uid, requests))

    def _values_batch_update(
        self,
        uid: str,
        range_values: Mapping[str, list[Any]],
        value_input_option: ValueInputOption = ValueInputOption.user_entered,
    ):
        return self.request(_values_batch_update(uid, range_values, value_input_option))

    def is_folder_exists(self, folder_id: str) -> bool:
        try:
            self.request(
                RequestParam(
                    method="get",
                    url=DRIVE_FILES_API_V3_URL + f"/{folder_id}",
                    params={"supportsAllDrives": "true"},
                )
            )
        except APIError as e:
            if e.error["code"] == 404:
                return False
            else:
                raise e
        return True

    def list_spreadsheets(
        self, folder_id: Optional[str] = None
    ) -> list[SpreadsheetInfo]:
        """List all spreadsheets in the specified folder (defaults to '/' if no folder is provided)."""
        files = []
        page_token = ""
        url = DRIVE_FILES_API_V3_URL

        query = f'mimeType="{GOOGLE_SHEET_MIME_TYPE}"'

        if folder_id:
            query += f' and parents in "{folder_id}"'

        params = {
            "q": query,
            "pageSize": 1000,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "fields": "kind,nextPageToken,files(id,name,createdTime,modifiedTime)",
        }

        while True:
            if page_token:
                params["pageToken"] = page_token

            json = self.request(RequestParam(method="get", url=url, params=params))
            files.extend(json["files"])
            page_token = json.get("nextPageToken", None)

            if page_token is None:
                break

        return [SpreadsheetInfo(**file) for file in files]

    def remove_all_spreadsheet_files(self, folder_id: Optional[str] = None):
        """Remove all spreadsheets in the specified folder (defaults to ‘/’ if no folder is provided)."""
        infos = self.list_spreadsheets(folder_id)
        for info in infos:
            self.remove(info.id)

    def remove_all_spreadsheets_except_folder(self, folder_id: str):
        """Remove all spreadsheets except those in the specified folder."""
        all_ids = set(map(lambda info: info.id, self.list_spreadsheets()))
        except_ids = set(map(lambda info: info.id, self.list_spreadsheets(folder_id)))
        for id in all_ids - except_ids:
            self.remove(id)

    def __del__(self):
        self.session.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self):
        self.session.close()


class BackOffClient(Client):
    @backoff.on_exception(backoff.expo, QuotaExceeded, max_time=120)
    def request(self, param: RequestParam) -> Mapping[str, Any]:
        return super().request(param)


class AsyncClient:
    """A async client with general capabilities: creating, listing, and removing Google Drive spreadsheet files, as well as retrieving and updating spreadsheet data."""

    def __init__(
        self,
        auth: Credentials,
        gzip: bool = True,
        sheet_rate_limit: int = 55,
        drive_rate_limit: int = 12000,
    ):
        self.auth = auth
        self.session = AsyncAuthorizedSession(self.auth)
        self.headers = (
            {
                "Accept-Encoding": "gzip",
                "User-Agent": "wizard (gzip)",
            }
            if gzip
            else {"User-Agent": "wizard"}
        )
        self.gzip = gzip
        self.monitor = APIRateMonitor(sheet_rate_limit, drive_rate_limit)

    async def request(self, param: RequestParam) -> Optional[JsonDict]:
        if param.headers:
            headers = deepcopy(self.headers)
            headers.update(param.headers)
        else:
            headers = self.headers

        await self.monitor.async_record_request(param.url)
        response = await self.session.request(
            method=param.method,
            url=param.url,
            data=param.data,
            json=param.body,
            params=param.params,
            headers=headers,
        )

        if "Content-Encoding" in response.headers:
            decoder = urllib3.response.MultiDecoder(
                response.headers["Content-Encoding"]
            )
            decompressed = decoder.decompress(await response.read())
            data = decompressed.decode("utf-8")
            js = json.loads(data)
        else:
            try:
                js = await response.json()
            except Exception:
                return None

        if response.ok:
            return js
        else:
            error = js["error"]
            # Status code 429/403 indicates that the quota has been exceeded.
            # Reference: https://cloud.google.com/docs/quotas/troubleshoot#exceeding-quota-values
            # Reference: https://developers.google.com/drive/api/guides/limits
            if error["code"] == 429 or error["code"] == 403:
                raise QuotaExceeded(error)
            else:
                raise APIError(error)

    async def create(
        self, title: str, folder_id: Optional[str] = None
    ) -> AsyncSpreadsheet:
        """Creates a new spreadsheet file with the specified title within a designated folder.

        Note: Two spreadsheets can have the same title, but each one has a unique uid that distinguishes it from others.
        """
        response = await self.request(_create(title, folder_id))
        uid = response["id"]
        return AsyncSpreadsheet(uid, self, {"Sheet1": 0})

    async def remove(self, uid: str):
        """Remove the spreadsheet with the specified uid."""
        await self.request(_remove(uid))

    async def open(self, uid: str) -> AsyncSpreadsheet:
        return AsyncSpreadsheet(uid, self)

    async def _get(self, uid: str, fields: str) -> Mapping[str, Any]:
        params = {"fields": fields}
        return await self.request(
            method="get",
            url=SPREADSHEET_URL.format(uid=uid),
            params=params,
        )

    async def _values_batch_get(
        self,
        uid: str,
        ranges: list[str],
        value_render_option: ValueRenderOption = ValueRenderOption.unformatted,
        datetime_option: DateTimeOption = DateTimeOption.formatted_string,
    ) -> Mapping[str, list[list[Any]]]:
        response = await self.request(
            _values_batch_get(uid, ranges, value_render_option, datetime_option)
        )
        value_ranges = response["valueRanges"]
        sheets = {
            range_name2sheet_name(value_range["range"]): value_range["values"]
            for value_range in value_ranges
        }
        return sheets

    async def _batch_update(self, uid: str, requests: list[Any]) -> Mapping[str, Any]:
        return await self.request(_batch_update(uid, requests))

    async def _values_batch_update(
        self,
        uid: str,
        range_values: Mapping[str, list[Any]],
        value_input_option: ValueInputOption = ValueInputOption.user_entered,
    ):
        return await self.request(
            _values_batch_update(uid, range_values, value_input_option)
        )

    async def list_spreadsheets(
        self, folder_id: Optional[str] = None
    ) -> list[SpreadsheetInfo]:
        """List all spreadsheets in the specified folder (defaults to '/' if no folder is provided)."""
        files = []
        page_token = ""
        url = DRIVE_FILES_API_V3_URL

        query = f'mimeType="{GOOGLE_SHEET_MIME_TYPE}"'

        if folder_id:
            query += f' and parents in "{folder_id}"'

        params = {
            "q": query,
            "pageSize": 1000,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
            "fields": "kind,nextPageToken,files(id,name,createdTime,modifiedTime)",
        }

        while True:
            if page_token:
                params["pageToken"] = page_token

            json = await self.request(
                RequestParam(method="get", url=url, params=params)
            )
            files.extend(json["files"])

            page_token = json.get("nextPageToken", None)

            if page_token is None:
                break

        return [SpreadsheetInfo(**file) for file in files]

    async def remove_all_spreadsheets(self, folder_id: Optional[str] = None):
        """Remove all spreadsheets in the specified folder (defaults to '/' if no folder is provided)."""
        infos = await self.list_spreadsheets(folder_id)
        tasks = [self.remove(info.id) for info in infos]
        await asyncio.gather(*tasks)

    async def remove_all_spreadsheets_except_folder(self, folder_id: str):
        """Remove all spreadsheets except those in the specified folder."""
        all_ids = set(map(lambda info: info.id, await self.list_spreadsheets()))
        except_ids = set(
            map(lambda info: info.id, await self.list_spreadsheets(folder_id))
        )
        tasks = [self.remove(id) for id in all_ids - except_ids]
        await asyncio.gather(*tasks)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type,
        exc_val,
        exc_tb,
    ) -> None:
        await self.close()

    async def close(self):
        await self.session.close()


class AsyncBackOffClient(AsyncClient):
    @backoff.on_exception(backoff.expo, QuotaExceeded, max_time=120)
    async def request(self, param):
        return await super().request(param)


APIName = Literal["drive", "sheet_read", "sheet_write"]


class APIRateMonitor:
    def __init__(
        self, sheet_rate_limit: int, drive_rate_limit: int, time_window: int = 60
    ):
        self.request_limits: dict[APIName, int] = {
            "drive": drive_rate_limit,
            "sheet_read": sheet_rate_limit,
            "sheet_write": sheet_rate_limit,
        }
        # sliding window, for real-time tracking
        self.request_timestamps: defaultdict[APIName, deque[float]] = defaultdict(deque)
        # for full history logging
        self.request_history: defaultdict[APIName, list[float]] = defaultdict(list)
        self.time_window = time_window
        self.sync_lock = threading.Lock()
        self.async_lock = asyncio.Lock()

    def record_request(self, url: str):
        """Synchronously record a request, and sleep until the next request can be made if necessary."""
        with self.sync_lock:
            if api_name := self._url_to_api_name(url):
                current_time = self._get_current_time()
                self._clean_old_requests(api_name, current_time)

                # Check if rate limit exceeded
                request_limit = self.request_limits[
                    api_name
                ]  # Default to 60 if not found
                if len(self.request_timestamps[api_name]) >= request_limit:
                    secs = self.time_window - (
                        current_time - self.request_timestamps[api_name][0]
                    )
                    print(f"Rate limit exceeded in monitor, sleeping {secs} seconds")
                    time.sleep(secs)
                else:
                    print(
                        f"{api_name} API: {len(self.request_timestamps[api_name])} requests / {request_limit} limit"
                    )

                # record the request timestamp
                self.request_timestamps[api_name].append(current_time)
                self.request_history[api_name].append(current_time)

    async def async_record_request(self, url: str):
        """Asynchronously record a request, and sleep until the next request can be made if necessary."""
        async with self.async_lock:
            if api_name := self._url_to_api_name(url):
                current_time = self._get_current_time()
                self._clean_old_requests(api_name, current_time)
                # Check if rate limit exceeded
                request_limit = self.request_limits[
                    api_name
                ]  # Default to 60 if not found
                if len(self.request_timestamps[api_name]) >= request_limit:
                    secs = self.time_window - (
                        current_time - self.request_timestamps[api_name][0]
                    )
                    print(f"Rate limit exceeded in monitor, sleeping {secs} seconds")
                    await asyncio.sleep(secs)
                else:
                    print(
                        f"{api_name} API: {len(self.request_timestamps[api_name])} requests / {request_limit} limit"
                    )

                # record the request timestamp
                current_time = self._get_current_time()
                self._clean_old_requests(api_name, current_time)
                self.request_timestamps[api_name].append(current_time)
                self.request_history[api_name].append(current_time)

    def _clean_old_requests(self, api_name: APIName, current_time: float = time.time()):
        """Remove timestamps that are not within the last time window from the request deque."""
        while (
            self.request_timestamps[api_name]
            and current_time - self.request_timestamps[api_name][0] > self.time_window
        ):
            self.request_timestamps[api_name].popleft()

    def _format_time(self, timestamp: float):
        """Helper to format the timestamp into a human-readable format."""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))

    def _url_to_api_name(self, url: str) -> Optional[APIName]:
        """Determines the API name based on the URL."""

        write_patterns = [
            re.compile(rf"^{SPREADSHEET_URL_BASE}/[^/]+/values:batchUpdate$"),
            re.compile(rf"^{SPREADSHEET_URL_BASE}/[^/]+:batchUpdate$"),
        ]
        read_patterns = [
            re.compile(rf"^{SPREADSHEET_URL_BASE}/[^/]+/values:batchGet$"),
            re.compile(rf"^{SPREADSHEET_URL_BASE}/[^/]+$"),
        ]
        if url.startswith(DRIVE_FILES_API_V3_URL):
            return "drive"
        elif any(pattern.fullmatch(url) for pattern in write_patterns):
            return "sheet_write"
        elif any(pattern.fullmatch(url) for pattern in read_patterns):
            return "sheet_read"
        return None

    def _get_current_time(self):
        """Return the current time in seconds."""
        return time.time()

    def get_request_count(self, api_name: APIName):
        """Get the number of requests made in the last time window."""
        return len(self.request_timestamps[api_name])

    def get_full_history(self):
        """Get the full request history for all APIs, with human-readable timestamps."""
        return {
            api: [self._format_time(ts) for ts in timestamps]
            for api, timestamps in self.request_history.items()
        }
