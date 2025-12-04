from typing import Self
import uuid

from wizard.utils.google.client import APIRateMonitor
import pytest

DRIVE_FILES_API_V3_URL = "https://www.googleapis.com/drive/v3/files"
SPREADSHEET_URL_BASE = "https://sheets.googleapis.com/v4/spreadsheets"


class TestAPIRateMonitor:

    @pytest.fixture(scope="session")
    def monitor(self):
        return APIRateMonitor(60, 12000)

    def test_url_to_api_name(self, monitor: Self):
        uid = str(uuid.uuid4())
        drive_urls = [DRIVE_FILES_API_V3_URL, f"{DRIVE_FILES_API_V3_URL}/{uid}"]
        sheet_read_urls = [
            f"{SPREADSHEET_URL_BASE}/{uid}",
            f"{SPREADSHEET_URL_BASE}/{uid}/values:batchGet",
        ]
        sheet_write_urls = [
            f"{SPREADSHEET_URL_BASE}/{uid}/values:batchUpdate",
            f"{SPREADSHEET_URL_BASE}/{uid}:batchUpdate",
        ]

        for url in drive_urls:
            assert monitor._url_to_api_name(url) == "drive"
        for url in sheet_read_urls:
            assert monitor._url_to_api_name(url) == "sheet_read"
        for url in sheet_write_urls:
            assert monitor._url_to_api_name(url) == "sheet_write"
