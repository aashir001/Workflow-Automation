from datetime import datetime
import requests
from app.connectors.base import BaseConnector, ConnectorError
from app.credentials import get_credential

LOG_FILE = "workflow_actions.log"


class SlackConnector(BaseConnector):
    name = "slack"
    actions = {"post_message": "Post a real message to a Slack channel via an incoming webhook"}

    def execute(self, action: str, params: dict, working_data: dict) -> str:
        message = params.get("message", "")
        webhook_url = get_credential("SLACK_WEBHOOK_URL")
        if not webhook_url:
            with open(LOG_FILE, "a") as f:
                f.write(f"[{datetime.utcnow().isoformat()}] [SIMULATED] SLACK message='{message}'\n")
            return f"[SIMULATED] Would post: {message}"
        try:
            resp = requests.post(webhook_url, json={"text": message}, timeout=5)
        except requests.RequestException as e:
            raise ConnectorError(f"Slack webhook failed: {e}")
        if resp.status_code != 200:
            raise ConnectorError(f"Slack webhook returned {resp.status_code}: {resp.text[:200]}")
        return f"Posted to Slack: {message}"
