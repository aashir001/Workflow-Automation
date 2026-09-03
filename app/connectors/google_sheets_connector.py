import csv, json, os
from app.connectors.base import BaseConnector, ConnectorError
from app.credentials import get_credential

FALLBACK_CSV = "workflow_sheet.csv"


class GoogleSheetsConnector(BaseConnector):
    name = "google_sheets"
    actions = {"append_row": "Append a row to a real Google Sheet"}

    def execute(self, action: str, params: dict, working_data: dict) -> str:
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
            return f"[SIMULATED - wrote to {FALLBACK_CSV}] Row: {row}"

        try:
            import gspread
            from google.oauth2.service_account import Credentials
        except ImportError:
            raise ConnectorError("Missing packages. Run: pip install gspread google-auth")

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
