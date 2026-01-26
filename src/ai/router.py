"""Intelligent model routing - use local models when possible, fall back to API."""

import asyncio
import logging
from typing import Any

from src.ai.base import BaseAIProvider, ModelConfig, ModelProvider, AIResponse
from src.ai.api_provider import create_provider
from src.ai.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)


class ModelRouter:
    """Route AI requests to the best available model.

    Priority chain:
    1. Ollama (local, free, private) - for general analysis
    2. Groq (fast, cheap API) - when local unavailable
    3. OpenAI/Anthropic (powerful, expensive) - for complex reasoning
    """

    def __init__(self):
        self.providers: dict[str, BaseAIProvider] = {}
        self.fallback_chain: list[str] = []
        self._health_cache: dict[str, bool] = {}

    def register(self, name: str, config: ModelConfig, priority: int = 0):
        """Register a provider with priority (lower = higher priority)."""
        provider = create_provider(config)
        self.providers[name] = provider
        self.fallback_chain.append((priority, name))
        self.fallback_chain.sort(key=lambda x: x[0])

    async def check_availability(self) -> dict[str, bool]:
        """Check which providers are currently available."""
        status = {}
        for name, provider in self.providers.items():
            if isinstance(provider, OllamaProvider):
                status[name] = await provider.check_health()
            else:
                status[name] = True  # Assume API providers are available
            self._health_cache[name] = status[name]
        return status

    async def generate(self, prompt: str, system: str | None = None, prefer: str | None = None) -> AIResponse:
        """Generate using best available model."""
        # Try preferred provider first
        if prefer and prefer in self.providers:
            try:
                return await self.providers[prefer].generate(prompt, system=system)
            except Exception as e:
                logger.warning(f"Preferred provider {prefer} failed: {e}")

        # Walk fallback chain
        for _, name in self.fallback_chain:
            if name == prefer:
                continue
            provider = self.providers[name]
            try:
                if isinstance(provider, OllamaProvider):
                    if not self._health_cache.get(name, True):
                        continue
                return await provider.generate(prompt, system=system)
            except Exception as e:
                logger.warning(f"Provider {name} failed: {e}")
                self._health_cache[name] = False
                continue

        raise RuntimeError("All AI providers unavailable")

    async def generate_structured(self, prompt: str, schema: dict, system: str | None = None, prefer: str | None = None) -> dict:
        """Generate structured output using best available model."""
        if prefer and prefer in self.providers:
            try:
                return await self.providers[prefer].generate_structured(prompt, schema, system=system)
            except Exception as e:
                logger.warning(f"Preferred provider {prefer} failed: {e}")

        for _, name in self.fallback_chain:
            if name == prefer:
                continue
            try:
                return await self.providers[name].generate_structured(prompt, schema, system=system)
            except Exception:
                continue

        raise RuntimeError("All AI providers unavailable for structured generation")


def create_default_router() -> ModelRouter:
    """Create router with default model configurations."""
    router = ModelRouter()

    # Priority 1: Local Ollama
    router.register("ollama", ModelConfig(
        provider=ModelProvider.OLLAMA,
        model_name="llama3.2",
        temperature=0.3,
    ), priority=1)

    # Priority 2: Groq (fast, cheap)
    router.register("groq", ModelConfig(
        provider=ModelProvider.GROQ,
        model_name="llama-3.1-70b-versatile",
        temperature=0.3,
    ), priority=2)

    # Priority 3: OpenAI
    router.register("openai", ModelConfig(
        provider=ModelProvider.OPENAI,
        model_name="gpt-4o-mini",
        temperature=0.3,
    ), priority=3)

    # Priority 4: Anthropic (most capable)
    router.register("anthropic", ModelConfig(
        provider=ModelProvider.ANTHROPIC,
        model_name="claude-sonnet-4-20250514",
        temperature=0.3,
    ), priority=4)

    return router
