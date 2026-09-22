"""Metered batch-one Function Calling expansion check.

This entry point reuses the phase-two protocol verifier but supplies an explicit
six-model schedule, a fresh append-only report, and batch-level stop rules.
Credentials are accepted only on one non-echo stdin line and never persisted.
"""
from __future__ import annotations

from datetime import datetime, timezone
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Import the SDK/gevent before requests/urllib3, while preventing dotenv,
# inherited settings, child processes and any unmetered network activity.
_LIVE = None


def protect_imports():
    def audit(event, args):
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            name = Path(os.fsdecode(args[0])).name.lower()
            if name == ".env" or name.startswith(".env."):
                raise RuntimeError("dotenv_forbidden")
        if event in {"subprocess.Popen", "os.system"}:
            raise RuntimeError("child_process_forbidden")
        if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
            allowed = _LIVE is not None and _LIVE.NETWORK_ALLOWED
            if not allowed:
                raise RuntimeError("unmetered_network_forbidden")

    sys.addaudithook(audit)
    from pydantic_settings.sources import DotEnvSettingsSource, EnvSettingsSource

    DotEnvSettingsSource._read_env_files = lambda self: {}
    EnvSettingsSource._load_env_vars = lambda self: {}


protect_imports()
import dify_plugin
from scripts import verify_fc_live as live
_LIVE = live

MODELS = (
    "claude-fable-5",
    "claude-sonnet-4-6",
    "deepseek-v4-pro",
    "glm-5.3",
    "gemini-2.5-flash",
    "gpt-5.5",
)
REPORT = ROOT / "scripts" / "fc_expansion_batch1_report.json"
LIMIT = 48
MAX_TOKENS = 512
BATCH_STOP_REASONS = {
    "authentication_or_permission",
    "quota_or_balance",
    "rate_limit_or_quota",
    "upstream_system_error",
    "redirect_blocked",
    "transport_error_no_retry",
    "unmetered_http_forbidden",
    "site_credential_mismatch",
    "request_cap_reached",
}


