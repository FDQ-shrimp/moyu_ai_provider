import argparse
import re
import time
from pathlib import Path
from typing import Any

import requests
import yaml

BASE_URL = "https://www.moyu.info/v1"
MODEL_LIST_PATH = "/models"
CHAT_COMPLETIONS_PATH = "/chat/completions"
DEFAULT_CONTEXT_SIZE = 128000
DEFAULT_MAX_TOKENS = 4096
TIMEOUT_SECONDS = 30

# Keywords indicating a model accepts image INPUT (i.e. vision/multimodal models).
# These models get `features: [vision, agent-thought]` so Dify shows the image
# upload button in the LLM node. Pure image-OUTPUT models (t2i, t2v) that only
# produce images from text prompts do NOT need the vision flag.
VISION_INPUT_KEYWORDS = [
    "vl",          # vision-language: qwen3-vl, qwen-vl, glm-vl, …
    "vision",      # explicit "vision" in model id
    "i2i",         # image-to-image: jimeng_i2i, …
    "i2v",         # image-to-video: jimeng_i2v, wan2.x-i2v, doubao-seedance-i2v, …
    "r2v",         # reference-to-video: happyhorse-1.0-r2v (accepts image reference input)
    "multimodal",  # generic multimodal tag
    "image-01",    # minimax hailuo-image-01 (supports image input)
    "image01",
    "gpt-4o",      # all GPT-4o variants are multimodal
    "gpt-4-vision",
    "claude-3",    # claude-3.x are all multimodal
    "claude-opus", # claude opus series are multimodal
    "claude-sonnet",
    "claude-haiku",
    "claude-fable",  # claude fable series are multimodal
    "gemini",      # all Gemini models accept image input
    "kling",       # Kling (快影) video models support image-to-video input
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync Moyu models to Dify predefined model YAML files."
    )
    parser.add_argument("--api-key", required=True, help="Moyu API Key")
    parser.add_argument(
        "--base-url",
        default=BASE_URL,
        help=f"Moyu API base URL (default: {BASE_URL})",
    )
    parser.add_argument(
        "--output-dir",
        default="models/llm",
        help="Output directory for generated model YAML files",
    )
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Probe each model with a tiny request and keep only available models",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max number of models to generate (0 means all)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help="HTTP retry times for unstable network",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=TIMEOUT_SECONDS,
        help=f"HTTP timeout seconds (default: {TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--probe-retries",
        type=int,
        default=1,
        help="Retry times for each probe request (default: 1)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove existing .yaml files in output dir before generating",
    )
    return parser.parse_args()


def _request_with_retry(
    method: str,
    url: str,
    headers: dict[str, str],
    retries: int,
    timeout: int,
    json_body: dict[str, Any] | None = None,
) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                json=json_body,
                timeout=timeout,
            )
            return response
        except requests.RequestException as e:
            last_error = e
            if attempt < retries:
                time.sleep(1.5 * attempt)
    if last_error:
        raise last_error
    raise RuntimeError("Unknown request error")


def fetch_model_ids(base_url: str, api_key: str, retries: int) -> list[str]:
    url = f"{base_url.rstrip('/')}{MODEL_LIST_PATH}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "dify-moyu-sync/1.0",
    }
    resp = _request_with_retry("GET", url, headers, retries, TIMEOUT_SECONDS)
    if resp.status_code != 200:
        raise RuntimeError(f"Fetch models failed: HTTP {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    models = data.get("data") if isinstance(data, dict) else None
    if not isinstance(models, list):
        raise RuntimeError("Unexpected model list response format: missing 'data' list")

    ids: list[str] = []
    for item in models:
        model_id = (item or {}).get("id")
        if isinstance(model_id, str) and model_id.strip():
            ids.append(model_id.strip())

    if not ids:
        raise RuntimeError("Model list is empty")

    return ids


def probe_model(
    base_url: str, api_key: str, model: str, retries: int, timeout: int
) -> tuple[bool, str]:
    url = f"{base_url.rstrip('/')}{CHAT_COMPLETIONS_PATH}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
        "stream": False,
    }

    try:
        resp = _request_with_retry(
            "POST", url, headers, retries, timeout, json_body=payload
        )
    except requests.RequestException as e:
        return False, f"request_error: {e}"

    if resp.status_code >= 400:
        return False, f"http_{resp.status_code}"
    return True, "ok"


