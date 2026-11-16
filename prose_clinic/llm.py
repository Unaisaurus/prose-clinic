"""Optional connections to AI models. Nothing here runs unless you turn AI on in Settings.

Two kinds of provider are supported:
* Anthropic (Claude), through the official ``anthropic`` Python package.
* Any OpenAI-compatible chat server: OpenAI itself, OpenRouter, or a free local
  model running in Ollama or LM Studio.

API keys are read, in order, from: a key pasted into the app for this session
only, ``.streamlit/secrets.toml``, or an environment variable. They are never
written to disk by this app.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

# Claude models that accept server-side refusal fallbacks ("default" routing).
FALLBACK_MODELS = {"claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}

KEY_NAMES = {
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openai_compatible": ("OPENAI_API_KEY", "LLM_API_KEY"),
}

PROVIDER_LABELS = {
    "none": "Off (rule-based only)",
    "anthropic": "Anthropic (Claude)",
    "openai_compatible": "OpenAI-compatible (OpenAI, Ollama, LM Studio, OpenRouter…)",
}


class LLMError(Exception):
    """A problem talking to the AI provider, with a message meant for the user."""


@dataclass
class LLMConfig:
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None
    effort: str | None = None


def find_api_key(provider: str, session_keys: dict, secrets: dict | None = None) -> tuple[str | None, str]:
    """Return (key, where it came from)."""
    if session_keys.get(provider):
        return session_keys[provider], "pasted for this session"
    for name in KEY_NAMES.get(provider, ()):
        if secrets and secrets.get(name):
            return str(secrets[name]), f"{name} in .streamlit/secrets.toml"
    for name in KEY_NAMES.get(provider, ()):
        if os.environ.get(name):
            return os.environ[name], f"{name} environment variable"
    return None, ""


def build_config(ai_settings: dict, session_keys: dict, secrets: dict | None = None) -> LLMConfig | None:
    provider = ai_settings.get("provider", "none")
    if provider == "anthropic":
        key, _ = find_api_key(provider, session_keys, secrets)
        return LLMConfig(
            provider=provider,
            model=(ai_settings.get("anthropic_model") or "").strip() or "claude-opus-5-5",
            api_key=key,
            effort=ai_settings.get("anthropic_effort"),
        )
    if provider == "openai_compatible":
        key, _ = find_api_key(provider, session_keys, secrets)
        return LLMConfig(
            provider=provider,
            model=(ai_settings.get("openai_model") or "").strip(),
            api_key=key,
            base_url=(ai_settings.get("openai_base_url") or "").strip(),
        )
    return None


def complete(config: LLMConfig, system: str, user: str, *, json_schema: dict | None = None, max_tokens: int = 32000) -> str:
    """Send one request and return the model's text reply."""
    if config.provider == "anthropic":
        return _anthropic(config, system, user, json_schema, max_tokens)
    if config.provider == "openai_compatible":
        return _openai_compatible(config, system, user, json_schema)
    raise LLMError("No AI provider is configured. Choose one in Settings → AI connection.")