class Journal:
    def __init__(self, path=REPORT):
        self.path = Path(path)
        self.data = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "batch": "function_calling_expansion_1",
            "models": list(MODELS),
            "existing_verified_model_not_retested": "qwen3.6-plus",
            "python": sys.version.split()[0],
            "sdk": importlib.metadata.version("dify_plugin"),
            "interpreter": sys.executable,
            "max_attempts": LIMIT,
            "max_tokens_per_request": MAX_TOKENS,
            "budget": {
                "china": {"currency": "CNY", "limit": 30},
                "overseas": {"currency": "USD", "limit": 6},
                "platform_hard_limit_verified": False,
            },
            "cost_estimate": None,
            "cost_note": "Prices and actual charges are not verified; usage is not billing proof.",
            "credential_source": "anonymous_stdin_line",
            "automatic_retries": False,
            "redirects": False,
            "attempts": [],
            "results": [
                {"model": model, "site": site, "endpoint": endpoint, "mode": mode,
                 "status": "not_run", "reason": "pending", "evidence": []}
                for model in MODELS
                for mode in ("nonstream", "stream")
                for site, endpoint in live.SITES.items()
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
        live.require(model in MODELS and site in live.SITES and turn in (1, 2),
                     "request_scope_exceeded")
        live.require(self.total_attempts < LIMIT, "request_cap_reached")
        prior = [a for a in self.data["attempts"]
                 if a["model"] == model and a["site"] == site and a["mode"] == mode]
        live.require(len(prior) < 2 and turn == len(prior) + 1, "unexpected_retry_or_turn")
        item = {"number": self.total_attempts + 1, "model": model, "site": site,
                "mode": mode, "turn": turn, "outcome": "dispatch_started",
                "request_protocol_validated": True}
        self.data["attempts"].append(item)
        self.save()  # A timeout/crash still consumes one attempt.
        return item


def result(journal, model, site, mode):
    return next(row for row in journal.data["results"]
                if row["model"] == model and row["site"] == site and row["mode"] == mode)


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
        row["error_category"] = next((name for cls, name in (
            (KeyError, "missing_response_field"), (ValueError, "invalid_value_or_payload"),
            (TypeError, "unexpected_value_type"), (AttributeError, "unexpected_object_shape"))
            if isinstance(exc, cls)), "other_sdk_error")
    row["request_attempts"] = sum(
        a["model"] == row["model"] and a["site"] == row["site"] and a["mode"] == row["mode"]
        for a in journal.data["attempts"])
    journal.save()
    return row["reason"] in BATCH_STOP_REASONS


def run_batch(journal, keys):
    # Complete all six bilateral non-stream checks before any stream request.
    for model in MODELS:
        for site in live.SITES:
            if execute_row(journal, result(journal, model, site, "nonstream"), keys[site]):
                journal.data.update(halted=True,
                                    halt_reason=result(journal, model, site, "nonstream")["reason"])
                mark_remaining(journal, "batch_halted_after_systemic_error")
                return

    # Only a model passing both sites may proceed to either stream check.
    for model in MODELS:
        nonstream_pass = all(result(journal, model, site, "nonstream")["status"] == "pass"
                             for site in live.SITES)
        if not nonstream_pass:
            for site in live.SITES:
                row = result(journal, model, site, "stream")
                row.update(reason="skipped_nonstream_bilateral_gate", request_attempts=0)
            journal.save()
            continue
        for site in live.SITES:
            if execute_row(journal, result(journal, model, site, "stream"), keys[site]):
                journal.data.update(halted=True,
                                    halt_reason=result(journal, model, site, "stream")["reason"])
                mark_remaining(journal, "batch_halted_after_systemic_error")
                return


def read_credentials_line(stream):
    restore_console = None
    if stream.isatty():
        # Codex on Windows provides a ConPTY even for programmatic stdin. Turn
        # echo off for exactly this single line and fail closed if that cannot
        # be guaranteed. No prompt or manual terminal interaction is required.
        live.require(os.name == "nt", "credentials_require_non_echo_input")
        import ctypes
        import msvcrt

        handle = msvcrt.get_osfhandle(stream.fileno())
        mode = ctypes.c_uint()
        kernel = ctypes.windll.kernel32
        live.require(bool(kernel.GetConsoleMode(handle, ctypes.byref(mode))),
                     "credentials_echo_control_failed")
        live.require(bool(kernel.SetConsoleMode(handle, mode.value & ~0x0004)),
                     "credentials_echo_control_failed")
        restore_console = lambda: kernel.SetConsoleMode(handle, mode.value)
    try:
        try:
            line = stream.readline(8193)
            data = json.loads(line)
        except (ValueError, TypeError):
            raise live.Halt("invalid_credential_input") from None
    finally:
        if restore_console is not None:
            restore_console()
    live.require(isinstance(data, dict) and set(data) == set(live.SITES),
                 "invalid_credential_input")
    live.require(all(isinstance(value, str) and 0 < len(value.strip()) <= 512
                     and "\n" not in value and "\r" not in value for value in data.values()),
                 "invalid_credential_input")
    return {site: value.strip() for site, value in data.items()}


def main():
    live.require(sys.argv[1:] == ["--credentials-stdin"], "credentials_stdin_flag_required")
    live.require(sys.version_info[:2] == (3, 12) and sys.prefix != sys.base_prefix,
                 "isolated_python312_required")
    live.require(importlib.metadata.version("dify_plugin") == "0.9.0", "sdk090_required")
    live.require(not REPORT.exists(), "existing_report_do_not_reset_request_budget")
    sys.path.insert(0, str(ROOT))
    sys.dont_write_bytecode = True
    logging.disable(logging.CRITICAL)
    print("Six-model batch one. Non-stream bilateral gate before stream; maximum 48 attempts.")
    print("No retries, redirects, model listing, credential probing, raw replies, keys or headers.")
    print("Authorized budgets: China CNY 30; overseas USD 6. No platform hard cap claimed.")
    keys = {}
    try:
        keys = read_credentials_line(sys.stdin)
        journal = Journal()
        journal.data["sdk_path"] = dify_plugin.__file__
        run_batch(journal, keys)
        journal.save()
        print("Request attempts:", journal.total_attempts)
        for model in MODELS:
            summary = []
            for mode in ("nonstream", "stream"):
                for site in live.SITES:
                    row = result(journal, model, site, mode)
                    summary.append(site + "/" + mode + "=" + row["status"] + ":" + row["reason"])
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
