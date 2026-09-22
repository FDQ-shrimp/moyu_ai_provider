"""Resumable full Function Calling verification for the remaining approved scope.

This runner never revisits preserved Batch 1 or Batch 2 evidence. It executes
Batch 2 streams, then Batch 3-6 non-stream gates and qualifying streams.
Credentials are accepted only through one non-echo stdin line and never saved.
"""
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
from scripts import verify_fc_expansion_batch2_nonstream_resume as prior

live = prior.live
dify_plugin = prior.dify_plugin
REPORT = ROOT / "scripts" / "fc_full_remaining_progress_report.json"
LIMIT = 320
SITE_LIMITS = {"china": 178, "overseas": 142}
MAX_TOKENS = 512
BUDGET = {
    "china": {"currency": "CNY", "limit": 100},
    "overseas": {"currency": "USD", "limit": 20},
    "platform_hard_limit_verified": False,
}
PARENTS = {
    "batch2": (
        ROOT / "scripts" / "fc_expansion_batch2_report.json",
        "f114bd792daf8062636740f722bb59c775d240a4ab477ea5d6f098c49e14945d",
    ),
    "batch2_gemini_retest": (
        ROOT / "scripts" / "fc_expansion_batch2_gemini25pro_china_nonstream_retest_report.json",
        "07e07b46811777c232317188abfc2259afadc71aacc25ae138b35c72afc9f1a6",
    ),
    "batch2_nonstream_resume": (
        ROOT / "scripts" / "fc_expansion_batch2_nonstream_resume_report.json",
        "b760b4321ea6cac8e1fb4f5a96d02b02157d50dadad382c4305b9fbd15e0f9ce",
    ),
}

# Batch 2 models whose preserved non-stream evidence passed every scheduled site.
BATCH2_STREAM = {
    "claude-haiku-4-5-20251001": ("china", "overseas"),
    "claude-opus-4-6": ("china", "overseas"),
    "deepseek-v4-flash": ("china", "overseas"),
    "glm-5.2": ("china", "overseas"),
    "gpt-5.6-sol": ("china", "overseas"),
    "kimi-k2.6": ("china", "overseas"),
    "qwen3.6-flash": ("china", "overseas"),
    "qwen-plus": ("china",),
    "doubao-seed-2-0-pro-260215": ("china",),
}
BATCHES = {
    3: {
        "MiniMax-M3": ("china", "overseas"),
        "claude-opus-4-5-20251101": ("china", "overseas"),
        "deepseek-v4-flash-0731": ("china", "overseas"),
        "doubao-seed-2-1-pro-260628": ("china", "overseas"),
        "gemini-2.5-flash-lite": ("china", "overseas"),
        "gpt-5.6-terra": ("china", "overseas"),
        "kimi-k3": ("china", "overseas"),
        "qwen3.7-plus": ("china", "overseas"),
        "DeepSeek-R1-0528": ("china",),
        "qwen3-max": ("china",),
    },
    4: {
        "claude-opus-4-1-20250805": ("china", "overseas"),
        "claude-sonnet-4-20250514": ("china", "overseas"),
        "gemini-3-flash-preview": ("china", "overseas"),
        "gemini-3.1-pro-preview": ("china", "overseas"),
        "glm-5.1": ("china", "overseas"),
        "gpt-5.6-luna": ("china", "overseas"),
        "kimi-k2.7-code": ("china", "overseas"),
        "qwen3.7-max": ("china", "overseas"),
        "DeepSeek-V3-0324": ("china",),
        "GLM-5": ("china",),
    },
    5: {
        "claude-opus-4-20250514": ("china", "overseas"),
        "claude-opus-4-7": ("china", "overseas"),
        "gemini-3.5-flash": ("china", "overseas"),
        "gemini-3.1-flash-lite-preview": ("china", "overseas"),
        "gpt-6-astra": ("china", "overseas"),
        "qwen3.6-27b": ("china", "overseas"),
        "qwen3.8-max": ("china", "overseas"),
        "doubao-seed-2-0-code-preview-260215": ("china",),
        "doubao-seed-2-0-lite-260215": ("china",),
        "qwen3-vl-plus": ("china",),
    },
    6: {
        "claude-opus-4-8": ("china", "overseas"),
        "claude-opus-5": ("china", "overseas"),
        "claude-sonnet-5": ("china", "overseas"),
        "gemini-2.5-flash-image-preview": ("china", "overseas"),
        "gemini-3-pro-image-preview": ("china", "overseas"),
        "gemini-3.1-flash-image-preview": ("china", "overseas"),
        "gemini-3.6-flash": ("china", "overseas"),
        "gpt-image-2(按次)": ("china", "overseas"),
        "qwen3.6-35b-a3b": ("china", "overseas"),
        "doubao-seed-2-0-mini-260215": ("china",),
    },
}
EXCLUDED = {
    "qwen3.6-plus",
    "claude-fable-5",
    "claude-sonnet-4-6",
    "deepseek-v4-pro",
    "glm-5.3",
    "gemini-2.5-flash",
    "gpt-5.5",
    "gemini-2.5-pro",
    "claude-sonnet-4-5-20250929",
}
IMMEDIATE_BATCH_STOP_REASONS = prior.IMMEDIATE_BATCH_STOP_REASONS
COMMON_INFRA_REASONS = prior.COMMON_INFRA_REASONS