def to_label(model_id: str) -> str:
    """Return the label that Dify shows in the model picker.

    We deliberately keep the *raw* Moyu AI model ID (including dashes, dots,
    slashes and numeric suffixes) so that a user comparing the Dify dropdown
    against the Moyu AI console / model marketplace sees the same string on
    both sides. This avoids confusion such as `claude-opus-4-6` on Moyu AI
    being displayed as `Claude Opus 4 6` in Dify.
    """
    return (model_id or "").strip()


def to_filename(model_id: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", model_id.strip().lower()).strip("-")
    return f"{normalized or 'model'}.yaml"


def infer_context_size(model_id: str) -> int:
    lowered = model_id.lower()
    if "claude" in lowered:
        return 200000
    if "32k" in lowered:
        return 32000
    if "16k" in lowered:
        return 16000
    return DEFAULT_CONTEXT_SIZE


def infer_features(model_id: str) -> list[str]:
    """Return the Dify feature list for a model.

    Models that accept image INPUT get the `vision` feature so that Dify
    shows an image-upload button in the LLM node. Pure text-only models get
    only `agent-thought`.
    """
    lowered = model_id.lower()
    if any(kw in lowered for kw in VISION_INPUT_KEYWORDS):
        return ["vision", "agent-thought"]
    return ["agent-thought"]


def render_model_yaml(model_id: str) -> dict[str, Any]:
    context_size = infer_context_size(model_id)
    return {
        "model": model_id,
        "label": {
            "en_US": to_label(model_id),
            "zh_Hans": to_label(model_id),
        },
        "model_type": "llm",
        "features": infer_features(model_id),
        "model_properties": {
            "mode": "chat",
            "context_size": context_size,
        },
        "parameter_rules": [
            {"name": "temperature", "use_template": "temperature"},
            {"name": "top_p", "use_template": "top_p"},
            {"name": "max_tokens", "use_template": "max_tokens", "default": DEFAULT_MAX_TOKENS},
        ],
    }


def clean_existing_yaml(output_dir: Path) -> None:
    for file in output_dir.glob("*.yaml"):
        file.unlink()


def write_models(output_dir: Path, model_ids: list[str]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for model_id in model_ids:
        file_path = output_dir / to_filename(model_id)
        model_yaml = render_model_yaml(model_id)
        file_path.write_text(
            yaml.safe_dump(model_yaml, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)

    model_ids = fetch_model_ids(args.base_url, args.api_key, args.retries)
    print(f"[INFO] fetched models: {len(model_ids)}")

    if args.limit > 0:
        model_ids = model_ids[: args.limit]
        print(f"[INFO] applying limit: {len(model_ids)}")

    if args.probe:
        available: list[str] = []
        for idx, model_id in enumerate(model_ids, start=1):
            ok, reason = probe_model(
                args.base_url,
                args.api_key,
                model_id,
                args.probe_retries,
                args.timeout,
            )
            status = "OK" if ok else "FAIL"
            print(
                f"[PROBE] {idx}/{len(model_ids)} {model_id} -> {status} ({reason})",
                flush=True,
            )
            if ok:
                available.append(model_id)
        model_ids = available
        print(f"[INFO] available models after probe: {len(model_ids)}")

    if args.clean:
        clean_existing_yaml(output_dir)
        print(f"[INFO] cleaned existing YAML files in: {output_dir}")

    write_models(output_dir, model_ids)
    print(f"[OK] generated model YAML files: {len(model_ids)}")
    print(f"[OK] output dir: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
