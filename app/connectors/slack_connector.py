"""
Slack connector - REAL, not simulated.

Uses a Slack "incoming webhook" URL (free, generated from
https://api.slack.com/apps -> your app -> Incoming Webhooks). The
webhook URL is read from the credential store (see app/credentials.py)
under the key SLACK_WEBHOOK_URL - set it via the Streamlit "Credentials"
tab, or as an environment variable of the same name.

Falls back to writing a log entry (clearly tagged [SIMULATED]) only if
no webhook URL is configured, so the app still runs end-to-end before
you've set anything up - but it will not silently pretend to be real
once a URL is present.
"""

from datetime import datetime
import requests

from app.connectors.base import BaseConnector, ConnectorError
from app.credentials import get_credential

LOG_FILE = "workflow_actions.log"


class SlackConnector(BaseConnector):
    name = "slack"
    actions = {
        "post_message": "Post a real message to a Slack channel via an incoming webhook"
    }

    def execute(self, action: str, params: dict, working_data: dict) -> str:
        if action != "post_message":
            raise ValueError(f"Unknown action '{action}' for connector '{self.name}'")

        message = params.get("message", "")
        webhook_url = get_credential("SLACK_WEBHOOK_URL")

        if not webhook_url:
            with open(LOG_FILE, "a") as f:
                f.write(
                    f"[{datetime.utcnow().isoformat()}] [SIMULATED] SLACK "
                    f"message='{message}' (no SLACK_WEBHOOK_URL configured)\n"
                )
            return f"[SIMULATED - no webhook configured] Would post: {message}"

        try:
            resp = requests.post(webhook_url, json={"text": message}, timeout=5)
        except requests.RequestException as e:
            raise ConnectorError(f"Slack webhook request failed: {e}")

        if resp.status_code != 200:
            raise ConnectorError(
                f"Slack webhook returned status {resp.status_code}: {resp.text[:200]}"
            )

        return f"Posted to Slack: {message}"
