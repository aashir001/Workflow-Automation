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
        to = params.get("to", "")
        subject = params.get("subject", "Notification")
        body = params.get("body", "")

        smtp_user = get_credential("EMAIL_SMTP_USER")
        smtp_password = get_credential("EMAIL_SMTP_PASSWORD")
        smtp_host = get_credential("EMAIL_SMTP_HOST") or "smtp.gmail.com"
        smtp_port = int(get_credential("EMAIL_SMTP_PORT") or 587)

        if not (smtp_user and smtp_password):
            with open(LOG_FILE, "a") as f:
                f.write(f"[{datetime.utcnow().isoformat()}] [SIMULATED] EMAIL to={to} subject='{subject}'\n")
            return f"[SIMULATED] Would email {to}: {subject}"

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
        except (smtplib.SMTPException, OSError) as e:
            raise ConnectorError(f"SMTP send failed: {e}")
        return f"Email sent to {to} (subject: {subject})"
