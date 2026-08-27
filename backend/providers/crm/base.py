from abc import ABC, abstractmethod
from typing import Any


class CRMProvider(ABC):
    name: str

    @abstractmethod
    def upsert(self, *, object_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
