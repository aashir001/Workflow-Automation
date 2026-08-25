"""Log connector - writes structured entries to a local log file.
The simplest possible connector; useful as a reference implementation
when writing a new one."""

import json
from datetime import datetime

from app.connectors.base import BaseConnector

LOG_FILE = "workflow_actions.log"


class LogConnector(BaseConnector):
    name = "log"
    actions = {"log_event": "Write a structured message to the local action log"}

    def execute(self, action: str, params: dict, working_data: dict) -> str:
        if action != "log_event":
            raise ValueError(f"Unknown action '{action}' for connector '{self.name}'")

        message = params.get("message", "")
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "message": message,
            "data": working_data,
        }
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
        return f"Logged: {message}"
