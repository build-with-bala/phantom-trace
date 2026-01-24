"""Cloud API providers for AI analysis (OpenAI, Anthropic, Groq)."""

import json
import os

import aiohttp

from src.ai.base import BaseAIProvider, ModelConfig, ModelProvider, AIResponse


class OpenAIProvider(BaseAIProvider):
    """OpenAI / OpenAI-compatible API provider."""

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.api_key = config.api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = config.base_url or "https://api.openai.com/v1"

    async def generate(self, prompt: str, system: str | None = None) -> AIResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/chat/completions", json=payload, headers=headers) as resp:
                data = await resp.json()
                if resp.status != 200:
                    raise RuntimeError(f"OpenAI error: {data}")

                choice = data["choices"][0]["message"]["content"]
                return AIResponse(
                    content=choice,
                    model=self.config.model_name,
                    usage=data.get("usage", {}),
                    raw=data,
                )

    async def generate_structured(self, prompt: str, schema: dict, system: str | None = None) -> dict:
        structured_prompt = f"{prompt}\n\nRespond with valid JSON matching: {json.dumps(schema)}"
        response = await self.generate(structured_prompt, system=system)
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        return json.loads(content)


class AnthropicProvider(BaseAIProvider):
    """Anthropic Claude API provider."""

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.api_key = config.api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.base_url = config.base_url or "https://api.anthropic.com/v1"

    async def generate(self, prompt: str, system: str | None = None) -> AIResponse:
        payload = {
            "model": self.config.model_name,
            "max_tokens": self.config.max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/messages", json=payload, headers=headers) as resp:
                data = await resp.json()
                if resp.status != 200:
                    raise RuntimeError(f"Anthropic error: {data}")

                content = data["content"][0]["text"]
                return AIResponse(
                    content=content,
                    model=self.config.model_name,
                    usage={"input_tokens": data["usage"]["input_tokens"], "output_tokens": data["usage"]["output_tokens"]},
                    raw=data,
                )

    async def generate_structured(self, prompt: str, schema: dict, system: str | None = None) -> dict:
        structured_prompt = f"{prompt}\n\nRespond with valid JSON matching: {json.dumps(schema)}"
        response = await self.generate(structured_prompt, system=system)
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        return json.loads(content)


class GroqProvider(OpenAIProvider):
    """Groq API provider (OpenAI-compatible)."""

    def __init__(self, config: ModelConfig):
        config.base_url = config.base_url or "https://api.groq.com/openai/v1"
        config.api_key = config.api_key or os.getenv("GROQ_API_KEY", "")
        super().__init__(config)


def create_provider(config: ModelConfig) -> BaseAIProvider:
    """Factory for creating the right provider."""
    from src.ai.ollama_provider import OllamaProvider

    providers = {
        ModelProvider.OPENAI: OpenAIProvider,
        ModelProvider.ANTHROPIC: AnthropicProvider,
        ModelProvider.OLLAMA: OllamaProvider,
        ModelProvider.GROQ: GroqProvider,
    }
    provider_cls = providers.get(config.provider)
    if not provider_cls:
        raise ValueError(f"Unknown provider: {config.provider}")
    return provider_cls(config)
