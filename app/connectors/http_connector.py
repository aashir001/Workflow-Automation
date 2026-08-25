"""
HTTP connector - the one connector that is NOT simulated. It makes a
real outbound HTTP request to whatever URL a workflow step configures.
This is what lets the engine genuinely integrate with any external
API (a webhook.site test URL, a real Slack incoming webhook, an
internal microservice, etc.) - the same shape as UnifyApps' own
"API integrations" pillar.

Raises ConnectorError (not a bare exception) on network failure or a
non-2xx response, so the engine's retry logic can distinguish "this
is worth retrying" from "the workflow config itself is broken".
"""

import requests

from app.connectors.base import BaseConnector, ConnectorError


class HttpConnector(BaseConnector):
    name = "http"
    actions = {
        "post_json": "Send a real HTTP POST with a JSON body to a configured URL",
        "get": "Send a real HTTP GET to a configured URL",
    }

    def execute(self, action: str, params: dict, working_data: dict) -> str:
        url = params.get("url")
        if not url:
            raise ValueError("HTTP connector requires a 'url' param")

        timeout = float(params.get("timeout_seconds", 5))

        try:
            if action == "post_json":
                body = params.get("body", working_data)
                resp = requests.post(url, json=body, timeout=timeout)
            elif action == "get":
                resp = requests.get(url, timeout=timeout)
            else:
                raise ValueError(f"Unknown action '{action}' for connector '{self.name}'")
        except requests.RequestException as e:
            raise ConnectorError(f"HTTP request to {url} failed: {e}")

        if resp.status_code >= 400:
            raise ConnectorError(
                f"HTTP {action} to {url} returned status {resp.status_code}: "
                f"{resp.text[:200]}"
            )

        return f"{action} to {url} succeeded (status {resp.status_code})"
