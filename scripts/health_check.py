import os
import sys
from typing import Any

import requests

BASE_URL = "https://www.moyu.info/v1"
MODEL = "gpt-5.3-codex"


def fail(message: str) -> None:
    print(f"[FAIL] {message}")
    sys.exit(1)


def main() -> None:
    api_key = (os.getenv("MOYU_API_KEY") or "").strip()
    model = (os.getenv("MOYU_MODEL") or MODEL).strip()
    base_url = (os.getenv("MOYU_BASE_URL") or BASE_URL).strip().rstrip("/")

    if not api_key:
        fail("Missing MOYU_API_KEY environment variable.")

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": "请回复: ok"}],
        "max_tokens": 16,
        "stream": False,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    except requests.Timeout:
        fail("Request timeout.")
    except requests.RequestException as e:
        fail(f"Request failed: {e}")

    if resp.status_code >= 400:
        fail(f"HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        fail("No choices in response.")

    text = ((choices[0] or {}).get("message") or {}).get("content") or ""
    print("[OK] API reachable and model invocation succeeded.")
    print(f"Model: {model}")
    print(f"Reply: {text[:120]}")


if __name__ == "__main__":
    main()
