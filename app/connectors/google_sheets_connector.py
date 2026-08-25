"""
Google Sheets connector - REAL, via a Google service account.

Setup:
  1. Go to https://console.cloud.google.com -> create a project (free)
  2. Enable the "Google Sheets API" for that project
  3. Create a Service Account (IAM & Admin -> Service Accounts)
  4. Create a JSON key for it and download it
  5. Open your target Google Sheet and "Share" it with the service
     account's email address (looks like xxx@xxx.iam.gserviceaccount.com)
     giving it Editor access
  6. Store the JSON key's file contents as the GOOGLE_SERVICE_ACCOUNT_JSON
     credential (paste the whole JSON file content as the value)

Requires the `gspread` and `google-auth` packages.
Falls back to writing to a local CSV file if the credential isn't set,
so the app still runs before this is configured.
"""

import csv
import json
import os
from datetime import datetime

from app.connectors.base import BaseConnector, ConnectorError
from app.credentials import get_credential

FALLBACK_CSV = "workflow_sheet.csv"


class GoogleSheetsConnector(BaseConnector):
    name = "google_sheets"
    actions = {"append_row": "Append a row to a real Google Sheet"}

    def execute(self, action: str, params: dict, working_data: dict) -> str:
        if action != "append_row":
            raise ValueError(f"Unknown action '{action}' for connector '{self.name}'")

        fields = params.get("fields") or list(working_data.keys())
        row = [str(working_data.get(f, "")) for f in fields]
        spreadsheet_id = params.get("spreadsheet_id")
        worksheet_name = params.get("worksheet_name", "Sheet1")

        service_account_json = get_credential("GOOGLE_SERVICE_ACCOUNT_JSON")

        if not (service_account_json and spreadsheet_id):
            write_header = not os.path.exists(FALLBACK_CSV)
            with open(FALLBACK_CSV, "a", newline="") as f:
                writer = csv.writer(f)
                if write_header:
                    writer.writerow(fields)
                writer.writerow(row)
            return (
                f"[SIMULATED - Google Sheets not configured, wrote to "
                f"{FALLBACK_CSV} instead] Row: {row}"
            )

        try:
            import gspread
            from google.oauth2.service_account import Credentials
        except ImportError:
            raise ConnectorError(
                "Missing packages. Run: pip install gspread google-auth"
            )

        try:
            creds_dict = json.loads(service_account_json)
            scopes = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            client = gspread.authorize(creds)
            sheet = client.open_by_key(spreadsheet_id).worksheet(worksheet_name)
            sheet.append_row(row)
        except Exception as e:
            raise ConnectorError(f"Google Sheets append failed: {e}")

        return f"Appended row to Google Sheet ({spreadsheet_id}): {row}"
