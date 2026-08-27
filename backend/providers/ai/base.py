from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class ProviderUnavailable(Exception):
    pass


@dataclass
class CompletionResult:
    data: dict[str, Any]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    model: str = ""

    @property
    def credits(self) -> int:
        return max(int(self.prompt_tokens or 0) + int(self.completion_tokens or 0), 1)


class AIProvider(ABC):
    name: str

    @abstractmethod
    def complete(self, *, prompt: str, schema: dict[str, Any] | None = None) -> CompletionResult:
        raise NotImplementedError
