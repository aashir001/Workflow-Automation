from app.connectors.log_connector import LogConnector
from app.connectors.email_connector import EmailConnector
from app.connectors.slack_connector import SlackConnector
from app.connectors.sheet_connector import SheetConnector
from app.connectors.http_connector import HttpConnector
from app.connectors.sql_lookup_connector import SqlLookupConnector
from app.connectors.whatsapp_connector import WhatsAppConnector
from app.connectors.google_sheets_connector import GoogleSheetsConnector
from app.connectors.google_calendar_connector import GoogleCalendarConnector

CONNECTOR_REGISTRY = {
    "log": LogConnector(),
    "email": EmailConnector(),
    "slack": SlackConnector(),
    "sheet": SheetConnector(),
    "http": HttpConnector(),
    "sql_lookup": SqlLookupConnector(),
    "whatsapp": WhatsAppConnector(),
    "google_sheets": GoogleSheetsConnector(),
    "google_calendar": GoogleCalendarConnector(),
}


def get_connector(name: str):
    connector = CONNECTOR_REGISTRY.get(name)
    if connector is None:
        raise ValueError(f"Unknown connector '{name}'. Registered: {list(CONNECTOR_REGISTRY.keys())}")
    return connector


def list_connectors_and_actions() -> dict:
    return {name: conn.actions for name, conn in CONNECTOR_REGISTRY.items()}
