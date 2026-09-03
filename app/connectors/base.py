from abc import ABC, abstractmethod


class ConnectorError(Exception):
    pass


class BaseConnector(ABC):
    name: str
    actions: dict

    @abstractmethod
    def execute(self, action: str, params: dict, working_data: dict) -> str:
        ...
