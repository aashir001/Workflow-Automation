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
                resp = requests.post(url, json=params.get("body", working_data), timeout=timeout)
            elif action == "get":
                resp = requests.get(url, timeout=timeout)
            else:
                raise ValueError(f"Unknown action '{action}'")
        except requests.RequestException as e:
            raise ConnectorError(f"HTTP request to {url} failed: {e}")
        if resp.status_code >= 400:
            raise ConnectorError(f"HTTP {action} to {url} returned {resp.status_code}: {resp.text[:200]}")
        return f"{action} to {url} succeeded (status {resp.status_code})"
