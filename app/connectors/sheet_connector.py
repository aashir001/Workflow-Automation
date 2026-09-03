import csv
import os
from app.connectors.base import BaseConnector

SHEET_FILE = "workflow_sheet.csv"


class SheetConnector(BaseConnector):
    name = "sheet"
    actions = {"append_row": "Append a row of data to a local CSV file"}

    def execute(self, action: str, params: dict, working_data: dict) -> str:
        fields = params.get("fields") or list(working_data.keys())
        row = [str(working_data.get(f, "")) for f in fields]
        write_header = not os.path.exists(SHEET_FILE)
        with open(SHEET_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(fields)
            writer.writerow(row)
        return f"Appended row to {SHEET_FILE}: {row}"
