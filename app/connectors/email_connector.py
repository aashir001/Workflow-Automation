"""
Email connector - REAL, via SMTP (works with Gmail, Outlook, or any
SMTP provider).

For Gmail specifically:
  1. Enable 2-Step Verification on your Google account (required)
  2. Generate an "App Password" at https://myaccount.google.com/apppasswords
  3. Use your Gmail address as EMAIL_SMTP_USER and the generated
     16-character app password as EMAIL_SMTP_PASSWORD (NOT your real
     Gmail password - Google blocks that for security)

Credentials (via app/credentials.py):
  EMAIL_SMTP_HOST     (default: smtp.gmail.com)
  EMAIL_SMTP_PORT     (default: 587)
  EMAIL_SMTP_USER     (your email address)
  EMAIL_SMTP_PASSWORD (app password, not your real password)

Falls back to a clearly-labeled simulated log entry if credentials
aren't configured yet.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from app.connectors.base import BaseConnector, ConnectorError
from app.credentials import get_credential

LOG_FILE = "workflow_actions.log"


class EmailConnector(BaseConnector):
    name = "email"
    actions = {"send_email": "Send a real email via SMTP"}

    def execute(self, action: str, params: dict, working_data: dict) -> str:
        if action != "send_email":
            raise ValueError(f"Unknown action '{action}' for connector '{self.name}'")

        to = params.get("to", "")
        subject = params.get("subject", "Notification")
        body = params.get("body", "")

        smtp_user = get_credential("EMAIL_SMTP_USER")
        smtp_password = get_credential("EMAIL_SMTP_PASSWORD")
        smtp_host = get_credential("EMAIL_SMTP_HOST") or "smtp.gmail.com"
        smtp_port = int(get_credential("EMAIL_SMTP_PORT") or 587)

        if not (smtp_user and smtp_password):
            with open(LOG_FILE, "a") as f:
                f.write(
                    f"[{datetime.utcnow().isoformat()}] [SIMULATED] EMAIL "
                    f"to={to} subject='{subject}' (SMTP credentials not configured)\n"
                )
            return f"[SIMULATED - no SMTP credentials] Would email {to}: {subject}"

        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, [to], msg.as_string())
        except smtplib.SMTPException as e:
            raise ConnectorError(f"SMTP send failed: {e}")
        except OSError as e:
            raise ConnectorError(f"Could not connect to SMTP server: {e}")

        return f"Email sent to {to} (subject: {subject})"
