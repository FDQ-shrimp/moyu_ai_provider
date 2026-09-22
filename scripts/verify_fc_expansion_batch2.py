"""Metered Batch 2 Function Calling verification.

The schedule is an exact allowlist: nine bilateral models and two China-only
models. Credentials arrive through one non-echo stdin line and are never saved.
"""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata
import json
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts import verify_fc_expansion as batch1
from scripts import verify_fc_live as live

REPORT = ROOT / "scripts" / "fc_expansion_batch2_report.json"
LIMIT = 80
MAX_TOKENS = 512
VERIFIED_NOT_RETESTED = (
    "qwen3.6-plus",
    "claude-fable-5",
    "claude-sonnet-4-6",
    "deepseek-v4-pro",
    "glm-5.3",
    "gemini-2.5-flash",
    "gpt-5.5",
)
SCHEDULE = {
    "claude-haiku-4-5-20251001": ("china", "overseas"),
    "claude-opus-4-6": ("china", "overseas"),
    "claude-sonnet-4-5-20250929": ("china", "overseas"),
    "deepseek-v4-flash": ("china", "overseas"),
    "gemini-2.5-pro": ("china", "overseas"),
    "glm-5.2": ("china", "overseas"),
    "gpt-5.6-sol": ("china", "overseas"),
    "kimi-k2.6": ("china", "overseas"),
    "qwen3.6-flash": ("china", "overseas"),
    "qwen-plus": ("china",),
    "doubao-seed-2-0-pro-260215": ("china",),
}


class Journal:
    def __init__(self, path=REPORT):
        self.path = Path(path)
        self.data = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "batch": "function_calling_expansion_2",
            "schedule": {model: list(sites) for model, sites in SCHEDULE.items()},
            "verified_models_not_retested": list(VERIFIED_NOT_RETESTED),
            "python": sys.version.split()[0],
            "sdk": importlib.metadata.version("dify_plugin"),
            "interpreter": sys.executable,
            "max_attempts": LIMIT,
            "max_tokens_per_request": MAX_TOKENS,
            "budget": {
                "china": {"currency": "CNY", "limit": 50},
                "overseas": {"currency": "USD", "limit": 10},
                "platform_hard_limit_verified": False,
            },
            "cost_estimate": None,
            "cost_note": "Prices and actual charges are not verified; usage is not billing proof.",
            "credential_source": "non_echo_stdin_line",
            "automatic_retries": False,
            "redirects": False,
            "model_listing": False,
            "credential_probing": False,
            "attempts": [],
            "results": [
                {
                    "model": model,
                    "site": site,
                    "endpoint": live.SITES[site],
                    "mode": mode,
                    "status": "not_run",
                    "reason": "pending",
                    "evidence": [],
                }
                for model, sites in SCHEDULE.items()
                for mode in ("nonstream", "stream")
                for site in sites
            ],
            "halted": False,
            "halt_reason": None,
        }
        with self.path.open("x", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)

    @property
    def total_attempts(self):
        return len(self.data["attempts"])

    def save(self):
        self.data["request_attempts"] = self.total_attempts
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)

    def begin_attempt(self, site, stream, turn):
        model = live.MODEL
        mode = "stream" if stream else "nonstream"
        live.require(
            model in SCHEDULE and site in SCHEDULE[model] and turn in (1, 2),
            "request_scope_exceeded",
        )
        live.require(self.total_attempts < LIMIT, "request_cap_reached")
        prior = [
            attempt
            for attempt in self.data["attempts"]
            if attempt["model"] == model
            and attempt["site"] == site
            and attempt["mode"] == mode
        ]
        live.require(
            len(prior) < 2 and turn == len(prior) + 1,
            "unexpected_retry_or_turn",
        )
        item = {
            "number": self.total_attempts + 1,
            "model": model,
            "site": site,
            "mode": mode,
            "turn": turn,
            "outcome": "dispatch_started",
            "request_protocol_validated": True,
        }
        self.data["attempts"].append(item)
        self.save()
        return item


def result(journal, model, site, mode):
    return next(
        row
        for row in journal.data["results"]
        if row["model"] == model and row["site"] == site and row["mode"] == mode
    )


