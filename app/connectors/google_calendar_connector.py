import json
from datetime import datetime, timedelta
from app.connectors.base import BaseConnector, ConnectorError
from app.credentials import get_credential

LOG_FILE = "workflow_actions.log"


class GoogleCalendarConnector(BaseConnector):
    name = "google_calendar"
    actions = {"create_event": "Create a real event on a Google Calendar"}

    def execute(self, action: str, params: dict, working_data: dict) -> str:
        calendar_id = params.get("calendar_id")
        summary = params.get("summary", "Workflow event")
        duration_minutes = int(params.get("duration_minutes", 30))
        service_account_json = get_credential("GOOGLE_SERVICE_ACCOUNT_JSON")

        if not (service_account_json and calendar_id):
            with open(LOG_FILE, "a") as f:
                f.write(f"[{datetime.utcnow().isoformat()}] [SIMULATED] CALENDAR summary='{summary}'\n")
            return f"[SIMULATED] Would create event: {summary}"

        try:
            from googleapiclient.discovery import build
            from google.oauth2.service_account import Credentials
        except ImportError:
            raise ConnectorError("Missing packages. Run: pip install google-api-python-client google-auth")

        try:
            creds_dict = json.loads(service_account_json)
            scopes = ["https://www.googleapis.com/auth/calendar"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            service = build("calendar", "v3", credentials=creds)
            start = datetime.utcnow()
            end = start + timedelta(minutes=duration_minutes)
            event = {"summary": summary, "start": {"dateTime": start.isoformat() + "Z"},
                     "end": {"dateTime": end.isoformat() + "Z"}}
            created = service.events().insert(calendarId=calendar_id, body=event).execute()
        except Exception as e:
            raise ConnectorError(f"Google Calendar event creation failed: {e}")
        return f"Created calendar event: {summary} ({created.get('htmlLink', 'no link')})"
