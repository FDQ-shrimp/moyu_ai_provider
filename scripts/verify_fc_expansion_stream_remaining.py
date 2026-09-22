"""Finish Batch 1 streaming checks for gemini-2.5-flash and gpt-5.5 only."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts import verify_fc_expansion as expansion

live = expansion.live
dify_plugin = expansion.dify_plugin
MODELS = ("gemini-2.5-flash", "gpt-5.5")
REPORT = ROOT / "scripts" / "fc_expansion_batch1_stream_remaining_report.json"
BATCH_REPORT = ROOT / "scripts" / "fc_expansion_batch1_report.json"
BATCH_SHA256 = "8bdbe359214af8091aafc1d7fab9880ec5d8c9ee5998fe29387cc18027b2150f"
GLM_RETEST_REPORT = ROOT / "scripts" / "fc_expansion_batch1_glm53_stream_retest_report.json"
GLM_RETEST_SHA256 = "fbf4e3da3c99e0406f5aca0b03036c69c81556fb195cf63735402145ca865224"
LIMIT = 8


class Journal:
    def __init__(self):
        self.check_parents()
        batch = json.loads(BATCH_REPORT.read_bytes())
        for model in MODELS:
            for site in live.SITES:
                nonstream = next(r for r in batch["results"] if r["model"] == model
                                 and r["site"] == site and r["mode"] == "nonstream")
                stream = next(r for r in batch["results"] if r["model"] == model
                              and r["site"] == site and r["mode"] == "stream")
                live.require(nonstream["status"] == "pass" and stream["status"] == "not_run",
                             "unexpected_parent_history")
        glm = json.loads(GLM_RETEST_REPORT.read_bytes())
        live.require(glm["scope"]["model"] == "glm-5.3"
                     and glm["result"]["status"] == "pass"
                     and glm["request_attempts"] == 2, "unexpected_glm_retest_history")
        self.path = REPORT
        self.data = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "scope": {"models": list(MODELS), "sites": live.SITES,
                      "mode": "stream", "single_tool_only": True},
            "python": sys.version.split()[0],
            "sdk": importlib.metadata.version("dify_plugin"),
            "interpreter": sys.executable,
            "sdk_path": dify_plugin.__file__,
            "max_attempts": LIMIT,
            "max_tokens_per_request": expansion.MAX_TOKENS,
            "automatic_retries": False,
            "redirects": False,
            "model_listing": False,
            "credential_probing": False,
            "credential_source": "non_echo_stdin_line",
            "batch_report": "scripts/fc_expansion_batch1_report.json",
            "batch_report_sha256": BATCH_SHA256,
            "glm_retest_report": "scripts/fc_expansion_batch1_glm53_stream_retest_report.json",
            "glm_retest_report_sha256": GLM_RETEST_SHA256,
            "attempts": [],
            "results": [
                {"model": model, "site": site, "endpoint": endpoint,
                 "mode": "stream", "status": "not_run", "reason": "pending", "evidence": []}
                for model in MODELS for site, endpoint in live.SITES.items()
            ],
            "halted": False,
            "halt_reason": None,
        }
        with REPORT.open("x", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)

    @property
    def total_attempts(self):
        return len(self.data["attempts"])

    def check_parents(self):
        live.require(hashlib.sha256(BATCH_REPORT.read_bytes()).hexdigest() == BATCH_SHA256,
                     "batch_report_hash_mismatch")
        live.require(hashlib.sha256(GLM_RETEST_REPORT.read_bytes()).hexdigest() == GLM_RETEST_SHA256,
                     "glm_retest_report_hash_mismatch")

    def save(self):
        self.data["request_attempts"] = self.total_attempts
        with REPORT.open("w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)

    def begin_attempt(self, site, stream, turn):
        self.check_parents()
        model = live.MODEL
        live.require(model in MODELS and site in live.SITES and stream and turn in (1, 2),
                     "continuation_scope_exceeded")
        live.require(self.total_attempts < LIMIT, "request_cap_reached")
        prior = [a for a in self.data["attempts"] if a["model"] == model and a["site"] == site]
        live.require(len(prior) < 2 and turn == len(prior) + 1, "unexpected_retry_or_turn")
        item = {"number": self.total_attempts + 1, "model": model, "site": site,
                "mode": "stream", "turn": turn, "outcome": "dispatch_started",
                "request_protocol_validated": True}
        self.data["attempts"].append(item)
        self.save()
        return item


def result(journal, model, site):
    return next(r for r in journal.data["results"] if r["model"] == model and r["site"] == site)


def mark_remaining(journal, reason):
    for row in journal.data["results"]:
        if row["status"] == "not_run":
            row.update(reason=reason, request_attempts=0)
    journal.save()


def execute_row(journal, row, key):
    live.MODEL = row["model"]
    live.MAX_TOKENS = expansion.MAX_TOKENS
    try:
        live.check_pair(journal, row, key)
    except live.Halt as exc:
        row.update(status="inconclusive", reason=str(exc))
    except Exception as exc:
        row.update(status="inconclusive", reason="unexpected_sdk_or_payload_error")
        row["error_category"] = next((name for cls, name in (
            (KeyError, "missing_response_field"), (ValueError, "invalid_value_or_payload"),
            (TypeError, "unexpected_value_type"), (AttributeError, "unexpected_object_shape"))
            if isinstance(exc, cls)), "other_sdk_error")
    row["request_attempts"] = sum(a["model"] == row["model"] and a["site"] == row["site"]
                                  for a in journal.data["attempts"])
    journal.save()
    return row["reason"] in expansion.BATCH_STOP_REASONS


def run(journal, keys):
    for model in MODELS:
        for site in live.SITES:
            row = result(journal, model, site)
            if execute_row(journal, row, keys[site]):
                journal.data.update(halted=True, halt_reason=row["reason"])
                mark_remaining(journal, "batch_halted_after_systemic_error")
                return


def main():
    live.require(sys.argv[1:] == ["--credentials-stdin"], "credentials_stdin_flag_required")
    live.require(sys.version_info[:2] == (3, 12) and sys.prefix != sys.base_prefix,
                 "isolated_python312_required")
    live.require(importlib.metadata.version("dify_plugin") == "0.9.0", "sdk090_required")
    live.require(not REPORT.exists(), "existing_report_do_not_reset_request_budget")
    logging.disable(logging.CRITICAL)
    print("Batch 1 stream continuation: gemini-2.5-flash and gpt-5.5 only; maximum 8 requests.")
    print("No retries, redirects, nonstream reruns, model listing, credential probing or raw responses.")
    keys = {}
    try:
        keys = expansion.read_credentials_line(sys.stdin)
        journal = Journal()
        run(journal, keys)
        journal.save()
        print("Request attempts:", journal.total_attempts)
        for model in MODELS:
            for site in live.SITES:
                row = result(journal, model, site)
                print(model, site, "stream", row["status"], row["reason"])
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