def mark_remaining(journal, reason):
    for row in journal.data["results"]:
        if row["status"] == "not_run":
            row["reason"] = reason
            row["request_attempts"] = 0
    journal.save()


def execute_row(journal, row, key):
    live.MODEL = row["model"]
    live.MAX_TOKENS = MAX_TOKENS
    try:
        live.check_pair(journal, row, key)
    except live.Halt as exc:
        row.update(status="inconclusive", reason=str(exc))
    except Exception as exc:
        row.update(status="inconclusive", reason="unexpected_sdk_or_payload_error")
        row["error_category"] = next(
            (
                name
                for cls, name in (
                    (KeyError, "missing_response_field"),
                    (ValueError, "invalid_value_or_payload"),
                    (TypeError, "unexpected_value_type"),
                    (AttributeError, "unexpected_object_shape"),
                )
                if isinstance(exc, cls)
            ),
            "other_sdk_error",
        )
    row["request_attempts"] = sum(
        attempt["model"] == row["model"]
        and attempt["site"] == row["site"]
        and attempt["mode"] == row["mode"]
        for attempt in journal.data["attempts"]
    )
    journal.save()
    return row["reason"] in batch1.BATCH_STOP_REASONS


def run_batch(journal, keys):
    # Finish every scheduled non-stream check before any stream request.
    for model, sites in SCHEDULE.items():
        for site in sites:
            row = result(journal, model, site, "nonstream")
            if execute_row(journal, row, keys[site]):
                journal.data.update(halted=True, halt_reason=row["reason"])
                mark_remaining(journal, "batch_halted_after_systemic_error")
                return

    # A model advances only when non-stream passed on every scheduled site.
    for model, sites in SCHEDULE.items():
        nonstream_pass = all(
            result(journal, model, site, "nonstream")["status"] == "pass"
            for site in sites
        )
        if not nonstream_pass:
            for site in sites:
                row = result(journal, model, site, "stream")
                row.update(reason="skipped_nonstream_site_gate", request_attempts=0)
            journal.save()
            continue
        for site in sites:
            row = result(journal, model, site, "stream")
            if execute_row(journal, row, keys[site]):
                journal.data.update(halted=True, halt_reason=row["reason"])
                mark_remaining(journal, "batch_halted_after_systemic_error")
                return


def main():
    live.require(sys.argv[1:] == ["--credentials-stdin"], "credentials_stdin_flag_required")
    live.require(
        sys.version_info[:2] == (3, 12) and sys.prefix != sys.base_prefix,
        "isolated_python312_required",
    )
    live.require(importlib.metadata.version("dify_plugin") == "0.9.0", "sdk090_required")
    live.require(not REPORT.exists(), "existing_report_do_not_reset_request_budget")
    sys.dont_write_bytecode = True
    logging.disable(logging.CRITICAL)
    print("Batch 2: 11 exact models; non-stream site gate before stream; maximum 80 attempts.")
    print("No retries, redirects, model listing, credential probing, raw replies, keys or headers.")
    print("Authorized budgets: China CNY 50; overseas USD 10. No platform hard cap claimed.")
    keys = {}
    try:
        keys = batch1.read_credentials_line(sys.stdin)
        journal = Journal()
        journal.data["sdk_path"] = batch1.dify_plugin.__file__
        run_batch(journal, keys)
        journal.save()
        print("Request attempts:", journal.total_attempts)
        for model, sites in SCHEDULE.items():
            summary = []
            for mode in ("nonstream", "stream"):
                for site in sites:
                    row = result(journal, model, site, mode)
                    summary.append(
                        site + "/" + mode + "=" + row["status"] + ":" + row["reason"]
                    )
            print(model, "; ".join(summary))
        print("Sanitized report:", REPORT)
    finally:
        keys.clear()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("Cancelled. No automatic retry.")
    except live.Halt as exc:
        print("Stopped:", str(exc))
        sys.exit(1)
    except Exception:
        print("Stopped: unexpected local error. Raw exception suppressed to protect credentials.")
        sys.exit(1)
