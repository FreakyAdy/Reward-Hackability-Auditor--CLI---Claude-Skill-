"""Unified LLM client abstraction for dynamic fuzzing.

Supports:
- Ollama (local, free, default) — raw HTTP to localhost:11434
- OpenAI-compatible APIs (--frontier) — via openai package
- Anthropic (--frontier) — via anthropic package

All backends are optional dependencies — ratctl core stays light.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default models per backend
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:7b"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-20250514"


@dataclass
class LLMResponse:
    """Response from an LLM backend."""

    content: str
    model: str
    tokens_used: int = 0


class LLMClient(ABC):
    """Abstract LLM client."""

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Generate a completion."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is ready to use."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """The model identifier being used."""


class OllamaClient(LLMClient):
    """Ollama local LLM client — uses raw HTTP, no external deps."""

    def __init__(self, model: str | None = None, base_url: str | None = None):
        self._model = model or os.environ.get("RATCTL_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
        self._base_url = base_url or os.environ.get("RATCTL_OLLAMA_URL", "http://localhost:11434")

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            req = urllib.request.Request(
                f"{self._base_url}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                models = [m.get("name", "") for m in data.get("models", [])]
                # Check if exact model or base name matches
                return any(
                    self._model in m or m.startswith(self._model.split(":")[0])
                    for m in models
                )
        except (urllib.error.URLError, OSError, json.JSONDecodeError):
            return False

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Generate via Ollama's /api/chat endpoint."""
        payload = json.dumps({
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {
                "temperature": 0.7,
                "num_predict": 4096,
            },
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self._base_url}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                message = data.get("message", {})
                return LLMResponse(
                    content=message.get("content", ""),
                    model=self._model,
                    tokens_used=data.get("eval_count", 0),
                )
        except (urllib.error.URLError, OSError) as e:
            raise ConnectionError(f"Ollama request failed: {e}") from e


class OpenAIClient(LLMClient):
    """OpenAI-compatible API client."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self._model = model or os.environ.get("RATCTL_OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        self._api_key = api_key or os.environ.get("RATCTL_OPENAI_API_KEY", "")

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package required for --frontier mode. "
                "Install with: pip install ratctl[frontier]"
            )

        client = openai.OpenAI(api_key=self._api_key)
        response = client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=4096,
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            model=self._model,
            tokens_used=response.usage.total_tokens if response.usage else 0,
        )


class AnthropicClient(LLMClient):
    """Anthropic API client."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self._model = model or os.environ.get("RATCTL_ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
        self._api_key = api_key or os.environ.get("RATCTL_ANTHROPIC_API_KEY", "")

    @property
    def model_name(self) -> str:
        return self._model

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package required for --frontier mode with Anthropic. "
                "Install with: pip install ratctl[frontier]"
            )

        client = anthropic.Anthropic(api_key=self._api_key)
        response = client.messages.create(
            model=self._model,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.7,
            max_tokens=4096,
        )
        content = response.content[0].text if response.content else ""
        return LLMResponse(
            content=content,
            model=self._model,
            tokens_used=response.usage.input_tokens + response.usage.output_tokens
            if response.usage else 0,
        )


def get_client(
    frontier: bool = False,
    model: str | None = None,
) -> LLMClient:
    """Get the best available LLM client.

    Priority:
    1. If --frontier: try OpenAI, then Anthropic
    2. Otherwise: try Ollama (local)

    Args:
        frontier: Use paid API instead of local.
        model: Override the default model.

    Returns:
        An LLMClient instance.

    Raises:
        RuntimeError: If no backend is available.
    """
    if frontier:
        # Try OpenAI first
        openai_client = OpenAIClient(model=model)
        if openai_client.is_available():
            logger.info("Using OpenAI backend: %s", openai_client.model_name)
            return openai_client

        # Try Anthropic
        anthropic_client = AnthropicClient(model=model)
        if anthropic_client.is_available():
            logger.info("Using Anthropic backend: %s", anthropic_client.model_name)
            return anthropic_client

        raise RuntimeError(
            "No frontier LLM backend available. Set RATCTL_OPENAI_API_KEY or "
            "RATCTL_ANTHROPIC_API_KEY environment variable."
        )

    # Default: try Ollama
    ollama_client = OllamaClient(model=model)
    if ollama_client.is_available():
        logger.info("Using Ollama backend: %s", ollama_client.model_name)
        return ollama_client

    raise RuntimeError(
        "No LLM backend available. Install and start Ollama "
        "(https://ollama.com) or use --frontier with an API key.\n"
        f"Tried: Ollama at {ollama_client._base_url} with model {ollama_client._model}"
    )
