from abc import ABC, abstractmethod
from typing import Any


class LeadSourceProvider(ABC):
    name: str

    @abstractmethod
    def search(self, *, query: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError
