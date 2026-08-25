"""
WhatsApp connector - REAL, via Twilio's free WhatsApp sandbox.

Twilio's sandbox lets you send/receive real WhatsApp messages for free
during development, without Meta business verification. Setup:
  1. Sign up free at https://www.twilio.com/try-twilio
  2. Go to Messaging -> Try it out -> Send a WhatsApp message
  3. Follow the "join <sandbox-word>" instructions to link your own
     WhatsApp number to the sandbox
  4. Copy your Account SID and Auth Token from the Twilio console

Requires three credentials, stored via app/credentials.py:
  TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM
  (the sandbox's "from" number, formatted like "whatsapp:+14155238886")

Falls back to a clearly-labeled simulated log entry if credentials
aren't configured yet.
"""

from datetime import datetime

from app.connectors.base import BaseConnector, ConnectorError
from app.credentials import get_credential

LOG_FILE = "workflow_actions.log"


class WhatsAppConnector(BaseConnector):
    name = "whatsapp"
    actions = {
        "send_message": "Send a real WhatsApp message via Twilio's sandbox"
    }

    def execute(self, action: str, params: dict, working_data: dict) -> str:
        if action != "send_message":
            raise ValueError(f"Unknown action '{action}' for connector '{self.name}'")

        to = params.get("to", "")  # e.g. "whatsapp:+91XXXXXXXXXX"
        message = params.get("message", "")

        account_sid = get_credential("TWILIO_ACCOUNT_SID")
        auth_token = get_credential("TWILIO_AUTH_TOKEN")
        from_number = get_credential("TWILIO_WHATSAPP_FROM")

        if not (account_sid and auth_token and from_number):
            with open(LOG_FILE, "a") as f:
                f.write(
                    f"[{datetime.utcnow().isoformat()}] [SIMULATED] WHATSAPP "
                    f"to={to} message='{message}' (Twilio credentials not configured)\n"
                )
            return f"[SIMULATED - no Twilio credentials] Would send WhatsApp to {to}: {message}"

        try:
            from twilio.rest import Client
            from twilio.base.exceptions import TwilioRestException
        except ImportError:
            raise ConnectorError(
                "The 'twilio' package is not installed. Run: pip install twilio"
            )

        try:
            client = Client(account_sid, auth_token)
            sent = client.messages.create(
                from_=from_number,
                to=to if to.startswith("whatsapp:") else f"whatsapp:{to}",
                body=message,
            )
        except TwilioRestException as e:
            raise ConnectorError(f"Twilio WhatsApp send failed: {e}")

        return f"WhatsApp message sent to {to} (Twilio SID: {sent.sid})"
