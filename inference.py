from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from google import genai
from google.genai import types

from config import Settings


@dataclass(frozen=True)
class InferenceResult:
    text: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class InferenceProvider:
    def generate(self, *, user_text: str, system_instruction: str) -> InferenceResult:  # pragma: no cover
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover
        return None


class GeminiProvider(InferenceProvider):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = genai.Client(api_key=settings.gemini_api_key)

    def generate(self, *, user_text: str, system_instruction: str) -> InferenceResult:
        model = self._settings.inference_model or self._settings.gemini_model
        resp = self._client.models.generate_content(
            model=model,
            contents=user_text,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=self._settings.gemini_temperature,
                max_output_tokens=self._settings.gemini_max_output_tokens,
            ),
        )
        usage = getattr(resp, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", None) if usage else None
        output_tokens = getattr(usage, "candidates_token_count", None) if usage else None
        total_tokens = getattr(usage, "total_token_count", None) if usage else None
        return InferenceResult(
            text=(resp.text or "").strip(),
            model=f"gemini:{model}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    def close(self) -> None:
        return None


class OpenRouterProvider(InferenceProvider):
    def __init__(self, settings: Settings) -> None:
        if not settings.openrouter_api_key:
            raise ValueError("OPENROUTER_API_KEY is required when inference_provider=openrouter")
        self._settings = settings
        self._client = httpx.Client(
            base_url=settings.openrouter_base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {settings.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )

    def generate(self, *, user_text: str, system_instruction: str) -> InferenceResult:
        model = self._settings.inference_model or self._settings.openrouter_model
        payload: dict[str, Any] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_text},
            ],
            "temperature": self._settings.openrouter_temperature,
            "max_tokens": self._settings.openrouter_max_output_tokens,
        }
        r = self._client.post("/chat/completions", json=payload)
        r.raise_for_status()
        data = r.json()

        choices = data.get("choices") or []
        message = (choices[0].get("message") if choices else {}) or {}
        content = message.get("content") or ""

        usage = data.get("usage") or {}
        input_tokens = usage.get("prompt_tokens")
        output_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")

        return InferenceResult(
            text=str(content).strip(),
            model=f"openrouter:{model}",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

    def close(self) -> None:
        self._client.close()


def build_provider(settings: Settings) -> InferenceProvider:
    provider = (settings.inference_provider or "gemini").strip().lower()
    if provider == "gemini":
        return GeminiProvider(settings)
    if provider == "openrouter":
        return OpenRouterProvider(settings)
    raise ValueError(f"Unsupported INFERENCE_PROVIDER: {settings.inference_provider!r}")

