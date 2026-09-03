from datetime import datetime
from app.connectors.base import BaseConnector, ConnectorError
from app.credentials import get_credential

LOG_FILE = "workflow_actions.log"


class WhatsAppConnector(BaseConnector):
    name = "whatsapp"
    actions = {"send_message": "Send a real WhatsApp message via Twilio's sandbox"}

    def execute(self, action: str, params: dict, working_data: dict) -> str:
        to = params.get("to", "")
        message = params.get("message", "")
        account_sid = get_credential("TWILIO_ACCOUNT_SID")
        auth_token = get_credential("TWILIO_AUTH_TOKEN")
        from_number = get_credential("TWILIO_WHATSAPP_FROM")

        if not (account_sid and auth_token and from_number):
            with open(LOG_FILE, "a") as f:
                f.write(f"[{datetime.utcnow().isoformat()}] [SIMULATED] WHATSAPP to={to} message='{message}'\n")
            return f"[SIMULATED] Would send WhatsApp to {to}: {message}"

        try:
            from twilio.rest import Client
            from twilio.base.exceptions import TwilioRestException
        except ImportError:
            raise ConnectorError("Missing package. Run: pip install twilio")

        try:
            client = Client(account_sid, auth_token)
            sent = client.messages.create(
                from_=from_number,
                to=to if to.startswith("whatsapp:") else f"whatsapp:{to}",
                body=message,
            )
        except TwilioRestException as e:
            raise ConnectorError(f"Twilio send failed: {e}")
        return f"WhatsApp sent to {to} (SID: {sent.sid})"
