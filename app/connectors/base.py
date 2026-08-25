"""
Connector framework.

A "connector" is a self-contained integration with the outside world.
Each connector declares the actions it supports and implements them.
Adding a brand-new integration (say, a real Slack webhook, or a CRM
API) means writing ONE new file implementing BaseConnector and
registering it in CONNECTOR_REGISTRY below - nothing in the engine,
the models, or the API needs to change. This is the core "low-code
platform" design pattern: the platform grows by adding connectors as
data-driven plugins, not by branching engine code per integration.
"""

from abc import ABC, abstractmethod


class ConnectorError(Exception):
    """Raised by a connector when an action fails in an expected way
    (e.g. a webhook returns a non-2xx status). Distinguished from a
    bug so the engine's retry logic knows this is worth retrying."""
    pass


class BaseConnector(ABC):
    """
    Every connector must declare:
      - `name`      : unique key used in workflow step config
      - `actions`   : dict[str, str] mapping action_name -> short description
                      (used to populate the UI's action dropdown)
    And implement:
      - `execute(action, params, working_data) -> str`
        `working_data` is the current event data as it flows through the
        workflow (after any prior transforms). `params` are the step's
        configured parameters, with {field} placeholders already filled
        in from working_data by the engine before this is called.
        Must raise ConnectorError on a handled failure.
    """

    name: str
    actions: dict

    @abstractmethod
    def execute(self, action: str, params: dict, working_data: dict) -> str:
        ...
