"""Resume only the approved remaining Batch 2 non-stream checks."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import logging
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts import verify_fc_expansion_batch2 as batch2

live = batch2.live
dify_plugin = batch2.batch1.dify_plugin
REPORT = ROOT / "scripts" / "fc_expansion_batch2_nonstream_resume_report.json"
PARENT = ROOT / "scripts" / "fc_expansion_batch2_report.json"
PARENT_SHA256 = "f114bd792daf8062636740f722bb59c775d240a4ab477ea5d6f098c49e14945d"
GEMINI_RETEST = (
    ROOT / "scripts" / "fc_expansion_batch2_gemini25pro_china_nonstream_retest_report.json"
)
GEMINI_RETEST_SHA256 = "07e07b46811777c232317188abfc2259afadc71aacc25ae138b35c72afc9f1a6"
LIMIT = 20
MAX_TOKENS = 512
SCHEDULE = {
    "glm-5.2": ("china", "overseas"),
    "gpt-5.6-sol": ("china", "overseas"),
    "kimi-k2.6": ("china", "overseas"),
    "qwen3.6-flash": ("china", "overseas"),
    "qwen-plus": ("china",),
    "doubao-seed-2-0-pro-260215": ("china",),
}
IMMEDIATE_BATCH_STOP_REASONS = {
    "authentication_or_permission",
    "quota_or_balance",
    "rate_limit_or_quota",
    "site_credential_mismatch",
    "redirect_blocked",
    "unmetered_http_forbidden",
    "request_cap_reached",
}
COMMON_INFRA_REASONS = {"transport_error_no_retry", "upstream_system_error"}


class Journal:
    def __init__(self, path=REPORT):
        self.path = Path(path)
        self.check_parents()
        parent = json.loads(PARENT.read_bytes())
        retest = json.loads(GEMINI_RETEST.read_bytes())
        live.require(
            parent["request_attempts"] == 17
            and parent["halted"] is True
            and parent["halt_reason"] == "transport_error_no_retry"
            and retest["request_attempts"] == 1
            and retest["result"]["model"] == "gemini-2.5-pro"
            and retest["result"]["status"] == "inconclusive"
            and retest["result"]["reason"] == "transport_error_no_retry",
            "unexpected_parent_history",
        )
        self.data = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "batch": "function_calling_expansion_2_nonstream_resume",
            "schedule": {model: list(sites) for model, sites in SCHEDULE.items()},
            "mode": "nonstream",
            "python": sys.version.split()[0],
            "sdk": importlib.metadata.version("dify_plugin"),
            "interpreter": sys.executable,
            "sdk_path": dify_plugin.__file__,
            "max_attempts": LIMIT,
            "max_tokens_per_request": MAX_TOKENS,
            "budget_context": "Uses the approved Batch 2 total budgets; not additional budgets.",
            "automatic_retries": False,
            "redirects": False,
            "model_listing": False,
            "credential_probing": False,
            "credential_source": "non_echo_stdin_line",
            "parent_report": "scripts/fc_expansion_batch2_report.json",
            "parent_report_sha256": PARENT_SHA256,
            "gemini_retest_report": (
                "scripts/fc_expansion_batch2_gemini25pro_china_nonstream_retest_report.json"
            ),
            "gemini_retest_report_sha256": GEMINI_RETEST_SHA256,
            "attempts": [],
            "results": [
                {
                    "model": model,
                    "site": site,
                    "endpoint": live.SITES[site],
                    "mode": "nonstream",
                    "status": "not_run",
                    "reason": "pending",
                    "tool_protocol_status": "not_run",
                    "strict_final_text_status": "not_run",
                    "evidence": [],
                }
                for model, sites in SCHEDULE.items()
                for site in sites
            ],
            "halted": False,
            "halt_reason": None,
            "common_infrastructure_events": [],
        }
        with self.path.open("x", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)

    @property
    def total_attempts(self):
        return len(self.data["attempts"])

    def check_parents(self):
        live.require(
            hashlib.sha256(PARENT.read_bytes()).hexdigest() == PARENT_SHA256,
            "parent_report_hash_mismatch",
        )
        live.require(
            hashlib.sha256(GEMINI_RETEST.read_bytes()).hexdigest() == GEMINI_RETEST_SHA256,
            "gemini_retest_report_hash_mismatch",
        )

    def save(self):
        self.data["request_attempts"] = self.total_attempts
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)

    def begin_attempt(self, site, stream, turn):
        self.check_parents()
        model = live.MODEL
        live.require(
            model in SCHEDULE and site in SCHEDULE[model] and not stream and turn in (1, 2),
            "resume_scope_exceeded",
        )
        live.require(self.total_attempts < LIMIT, "request_cap_reached")
        prior = [
            attempt
            for attempt in self.data["attempts"]
            if attempt["model"] == model and attempt["site"] == site
        ]
        live.require(
            len(prior) < 2 and turn == len(prior) + 1,
            "unexpected_retry_or_turn",
        )
        item = {
            "number": self.total_attempts + 1,
            "model": model,
            "site": site,
            "mode": "nonstream",
            "turn": turn,
            "outcome": "dispatch_started",
            "request_protocol_validated": True,
        }
        self.data["attempts"].append(item)
        self.save()
        return item


def result(journal, model, site):
    return next(
        row
        for row in journal.data["results"]
        if row["model"] == model and row["site"] == site
    )


def annotate_outcomes(journal, row):
    attempts = [
        attempt
        for attempt in journal.data["attempts"]
        if attempt["model"] == row["model"] and attempt["site"] == row["site"]
    ]
    diagnostics = row.get("diagnostics", [])
    first_evidence = next(
        (item for item in row.get("evidence", []) if item.get("turn") == 1),
        None,
    )
    second_attempt = next((item for item in attempts if item["turn"] == 2), None)
    second_diagnostic = next(
        (item for item in diagnostics if item.get("turn") == 2),
        None,
    )
    turn1_ok = bool(
        first_evidence
        and first_evidence.get("structured_upstream_and_sdk_match") is True
        and first_evidence.get("local_add_executed") is True
        and first_evidence.get("local_result") == 5
    )
    history_ok = bool(second_attempt and second_attempt.get("request_protocol_validated") is True)
    final_response_ok = bool(
        second_attempt
        and second_attempt.get("http_status") == 200
        and second_diagnostic
        and second_diagnostic.get("sdk_parse_completed") is True
        and second_diagnostic.get("sdk_output_matches_expected") is True
        and second_diagnostic.get("finish_reason") == "stop"
    )
    protocol_complete = turn1_ok and history_ok and final_response_ok and row["reason"] in {
        "single_tool_roundtrip_verified",
        "final_answer_not_confirmed",
        "ambiguous_sdk_answer_mapping",
        "sdk_answer_mapping_mismatch",
    }
    strict_match = (
        second_diagnostic.get("final_answer_matches") if second_diagnostic else None
    )
    row.update(
        structured_tool_call_verified=turn1_ok,
        local_add_result=5 if turn1_ok else None,
        tool_result_history_validated=history_ok,
        final_response_received=final_response_ok,
        tool_protocol_status="pass" if protocol_complete else "inconclusive",
        strict_final_answer_matches=strict_match,
        strict_final_text_status=(
            "pass"
            if strict_match is True
            else "fail"
            if final_response_ok and strict_match is False
            else "not_evaluated"
        ),
    )


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
    annotate_outcomes(journal, row)
    row["request_attempts"] = sum(
        attempt["model"] == row["model"] and attempt["site"] == row["site"]
        for attempt in journal.data["attempts"]
    )
    journal.save()


def mark_remaining(journal, reason):
    for row in journal.data["results"]:
        if row["status"] == "not_run":
            row.update(
                reason=reason,
                request_attempts=0,
                tool_protocol_status="not_run",
                strict_final_text_status="not_run",
            )
    journal.save()


def run_batch(journal, keys):
    infra_models = defaultdict(set)
    for model, sites in SCHEDULE.items():
        for site in sites:
            row = result(journal, model, site)
            execute_row(journal, row, keys[site])
            reason = row["reason"]
            if reason in IMMEDIATE_BATCH_STOP_REASONS:
                journal.data.update(halted=True, halt_reason=reason)
                mark_remaining(journal, "batch_halted_after_systemic_error")
                return
            if reason in COMMON_INFRA_REASONS:
                key = (site, reason)
                infra_models[key].add(model)
                journal.data["common_infrastructure_events"].append(
                    {"site": site, "reason": reason, "model": model}
                )
                journal.save()
                if len(infra_models[key]) >= 2:
                    journal.data.update(
                        halted=True,
                        halt_reason="multiple_models_common_infrastructure_error",
                    )
                    mark_remaining(journal, "batch_halted_after_common_infrastructure_error")
                    return


def main():
    live.require(sys.argv[1:] == ["--credentials-stdin"], "credentials_stdin_flag_required")
    live.require(
        sys.version_info[:2] == (3, 12) and sys.prefix != sys.base_prefix,
        "isolated_python312_required",
    )
    live.require(importlib.metadata.version("dify_plugin") == "0.9.0", "sdk090_required")
    live.require(not REPORT.exists(), "existing_report_do_not_reset_request_budget")
    logging.disable(logging.CRITICAL)
    print("Batch 2 non-stream resume: 6 exact models, maximum 20 requests.")
    print("No retries, redirects, model listing, credential probing, raw exceptions or responses.")
    keys = {}
    try:
        keys = batch2.batch1.read_credentials_line(sys.stdin)
        journal = Journal()
        run_batch(journal, keys)
        journal.save()
        print("Request attempts:", journal.total_attempts)
        for row in journal.data["results"]:
            print(
                row["model"],
                row["site"],
                row["status"],
                row["reason"],
                "protocol=" + row["tool_protocol_status"],
                "strict_final=" + row["strict_final_text_status"],
            )
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
