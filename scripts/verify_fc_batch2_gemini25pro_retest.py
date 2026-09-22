"""One authorized two-request retest: gemini-2.5-pro China non-stream tools."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts import verify_fc_expansion_batch2 as batch2

live = batch2.live
dify_plugin = batch2.batch1.dify_plugin
MODEL = "gemini-2.5-pro"
SITE = "china"
MODE = "nonstream"
REPORT = ROOT / "scripts" / "fc_expansion_batch2_gemini25pro_china_nonstream_retest_report.json"
PARENT = ROOT / "scripts" / "fc_expansion_batch2_report.json"
PARENT_SHA256 = "f114bd792daf8062636740f722bb59c775d240a4ab477ea5d6f098c49e14945d"
LIMIT = 2


class Journal:
    def __init__(self, path=REPORT):
        self.path = Path(path)
        self.check_parent()
        parent = json.loads(PARENT.read_bytes())
        row = next(
            item
            for item in parent["results"]
            if item["model"] == MODEL and item["site"] == SITE and item["mode"] == MODE
        )
        attempt = next(item for item in parent["attempts"] if item["number"] == 17)
        live.require(
            parent["request_attempts"] == 17
            and parent["halted"] is True
            and parent["halt_reason"] == "transport_error_no_retry"
            and row["status"] == "inconclusive"
            and row["reason"] == "transport_error_no_retry"
            and attempt["model"] == MODEL
            and attempt["site"] == SITE
            and attempt["mode"] == MODE
            and attempt["turn"] == 1
            and attempt["exception_type"] == "ReadTimeout"
            and attempt["headers_received"] is False,
            "unexpected_parent_history",
        )
        self.data = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "scope": {
                "model": MODEL,
                "site": SITE,
                "endpoint": live.SITES[SITE],
                "mode": MODE,
                "single_tool_only": True,
            },
            "python": sys.version.split()[0],
            "sdk": importlib.metadata.version("dify_plugin"),
            "interpreter": sys.executable,
            "sdk_path": dify_plugin.__file__,
            "max_attempts": LIMIT,
            "automatic_retries": False,
            "redirects": False,
            "model_listing": False,
            "credential_probing": False,
            "credential_source": "non_echo_stdin_line",
            "budget_context": "Uses the already approved Batch 2 total budget; not an additional budget.",
            "parent_report": "scripts/fc_expansion_batch2_report.json",
            "parent_report_sha256": PARENT_SHA256,
            "preserved_parent_attempt": 17,
            "attempts": [],
            "result": {
                "model": MODEL,
                "site": SITE,
                "endpoint": live.SITES[SITE],
                "mode": MODE,
                "status": "not_run",
                "reason": "pending",
                "evidence": [],
            },
        }
        with self.path.open("x", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)

    @property
    def total_attempts(self):
        return len(self.data["attempts"])

    def check_parent(self):
        live.require(
            hashlib.sha256(PARENT.read_bytes()).hexdigest() == PARENT_SHA256,
            "parent_report_hash_mismatch",
        )

    def save(self):
        self.data["request_attempts"] = self.total_attempts
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)

    def begin_attempt(self, site, stream, turn):
        self.check_parent()
        live.require(
            live.MODEL == MODEL and site == SITE and not stream and turn in (1, 2),
            "retest_scope_exceeded",
        )
        live.require(
            self.total_attempts < LIMIT and turn == self.total_attempts + 1,
            "request_cap_or_retry_blocked",
        )
        item = {
            "number": self.total_attempts + 1,
            "model": MODEL,
            "site": SITE,
            "mode": MODE,
            "turn": turn,
            "outcome": "dispatch_started",
            "request_protocol_validated": True,
        }
        self.data["attempts"].append(item)
        self.save()
        return item


def read_key_line(stream):
    restore_console = None
    if stream.isatty():
        live.require(os.name == "nt", "credentials_require_non_echo_input")
        import ctypes
        import msvcrt

        handle = msvcrt.get_osfhandle(stream.fileno())
        mode = ctypes.c_uint()
        kernel = ctypes.windll.kernel32
        live.require(
            bool(kernel.GetConsoleMode(handle, ctypes.byref(mode))),
            "credentials_echo_control_failed",
        )
        live.require(
            bool(kernel.SetConsoleMode(handle, mode.value & ~0x0004)),
            "credentials_echo_control_failed",
        )
        restore_console = lambda: kernel.SetConsoleMode(handle, mode.value)
    try:
        try:
            data = json.loads(stream.readline(4097))
        except (ValueError, TypeError):
            raise live.Halt("invalid_credential_input") from None
    finally:
        if restore_console is not None:
            restore_console()
    live.require(isinstance(data, dict) and set(data) == {SITE}, "invalid_credential_input")
    key = data[SITE]
    live.require(
        isinstance(key, str)
        and 0 < len(key.strip()) <= 512
        and "\n" not in key
        and "\r" not in key,
        "invalid_credential_input",
    )
    return key.strip()


def main():
    live.require(sys.argv[1:] == ["--credentials-stdin"], "credentials_stdin_flag_required")
    live.require(
        sys.version_info[:2] == (3, 12) and sys.prefix != sys.base_prefix,
        "isolated_python312_required",
    )
    live.require(importlib.metadata.version("dify_plugin") == "0.9.0", "sdk090_required")
    live.require(not REPORT.exists(), "existing_report_do_not_reset_request_budget")
    logging.disable(logging.CRITICAL)
    print("gemini-2.5-pro China non-stream retest only; maximum 2 requests.")
    print("No retries, redirects, model listing, credential probing, raw exceptions or responses.")
    key = None
    try:
        key = read_key_line(sys.stdin)
        journal = Journal()
        live.MODEL = MODEL
        live.MAX_TOKENS = batch2.MAX_TOKENS
        row = journal.data["result"]
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
        row["request_attempts"] = journal.total_attempts
        journal.save()
        print("Request attempts:", journal.total_attempts)
        print(MODEL, SITE, MODE, row["status"], row["reason"])
        print("Sanitized report:", REPORT)
    finally:
        key = None


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("Cancelled. No automatic retry.")
    except live.Halt as exc:
        print("Stopped:", str(exc))
        sys.exit(1)
