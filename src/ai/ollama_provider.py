"""Ollama local model provider for offline/private OSINT analysis."""

import json
import aiohttp

from src.ai.base import BaseAIProvider, ModelConfig, AIResponse


class OllamaProvider(BaseAIProvider):
    """Connect to local Ollama instance for private AI inference."""

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.base_url = config.base_url or "http://localhost:11434"

    async def generate(self, prompt: str, system: str | None = None) -> AIResponse:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/chat", json=payload) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    raise RuntimeError(f"Ollama error {resp.status}: {error}")

                data = await resp.json()
                return AIResponse(
                    content=data["message"]["content"],
                    model=self.config.model_name,
                    usage={
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                    },
                    raw=data,
                )

    async def generate_structured(self, prompt: str, schema: dict, system: str | None = None) -> dict:
        structured_prompt = f"""{prompt}

Respond with valid JSON matching this schema:
{json.dumps(schema, indent=2)}

JSON response:"""

        response = await self.generate(structured_prompt, system=system)

        # Extract JSON from response
        content = response.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return json.loads(content)

    async def check_health(self) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as resp:
                    return resp.status == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return [m["name"] for m in data.get("models", [])]
        except Exception:
            pass
        return []
