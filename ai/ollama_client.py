from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


@dataclass
class OllamaConfig:
    model: str = "qwen2.5:7b-instruct"
    temperature: float = 0.3
    max_tokens: int = 600
    url: str = DEFAULT_OLLAMA_URL


class OllamaError(RuntimeError):
    pass


def _debug_print(title: str, content: str) -> None:
    print(f"\n===== OLLAMA DEBUG: {title} =====")
    print(content)
    print(f"===== END OLLAMA DEBUG: {title} =====\n")


def list_models(*, url: str = DEFAULT_OLLAMA_URL, timeout_s: float = 5.0) -> List[str]:
    endpoint = f"{url.rstrip('/')}/api/tags"
    try:
        resp = requests.get(endpoint, timeout=timeout_s)
    except requests.exceptions.RequestException as exc:
        raise OllamaError(f"Failed to query Ollama models at {endpoint}: {exc}") from exc

    if resp.status_code != 200:
        snippet = resp.text[:200]
        raise OllamaError(f"Ollama returned HTTP {resp.status_code}. Response: {snippet}")

    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        raise OllamaError("Failed to parse Ollama JSON response.") from exc

    models = data.get("models", [])
    out: List[str] = []
    if isinstance(models, list):
        for m in models:
            if isinstance(m, dict):
                name = m.get("name")
                if isinstance(name, str) and name:
                    out.append(name)
    return sorted(set(out))


def generate(prompt: str, *, config: Optional[OllamaConfig] = None) -> str:
    """
    Call Ollama's /api/generate endpoint in non-streaming mode and return the response text.
    """
    if config is None:
        config = OllamaConfig()

    endpoint = f"{config.url.rstrip('/')}/api/generate"
    body: Dict[str, Any] = {
        "model": config.model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": config.temperature,
            "num_predict": config.max_tokens,
        },
    }
    _debug_print(
        "REQUEST",
        json.dumps(
            {
                "endpoint": endpoint,
                "model": config.model,
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "prompt": prompt,
            },
            ensure_ascii=False,
            indent=2,
        ),
    )

    try:
        resp = requests.post(endpoint, json=body, timeout=300)
    except requests.exceptions.ConnectionError as exc:
        raise OllamaError(
            f"Could not connect to Ollama at {config.url}. "
            "Make sure Ollama is running and the model is pulled "
            f"(e.g., `ollama pull {config.model}`)."
        ) from exc
    except requests.exceptions.Timeout as exc:
        raise OllamaError("Timed out waiting for response from Ollama.") from exc
    except requests.exceptions.RequestException as exc:
        raise OllamaError(f"Request to Ollama failed: {exc}") from exc

    if resp.status_code != 200:
        snippet = resp.text[:200]
        raise OllamaError(
            f"Ollama returned HTTP {resp.status_code}. Response: {snippet}"
        )

    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        raise OllamaError("Failed to parse Ollama JSON response.") from exc

    text = data.get("response")
    if not isinstance(text, str):
        raise OllamaError("Ollama response did not contain 'response' text.")
    _debug_print("RESPONSE", text)
    return text