def _anthropic(config: LLMConfig, system: str, user: str, json_schema: dict | None, max_tokens: int) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise LLMError("The 'anthropic' package isn't installed. Run:  pip install anthropic") from exc

    client = anthropic.Anthropic(api_key=config.api_key) if config.api_key else anthropic.Anthropic()
    request: dict = {
        "model": config.model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    output_config: dict = {}
    if config.effort and config.effort != "default":
        output_config["effort"] = config.effort
    if json_schema:
        output_config["format"] = {"type": "json_schema", "schema": json_schema}
    if output_config:
        request["output_config"] = output_config
    if config.model in FALLBACK_MODELS:
        # If a safety classifier declines the request, retry server-side on a fallback model.
        request["betas"] = ["server-side-fallback-2026-07-01"]
        request["fallbacks"] = "default"

    try:
        with client.beta.messages.stream(**request) as stream:
            message = stream.get_final_message()
    except anthropic.AuthenticationError as exc:
        raise LLMError("Anthropic rejected the API key. Check it in Settings → AI connection.") from exc
    except anthropic.PermissionDeniedError as exc:
        raise LLMError(f"This API key isn't allowed to use that model or feature: {exc.message}") from exc
    except anthropic.NotFoundError as exc:
        raise LLMError(f"Model “{config.model}” wasn't found. Check the model name in Settings.") from exc
    except anthropic.RateLimitError as exc:
        raise LLMError("Rate limit reached. Wait a minute and try again.") from exc
    except anthropic.BadRequestError as exc:
        raise LLMError(
            f"The request was rejected: {exc.message}. If you changed the model, try setting "
            "“Effort” to “default” in Settings."
        ) from exc
    except anthropic.APIStatusError as exc:
        raise LLMError(f"Anthropic returned an error ({exc.status_code}). Try again shortly.") from exc
    except anthropic.APIConnectionError as exc:
        raise LLMError("Couldn't reach Anthropic. Check your internet connection.") from exc
    except TypeError as exc:  # very old SDK without these parameters
        raise LLMError(f"Your 'anthropic' package looks outdated ({exc}). Run:  pip install -U anthropic") from exc

    if message.stop_reason == "refusal":
        raise LLMError("The model declined this request. Try a different passage or model.")
    text = "".join(block.text for block in message.content if block.type == "text")
    if message.stop_reason == "max_tokens":
        raise LLMError("The reply was cut off because it hit the length limit. Try a shorter passage.")
    return text


def _openai_compatible(config: LLMConfig, system: str, user: str, json_schema: dict | None) -> str:
    import requests

    if not config.base_url:
        raise LLMError("Set the server address (base URL) in Settings → AI connection.")
    if not config.model:
        raise LLMError("Set a model name in Settings → AI connection.")
    if json_schema:
        user += (
            "\n\nRespond with a single JSON object (no prose before or after it) matching this JSON schema:\n"
            + json.dumps(json_schema)
        )
    headers = {"Content-Type": "application/json"}
    if config.api_key:
        headers["Authorization"] = f"Bearer {config.api_key}"
    payload = {
        "model": config.model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    url = config.base_url.rstrip("/") + "/chat/completions"
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=900)
    except requests.exceptions.ConnectionError as exc:
        raise LLMError(f"Couldn't connect to {config.base_url}. Is the server (e.g. Ollama) running?") from exc
    except requests.exceptions.Timeout as exc:
        raise LLMError("The server took too long to answer. Try a smaller model or a shorter passage.") from exc
    except requests.exceptions.RequestException as exc:
        raise LLMError(f"Request failed: {exc}") from exc

    if response.status_code in (401, 403):
        raise LLMError("The server rejected the API key. Check it in Settings → AI connection.")
    if response.status_code == 404:
        raise LLMError(f"Not found (404). Check the base URL and that model “{config.model}” is installed.")
    if response.status_code == 429:
        raise LLMError("Rate limit reached. Wait a minute and try again.")
    if not response.ok:
        raise LLMError(f"The server returned an error ({response.status_code}): {response.text[:300]}")
    try:
        text = response.json()["choices"][0]["message"]["content"] or ""
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LLMError("The server's reply wasn't in the expected OpenAI chat format.") from exc
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()  # hide local "reasoning" blocks


def test_connection(config: LLMConfig) -> str:
    reply = complete(config, "You are a connection test.", "Reply with exactly: OK", max_tokens=2000)
    return reply.strip()[:200] or "(empty reply)"


def parse_json_reply(text: str) -> dict:
    """Parse a JSON object from a model reply, tolerating code fences or stray prose."""
    cleaned = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise LLMError("The AI reply wasn't valid JSON.") from None
        try:
            data = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError("The AI reply wasn't valid JSON.") from exc
    if not isinstance(data, dict):
        raise LLMError("The AI reply wasn't a JSON object.")
    return data
