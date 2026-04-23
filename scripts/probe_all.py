"""
Probe every model from Moyu API and output a structured report.

Usage:
    python scripts/probe_all.py --api-key "YOUR_KEY"

Generates a JSON report (probe_report.json) and prints a summary table.
"""

import argparse
import json
import time
from pathlib import Path
from typing import Any

import requests

BASE_URL = "https://www.moyu.info/v1"
TIMEOUT = 30
RETRIES = 4


def _request(
    method: str,
    url: str,
    headers: dict[str, str],
    retries: int,
    timeout: int,
    json_body: dict[str, Any] | None = None,
) -> requests.Response:
    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            return requests.request(
                method, url, headers=headers, json=json_body, timeout=timeout
            )
        except requests.RequestException as e:
            last_err = e
            if attempt < retries:
                time.sleep(2 * attempt)
    raise last_err  # type: ignore[misc]


def fetch_models(base_url: str, api_key: str) -> list[str]:
    url = f"{base_url.rstrip('/')}/models"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "dify-moyu-probe/1.0",
    }
    resp = _request("GET", url, headers, RETRIES, TIMEOUT)
    if resp.status_code != 200:
        raise RuntimeError(f"List models failed: HTTP {resp.status_code}")
    data = resp.json().get("data") or []
    return [item["id"] for item in data if isinstance(item, dict) and item.get("id")]


def probe(base_url: str, api_key: str, model: str) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/chat/completions"
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

    start = time.time()
    try:
        resp = _request("POST", url, headers, RETRIES, TIMEOUT, json_body=payload)
    except requests.Timeout:
        return {
            "model": model,
            "ok": False,
            "reason": "timeout",
            "detail": f"No response within {TIMEOUT}s x {RETRIES} retries",
            "elapsed": round(time.time() - start, 1),
        }
    except requests.RequestException as e:
        return {
            "model": model,
            "ok": False,
            "reason": "network_error",
            "detail": str(e)[:200],
            "elapsed": round(time.time() - start, 1),
        }

    elapsed = round(time.time() - start, 1)

    if resp.status_code == 200:
        return {"model": model, "ok": True, "reason": "ok", "detail": "", "elapsed": elapsed}

    try:
        err = resp.json().get("error", {})
        code = err.get("code", "")
        msg = err.get("message", "")[:200]
    except Exception:
        code = ""
        msg = resp.text[:200]

    reason_map = {
        403: "no_permission",
        404: "model_not_found",
        400: "bad_request",
        500: "server_error",
        503: "service_unavailable",
    }
    reason = reason_map.get(resp.status_code, f"http_{resp.status_code}")

    return {
        "model": model,
        "ok": False,
        "reason": reason,
        "detail": f"[{code}] {msg}" if code else msg,
        "elapsed": elapsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--output", default="scripts/probe_report.json")
    args = parser.parse_args()

    models = fetch_models(args.base_url, args.api_key)
    total = len(models)
    print(f"[INFO] Total models to probe: {total}\n", flush=True)

    results: list[dict[str, Any]] = []
    for idx, model_id in enumerate(models, 1):
        r = probe(args.base_url, args.api_key, model_id)
        tag = "OK" if r["ok"] else "FAIL"
        print(f"[{idx:3d}/{total}] {tag:4s} | {r['elapsed']:5.1f}s | {model_id} | {r['reason']}", flush=True)
        results.append(r)

    ok_list = [r for r in results if r["ok"]]
    fail_list = [r for r in results if not r["ok"]]

    print(f"\n{'='*70}")
    print(f"  TOTAL: {total}   OK: {len(ok_list)}   FAIL: {len(fail_list)}")
    print(f"{'='*70}\n")

    if ok_list:
        print("--- CAN RUN (OK) ---")
        for r in ok_list:
            print(f"  {r['model']}")

    if fail_list:
        print("\n--- CANNOT RUN (FAIL) ---")
        for r in fail_list:
            detail = r["detail"][:80].encode("ascii", errors="replace").decode("ascii")
            print(f"  {r['model']:50s} | {r['reason']:20s} | {detail}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[INFO] Full report saved to: {out.resolve()}")


if __name__ == "__main__":
    main()