def plan_payload():
    return {
        "batch2_stream": {model: list(sites) for model, sites in BATCH2_STREAM.items()},
        "batches": {
            str(batch): {model: list(sites) for model, sites in models.items()}
            for batch, models in BATCHES.items()
        },
        "excluded": sorted(EXCLUDED),
    }


def plan_sha256():
    return hashlib.sha256(
        json.dumps(plan_payload(), ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def result_rows():
    rows = []
    for model, sites in BATCH2_STREAM.items():
        for site in sites:
            rows.append(new_row(2, model, site, "stream"))
    for batch, models in BATCHES.items():
        for mode in ("nonstream", "stream"):
            for model, sites in models.items():
                for site in sites:
                    rows.append(new_row(batch, model, site, mode))
    return rows


def new_row(batch, model, site, mode):
    return {
        "batch": batch,
        "model": model,
        "site": site,
        "endpoint": live.SITES[site],
        "mode": mode,
        "status": "not_run",
        "reason": "pending",
        "tool_protocol_status": "not_run",
        "strict_final_text_status": "not_run",
        "evidence": [],
    }


def safe_report_path(path):
    """Keep repository reports relative while allowing isolated test fixtures."""
    path = Path(path)
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return path.name


class Journal:
    def __init__(self, path=REPORT, *, resume=False):
        self.path = Path(path)
        self.check_parents()
        if resume:
            live.require(self.path.exists(), "resume_report_missing")
            self.data = json.loads(self.path.read_bytes())
            self.validate_existing()
            self.normalize_interrupted_rows()
            return
        live.require(not self.path.exists(), "existing_report_requires_resume")
        self.data = {
            "report_schema": 1,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "scope": "remaining_registered_llm_function_calling",
            "plan": plan_payload(),
            "plan_sha256": plan_sha256(),
            "python": sys.version.split()[0],
            "sdk": importlib.metadata.version("dify_plugin"),
            "interpreter": sys.executable,
            "sdk_path": dify_plugin.__file__,
            "max_attempts": LIMIT,
            "site_attempt_limits": SITE_LIMITS,
            "max_tokens_per_request": MAX_TOKENS,
            "budget": BUDGET,
            "cost_estimate": None,
            "cost_note": "Prices and actual charges are not verified; usage is not billing proof.",
            "automatic_retries": False,
            "redirects": False,
            "model_listing": False,
            "credential_probing": False,
            "credential_source": "non_echo_stdin_line",
            "parents": {
                name: {"path": safe_report_path(path), "sha256": digest}
                for name, (path, digest) in PARENTS.items()
            },
            "attempts": [],
            "results": result_rows(),
            "halted": False,
            "halt_reason": None,
            "completed": False,
            "last_site_outcomes": {"china": None, "overseas": None},
        }
        self.save(create=True)

    @property
    def total_attempts(self):
        return len(self.data["attempts"])

    def site_attempts(self, site):
        return sum(attempt["site"] == site for attempt in self.data["attempts"])

    def check_parents(self):
        for path, digest in PARENTS.values():
            live.require(
                path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                "parent_report_hash_mismatch",
            )

    def validate_existing(self):
        live.require(self.data.get("report_schema") == 1, "resume_schema_mismatch")
        live.require(self.data.get("plan_sha256") == plan_sha256(), "resume_plan_mismatch")
        live.require(self.data.get("max_attempts") == LIMIT, "resume_limit_mismatch")
        live.require(self.data.get("site_attempt_limits") == SITE_LIMITS, "resume_limit_mismatch")
        live.require(self.data.get("budget") == BUDGET, "resume_budget_mismatch")
        live.require(not self.data.get("completed"), "verification_already_complete")
        live.require(not self.data.get("halted"), "resume_after_global_stop_requires_approval")

    def normalize_interrupted_rows(self):
        changed = False
        for row in self.data["results"]:
            if row["status"] != "not_run":
                continue
            attempts = self.row_attempts(row)
            if attempts:
                row.update(status="inconclusive", reason="interrupted_after_recorded_dispatch")
                prior.annotate_outcomes(self, row)
                row["request_attempts"] = len(attempts)
                changed = True
        if changed:
            self.save()

    def save(self, *, create=False):
        self.data["request_attempts"] = self.total_attempts
        self.data["site_request_attempts"] = {
            site: self.site_attempts(site) for site in live.SITES
        }
        mode = "x" if create else "w"
        with self.path.open(mode, encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)

    def row_attempts(self, row):
        return [
            attempt
            for attempt in self.data["attempts"]
            if attempt["batch"] == row["batch"]
            and attempt["model"] == row["model"]
            and attempt["site"] == row["site"]
            and attempt["mode"] == row["mode"]
        ]

    def begin_attempt(self, site, stream, turn):
        self.check_parents()
        model = live.MODEL
        mode = "stream" if stream else "nonstream"
        candidates = [
            row
            for row in self.data["results"]
            if row["model"] == model
            and row["site"] == site
            and row["mode"] == mode
            and row["status"] == "not_run"
        ]
        live.require(len(candidates) == 1 and turn in (1, 2), "request_scope_exceeded")
        row = candidates[0]
        attempts = self.row_attempts(row)
        live.require(
            len(attempts) < 2 and turn == len(attempts) + 1,
            "unexpected_retry_or_turn",
        )
        live.require(self.total_attempts < LIMIT, "request_cap_reached")
        live.require(
            self.site_attempts(site) < SITE_LIMITS[site],
            "site_request_cap_reached",
        )
        item = {
            "number": self.total_attempts + 1,
            "batch": row["batch"],
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


def find_result(journal, batch, model, site, mode):
    return next(
        row
        for row in journal.data["results"]
        if row["batch"] == batch
        and row["model"] == model
        and row["site"] == site
        and row["mode"] == mode
    )


def execute_row(journal, row, key):
    if row["status"] != "not_run":
        return
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
    prior.annotate_outcomes(journal, row)
    row["request_attempts"] = len(journal.row_attempts(row))
    journal.save()


def infrastructure_signature(journal, row):
    if row["reason"] not in COMMON_INFRA_REASONS:
        return None
    attempts = journal.row_attempts(row)
    last = attempts[-1] if attempts else {}
    return {
        "model": row["model"],
        "site": row["site"],
        "reason": row["reason"],
        "error_category": last.get("error_category"),
        "transport_stage": last.get("transport_stage"),
        "http_status": last.get("http_status"),
    }


def apply_stop_policy(journal, row):
    reason = row["reason"]
    if reason in IMMEDIATE_BATCH_STOP_REASONS or reason == "site_request_cap_reached":
        journal.data.update(halted=True, halt_reason=reason)
        journal.save()
        return True
    signature = infrastructure_signature(journal, row)
    previous = journal.data["last_site_outcomes"].get(row["site"])
    if signature is None:
        journal.data["last_site_outcomes"][row["site"]] = None
        journal.save()
        return False
    journal.data["last_site_outcomes"][row["site"]] = signature
    journal.save()
    same_failure = bool(
        previous
        and previous["model"] != signature["model"]
        and all(
            previous.get(key) == signature.get(key)
            for key in ("reason", "error_category", "transport_stage", "http_status")
        )
    )
    if same_failure:
        journal.data.update(
            halted=True,
            halt_reason="multiple_models_consecutive_common_infrastructure_error",
        )
        journal.save()
        return True
    return False


def accepted(row):
    return (
        row["tool_protocol_status"] == "pass"
        and row["strict_final_text_status"] == "pass"
    )


def skip_streams_after_gate(journal, batch, model, sites):
    for site in sites:
        row = find_result(journal, batch, model, site, "stream")
        if row["status"] == "not_run" and not journal.row_attempts(row):
            row.update(
                status="skipped",
                reason="skipped_nonstream_acceptance_gate",
                request_attempts=0,
                tool_protocol_status="not_run",
                strict_final_text_status="not_run",
            )
    journal.save()


def run_rows(journal, keys, rows):
    for row in rows:
        if row["status"] != "not_run":
            continue
        execute_row(journal, row, keys[row["site"]])
        if apply_stop_policy(journal, row):
            return False
    return True


def run_all(journal, keys):
    batch2_rows = [row for row in journal.data["results"] if row["batch"] == 2]
    if not run_rows(journal, keys, batch2_rows):
        return
    for batch, models in BATCHES.items():
        nonstream_rows = [
            row
            for row in journal.data["results"]
            if row["batch"] == batch and row["mode"] == "nonstream"
        ]
        if not run_rows(journal, keys, nonstream_rows):
            return
        for model, sites in models.items():
            if not all(
                accepted(find_result(journal, batch, model, site, "nonstream"))
                for site in sites
            ):
                skip_streams_after_gate(journal, batch, model, sites)
                continue
            stream_rows = [
                find_result(journal, batch, model, site, "stream") for site in sites
            ]
            if not run_rows(journal, keys, stream_rows):
                return
    journal.data["completed"] = True
    journal.data["completed_utc"] = datetime.now(timezone.utc).isoformat()
    journal.save()


def main():
    resume = sys.argv[1:] == ["--credentials-stdin", "--resume"]
    live.require(
        resume or sys.argv[1:] == ["--credentials-stdin"],
        "credentials_stdin_flag_required",
    )
    live.require(
        sys.version_info[:2] == (3, 12) and sys.prefix != sys.base_prefix,
        "isolated_python312_required",
    )
    live.require(importlib.metadata.version("dify_plugin") == "0.9.0", "sdk090_required")
    logging.disable(logging.CRITICAL)
    print("Full remaining verification: maximum 320 requests (China 178, overseas 142).")
    print("Authorized budgets: China CNY 100; overseas USD 20; no platform hard cap claimed.")
    print("No retries, redirects, model listing, credential probing, raw exceptions or responses.")
    keys = {}
    try:
        keys = prior.batch2.batch1.read_credentials_line(sys.stdin)
        journal = Journal(resume=resume)
        run_all(journal, keys)
        journal.save()
        print("Request attempts:", journal.total_attempts)
        print("Site attempts:", journal.data["site_request_attempts"])
        print("Completed:", journal.data["completed"])
        print("Halted:", journal.data["halted"], journal.data["halt_reason"])
        counts = {}
        for row in journal.data["results"]:
            key = (row["batch"], row["status"])
            counts[key] = counts.get(key, 0) + 1
        print("Result counts:", sorted(counts.items()))
        print("Sanitized progress report:", REPORT)
    finally:
        keys.clear()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("Interrupted. Progress was saved; resume will not repeat recorded requests.")
    except live.Halt as exc:
        print("Stopped:", str(exc))
        sys.exit(1)
