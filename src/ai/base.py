"""Base classes for AI model providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ModelProvider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    GROQ = "groq"


@dataclass
class ModelConfig:
    provider: ModelProvider
    model_name: str
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = 0.3
    max_tokens: int = 4096


@dataclass
class AIResponse:
    content: str
    model: str
    usage: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] | None = None


class BaseAIProvider(ABC):
    def __init__(self, config: ModelConfig):
        self.config = config

    @abstractmethod
    async def generate(self, prompt: str, system: str | None = None) -> AIResponse:
        pass

    @abstractmethod
    async def generate_structured(self, prompt: str, schema: dict, system: str | None = None) -> dict:
        pass
