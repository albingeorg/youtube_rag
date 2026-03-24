"""Validate the configured Groq API key from project settings."""

from __future__ import annotations

import sys

from groq import APIConnectionError, APIStatusError, Groq

from app.core.config import get_settings


def _mask_key(key: str) -> str:
    if len(key) <= 10:
        return "*" * len(key)
    return f"{key[:6]}...{key[-4:]}"


def main() -> int:
    try:
        settings = get_settings()
    except Exception as exc:
        print(f"CONFIG ERROR: {exc}")
        return 2

    api_key = settings.groq_api_key
    print(f"Using key: {_mask_key(api_key)} (len={len(api_key)})")
    print(f"Model setting: {settings.groq_model}")

    client = Groq(api_key=api_key)

    try:
        # Lightweight auth check with minimal cost.
        models = client.models.list()
        count = len(models.data) if hasattr(models, "data") else "unknown"
        print(f"VALID: Groq key accepted. Available models: {count}")
        return 0
    except APIStatusError as exc:
        if exc.status_code == 401:
            print("INVALID: Groq returned 401 Invalid API Key")
        else:
            print(f"API ERROR: status={exc.status_code}, message={exc}")
        return 1
    except APIConnectionError as exc:
        print(f"NETWORK ERROR: Could not reach Groq API: {exc}")
        return 3
    except Exception as exc:
        print(f"UNEXPECTED ERROR: {type(exc).__name__}: {exc}")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
