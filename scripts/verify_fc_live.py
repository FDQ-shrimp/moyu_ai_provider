"""Explicit live check. Never import this to enable networking.

Run with the dedicated Python 3.12 / SDK 0.9.0 venv. Credentials arrive through
an anonymous stdin pipe, never command arguments. No credentials/headers saved.
The separate offline runner and its irreversible audit hooks remain untouched.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
MODEL = "qwen3.6-plus"
SITES = {"china": "https://www.moyu.cn/v1", "overseas": "https://www.konjac.ai/v1"}
LIMIT = 10
MAX_TOKENS = 256
REPORT = ROOT / "scripts" / "fc_phase2_round1_report.json"
RESUME_REPORT = ROOT / "scripts" / "fc_phase2_stream_resume_report.json"
ORIGINAL_REPORT_SHA256 = "57f8ce5032733a7ea13b9ecffb383b3697ce04b61ac725ce1f98c2a0b7559d72"
# The SDK uses gevent DNS worker threads: a ContextVar would not propagate there.
# This runner is sequential; permit networking only while its metered send runs.
NETWORK_ALLOWED = False


class Halt(Exception):
    """Only fixed, non-sensitive reason codes are used as messages."""


def require(condition, reason):
    if not condition:
        raise Halt(reason)


def protect_imports():
    def audit(event, args):
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            name = Path(os.fsdecode(args[0])).name.lower()
            if name == ".env" or name.startswith(".env."):
                raise Halt("dotenv_forbidden")
        if event in {"subprocess.Popen", "os.system"}:
            raise Halt("child_process_forbidden")
        if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto"}:
            require(NETWORK_ALLOWED, "unmetered_network_forbidden")

    sys.addaudithook(audit)
    from pydantic_settings.sources import DotEnvSettingsSource, EnvSettingsSource

    DotEnvSettingsSource._read_env_files = lambda self: {}
    EnvSettingsSource._load_env_vars = lambda self: {}


# Match the safe runner's import order: SDK/gevent BEFORE requests/SSL.
# On test import, the offline runner has already installed its stricter guards.
if __name__ == "__main__":
    sys.dont_write_bytecode = True
    protect_imports()
    import dify_plugin

import requests
from requests.adapters import HTTPAdapter
from urllib3.exceptions import ReadTimeoutError
from urllib3.util.retry import Retry


def reason_for_status(status):
    if status in (401, 403):
        return "authentication_or_permission"
    if status == 402:
        return "quota_or_balance"
    if status == 429:
        return "rate_limit_or_quota"
    if status == 404:
        return "model_or_endpoint_not_found"
    if 300 <= status < 400:
        return "redirect_blocked"
    if status >= 500:
        return "upstream_system_error"
    return "upstream_http_error"


def safe_transport_exception(exc):
    """Return only a fixed exception label/category; never serialize exc."""
    if isinstance(exc, requests.exceptions.ConnectTimeout):
        return "ConnectTimeout", "connect_timeout"
    if isinstance(exc, requests.exceptions.ReadTimeout):
        return "ReadTimeout", "read_timeout"
    if isinstance(exc, requests.exceptions.Timeout):
        return "Timeout", "timeout"
    # Response.iter_lines can wrap urllib3's ReadTimeoutError in ConnectionError.
    pending, seen = [exc], set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if isinstance(current, ReadTimeoutError):
            return "ReadTimeout", "read_timeout"
        if isinstance(current, BaseException):
            pending.extend(value for value in (current.__cause__, current.__context__)
                           if value is not None)
            pending.extend(value for value in current.args if isinstance(value, BaseException))
    if isinstance(exc, requests.exceptions.ConnectionError):
        return "ConnectionError", "connection_error"
    return None, None


class Journal:
    def __init__(self, path, *, parent_path=None, expected_parent_sha256=None):
        self.path = Path(path)
        self.parent_path = Path(parent_path) if parent_path is not None else None
        self.parent_sha256 = expected_parent_sha256
        prior_count = 0
        if self.parent_path is not None:
            self.check_parent()
            parent = json.loads(self.parent_path.read_bytes())
            require(parent["model"] == MODEL and parent["sdk"] == "0.9.0"
                    and [a["number"] for a in parent["attempts"]] == list(range(1, 7)),
                    "unexpected_parent_history")
            states = {(r["site"], r["mode"]): r for r in parent["results"]}
            require(all(states[(site, "nonstream")]["status"] == "pass" for site in SITES)
                    and states[("china", "stream")]["status"] == "inconclusive"
                    and states[("overseas", "stream")]["status"] == "not_run",
                    "unexpected_parent_results")
            prior_count = 6
        self.data = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "model": MODEL, "python": sys.version.split()[0],
            "sdk": importlib.metadata.version("dify_plugin"),
            "interpreter": sys.executable, "max_attempts": LIMIT,
            "budget": {"china": {"currency": "CNY", "limit": 10},
                       "overseas": {"currency": "USD", "limit": 2},
                       "platform_hard_limit_verified": False,
                       "billing_overrun_risk_accepted_by_user": True},
            "cost_estimate": None,
            "cost_note": "Current site prices not verified; usage is not proof of actual charges.",
            "credential_source": "anonymous_stdin_pipe",
            "prior_attempts": prior_count,
            "parent_report_sha256": self.parent_sha256,
            "cumulative_attempts": prior_count,
            "attempts": [], "results": [
                {"site": site, "endpoint": url, "model": MODEL,
                 "mode": mode, "status": "not_run", "reason": "pending", "evidence": []}
                for mode in (("stream",) if prior_count else ("nonstream", "stream"))
                for site, url in SITES.items()
            ],
        }
        # Fail closed on rerun: do not silently reset the cumulative allowance.
        with self.path.open("x", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)

    def check_parent(self):
        if self.parent_path is not None:
            require(hashlib.sha256(self.parent_path.read_bytes()).hexdigest() == self.parent_sha256,
                    "parent_report_hash_mismatch")

    @property
    def total_attempts(self):
        return self.data["prior_attempts"] + len(self.data["attempts"])

    def save(self):
        self.data["cumulative_attempts"] = self.total_attempts
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(self.data, handle, ensure_ascii=False, indent=2)

    def begin_attempt(self, site, stream, turn):
        self.check_parent()
        require(self.total_attempts < LIMIT, "request_cap_reached")
        if self.data["prior_attempts"]:
            require(stream and sum(a["site"] == site for a in self.data["attempts"]) < 2,
                    "resume_scope_exceeded")
        item = {"number": self.total_attempts + 1, "site": site,
                "mode": "stream" if stream else "nonstream", "turn": turn,
                "outcome": "dispatch_started", "request_protocol_validated": True}
        self.data["attempts"].append(item)
        # Persist BEFORE dispatch. Timeout/crash attempts remain charged to cap.
        self.save()
        return item


class Trace:
    def __init__(self):
        self.calls = {}
        self.finish = None
        self.fragments = 0
        self.digest = hashlib.sha256()
        self.usage = {}
        self.final_content = ""
        self.reasoning_field_present = False
        self.expected_sdk_content = ""
        self.in_reasoning = False
        self.answer_mapping_unambiguous = True
        self.payload_count = 0

    def observe(self, payload, stream):
        self.digest.update(json.dumps(payload, sort_keys=True).encode())
        self.payload_count += 1
        if payload.get("error"):
            # Classify without recording arbitrary server error text.
            error = json.dumps(payload["error"]).lower()
            if any(word in error for word in ("balance", "quota", "insufficient")):
                raise Halt("quota_or_balance")
            if any(word in error for word in ("unauthorized", "api_key", "api key")):
                raise Halt("authentication_or_permission")
            if "rate" in error:
                raise Halt("rate_limit_or_quota")
            raise Halt("upstream_error_payload")
        usage = payload.get("usage") or {}
        self.usage.update({k: v for k, v in usage.items()
                           if k in {"prompt_tokens", "completion_tokens", "total_tokens"}
                           and type(v) is int and v >= 0})
        for choice in payload.get("choices", []):
            require(choice.get("index", 0) == 0, "multiple_choices_out_of_scope")
            if choice.get("finish_reason"):
                self.finish = choice["finish_reason"]
            message = choice.get("delta" if stream else "message", {})
            if ("delta" if stream else "message") in choice:
                self.observe_content(message, stream)
            for index, call in enumerate(message.get("tool_calls") or []):
                slot = call.get("index", index)
                require(slot == 0, "multiple_tools_out_of_scope")
                item = self.calls.setdefault(slot, {"id": "", "name": "", "arguments": ""})
                function = call.get("function") or {}
                for name, value in (("id", call.get("id")), ("name", function.get("name")),
                                    ("arguments", function.get("arguments"))):
                    if value is not None:
                        require(isinstance(value, str), "malformed_tool_fragment")
                        item[name] += value
                self.fragments += 1

    def observe_content(self, message, stream):
        self.reasoning_field_present |= "reasoning_content" in message
        content = message.get("content")
        reasoning = message.get("reasoning_content")
        if not all(value is None or isinstance(value, str) for value in (content, reasoning)):
            self.answer_mapping_unambiguous = False
            raise Halt("non_text_answer_shape")
        content, reasoning = content or "", reasoning or ""
        self.final_content += content
        if not stream:
            self.expected_sdk_content += content
            return
        # SDK 0.9.0's documented wrapper, checked against real SDK output.
        # Never strip tags or search for a digit in combined reasoning/answer.
        # Same-delta reasoning+answer can lose content in this SDK: fail closed.
        if content and reasoning:
            self.answer_mapping_unambiguous = False
        if reasoning:
            if not self.in_reasoning:
                self.expected_sdk_content += "<think>\n"
            self.expected_sdk_content += reasoning
            self.in_reasoning = True
        else:
            if self.in_reasoning:
                self.expected_sdk_content += "\n</think>"
            self.in_reasoning = False
            self.expected_sdk_content += content

    def diagnostics(self, sdk_content, parse_completed):
        known_finishes = {"stop", "tool_calls", "length", "max_tokens", "content_filter"}
        return {
            "final_answer_present": bool(self.final_content.strip()),
            "final_answer_matches": self.final_content.strip() == "5",
            "reasoning_field_present": self.reasoning_field_present,
            "answer_mapping_unambiguous": self.answer_mapping_unambiguous,
            "sdk_parse_completed": parse_completed,
            "sdk_output_matches_expected": (sdk_content == self.expected_sdk_content)
            if parse_completed else None,
            "finish_reason": self.finish if self.finish in known_finishes else
            (None if self.finish is None else "unrecognized"),
            "usage": {k: self.usage.get(k) for k in ("prompt_tokens", "completion_tokens", "total_tokens")},
            "response_sha256": self.digest.hexdigest() if self.payload_count else None,
            "response_hash_scope": "observed_json_payloads_only",
            "observed_payload_count": self.payload_count,
        }

    def check_finish(self, final=False):
        if self.finish in {"length", "max_tokens"}:
            raise Halt("truncated")
        require(self.finish in ({"stop"} if final else {"stop", "tool_calls"}),
                "incomplete_or_unexpected_finish")


class MeteredAdapter(HTTPAdapter):
    def __init__(self, journal, site, stream, turn, call=None, expected_key=None):
        super().__init__(max_retries=Retry(total=0, connect=0, read=0, redirect=0, status=0, other=0))
        self.journal, self.site, self.stream, self.turn = journal, site, stream, turn
        self.call = call
        self.expected_key = expected_key
        self.trace = Trace()
        self.dispatched = False

    def send(self, request, **kwargs):
        global NETWORK_ALLOWED
        require(not self.dispatched, "unexpected_second_dispatch")
        require(request.method == "POST" and request.url == SITES[self.site] + "/chat/completions",
                "unapproved_destination")
        if self.expected_key is not None:
            require(request.headers.get("Authorization") == "Bearer " + self.expected_key,
                    "site_credential_mismatch")
        body = json.loads(request.body)
        require(body.get("model") == MODEL and body.get("stream") is self.stream
                and body.get("max_tokens") == MAX_TOKENS, "unexpected_request_parameters")
        if self.turn == 1:
            require(body.get("tool_choice") == "auto" and len(body.get("tools", [])) == 1
                    and body["tools"][0]["function"]["name"] == "add", "tools_not_forwarded")
        else:
            history = body["messages"]
            require("tools" not in body and "tool_choice" not in body, "unexpected_new_tools")
            require(history[-2].get("role") == "assistant"
                    and history[-2].get("tool_calls") == [self.call]
                    and history[-1] == {"role": "tool", "content": "5",
                                        "tool_call_id": self.call["id"]}, "tool_history_mismatch")
        item = self.journal.begin_attempt(self.site, self.stream, self.turn)
        self.dispatched = True
        started = time.monotonic()
        NETWORK_ALLOWED = True
        try:
            # This is the actual requests/urllib3 sending boundary, not _invoke.
            result = super().send(request, **kwargs)
        except Exception as exc:
            exception_type, category = safe_transport_exception(exc)
            item["outcome"] = "transport_error_no_retry"
            item["error_category"] = category or (
                "tls_error" if isinstance(exc, requests.exceptions.SSLError)
                else "other_transport_error")
            item["exception_type"] = exception_type or (
                "SSLError" if isinstance(exc, requests.exceptions.SSLError)
                else "OtherTransportError")
            item["headers_received"] = False
            item["transport_stage"] = (
                "connect" if item["exception_type"] == "ConnectTimeout"
                else "wait_response_headers" if item["exception_type"] == "ReadTimeout"
                else "before_response_headers")
            item["elapsed_ms"] = round((time.monotonic() - started) * 1000)
            self.journal.save()
            raise Halt("transport_error_no_retry") from None
        finally:
            NETWORK_ALLOWED = False
        item["http_status"] = result.status_code
        item["outcome"] = "http_response_received"
        item["headers_received"] = True
        item["elapsed_to_headers_ms"] = round((time.monotonic() - started) * 1000)
        self.journal.save()
        if result.status_code != 200:
            result.close()
            raise Halt(reason_for_status(result.status_code))
        result.encoding = "utf-8"
        if self.stream:
            original_lines = result.iter_lines
            headers_at = time.monotonic()

            def observed_lines(*args, **kw):
                try:
                    for line in original_lines(*args, **kw):
                        text = line.decode("utf-8") if isinstance(line, bytes) else line
                        text = text.strip()
                        if text and not text.startswith(":"):
                            value = text.removeprefix("data:").strip()
                            if value != "[DONE]":
                                self.trace.observe(json.loads(value), True)
                        yield line
                except Exception as exc:
                    exception_type, category = safe_transport_exception(exc)
                    if exception_type is None:
                        raise
                    item.update(
                        outcome="stream_transport_error_no_retry",
                        error_category=category,
                        exception_type=exception_type,
                        headers_received=True,
                        transport_stage="sse_body_read_after_headers",
                        elapsed_after_headers_ms=round((time.monotonic() - headers_at) * 1000),
                    )
                    self.journal.save()
                    raise Halt("transport_error_no_retry") from None

            result.iter_lines = observed_lines
        else:
            self.trace.observe(result.json(), False)
        return result


@contextmanager
def transport_for(meter):
    original_post, original_send = requests.post, requests.sessions.Session.send
    sessions, responses = [], []

    def denied(*args, **kwargs):
        raise Halt("unmetered_http_forbidden")

    def post(url, **kwargs):
        session = requests.Session()
        session.trust_env = False  # No inherited proxy credentials or netrc.
        session.mount("https://", meter)
        session.send = lambda request, **kw: original_send(session, request, **kw)
        sessions.append(session)
        kwargs["allow_redirects"] = False
        kwargs["timeout"] = (10, 60)
        reply = session.post(url, **kwargs)
        responses.append(reply)
        return reply

    requests.sessions.Session.send, requests.post = denied, post
    try:
        yield
    finally:
        requests.post, requests.sessions.Session.send = original_post, original_send
        for reply in responses:
            reply.close()
        for session in sessions:
            session.close()


def runtime(model=None):
    from dify_plugin.entities.model import AIModelEntity
    from dify_plugin.entities.model.message import AssistantPromptMessage, PromptMessageTool, ToolPromptMessage, UserPromptMessage
    from models.llm.llm import MoyuLargeLanguageModel
    import yaml

    model = model or MODEL
    candidates = []
    provider = yaml.safe_load((ROOT / "provider/moyu.yaml").read_text(encoding="utf-8"))
    for relative in provider["models"]["llm"]["predefined"]:
        path = ROOT / relative
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if data.get("model") == model:
            candidates.append((path, data))
    require(len(candidates) == 1, "model_not_uniquely_registered")
    schema = AIModelEntity.model_validate(candidates[0][1])
    return MoyuLargeLanguageModel([schema]), AssistantPromptMessage, PromptMessageTool, ToolPromptMessage, UserPromptMessage


def check_pair(journal, row, key):
    adapter, Assistant, Tool, ToolResult, User = runtime()
    stream = row["mode"] == "stream"
    tools = [Tool(name="add", description="Add two integers locally.", parameters={
        "type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
        "required": ["a", "b"], "additionalProperties": False})]
    messages = [User(content="Call the add tool with a=2 and b=3. Do not calculate yourself. After receiving its tool result, reply with only the numeric result.")]
    call = None
    for turn in (1, 2):
        meter = MeteredAdapter(journal, row["site"], stream, turn, call, expected_key=key)
        parsed = None
        try:
            with transport_for(meter), adapter.timing_context():
                result = adapter._invoke(MODEL, {"api_key": key, "endpoint_url": SITES[row["site"]]},
                                         messages, {"max_tokens": MAX_TOKENS}, tools if turn == 1 else None,
                                         stream=stream)
                if stream:
                    chunks = list(result)  # Actually consume the SDK's SSE parser.
                    parsed = Assistant(content="".join(c.delta.message.content or "" for c in chunks),
                                       tool_calls=[t for c in chunks for t in c.delta.message.tool_calls])
                else:
                    parsed = result.message
        finally:
            # Persist safe observations even if parsing or any later assertion fails.
            diagnostic = meter.trace.diagnostics((parsed.content or "") if parsed else None,
                                                 parsed is not None)
            diagnostic.update(turn=turn, request_dispatched=meter.dispatched)
            row.setdefault("diagnostics", []).append(diagnostic)
            journal.save()
        trace = meter.trace
        trace.check_finish(final=turn == 2)
        if turn == 1:
            require(bool(trace.calls), "no_structured_tool_call")
            require(len(parsed.tool_calls) == 1, "sdk_tool_parse_mismatch")
            tool_call = parsed.tool_calls[0]
            raw = trace.calls[0]
            require(bool(raw["id"]) and tool_call.id == raw["id"]
                    and tool_call.type == "function" and tool_call.function.name == raw["name"] == "add"
                    and tool_call.function.arguments == raw["arguments"], "sdk_tool_parse_mismatch")
            arguments = json.loads(raw["arguments"])
            require(arguments == {"a": 2, "b": 3}
                    and all(type(v) is int for v in arguments.values()), "unexpected_tool_arguments")
            # The only local tool execution; never eval/execute model-provided code.
            value = arguments["a"] + arguments["b"]
            call = tool_call.model_dump()
            messages.extend([parsed, ToolResult(content=str(value), tool_call_id=tool_call.id)])
            row["evidence"].append({"turn": 1, "structured_upstream_and_sdk_match": True,
                                    "tool_id_sha256": hashlib.sha256(raw["id"].encode()).hexdigest(),
                                    "local_add_executed": True, "local_result": value,
                                    "tool_fragment_count": trace.fragments,
                                    "response_sha256": trace.digest.hexdigest(), "usage": trace.usage})
        else:
            require(not trace.calls and not parsed.tool_calls, "unexpected_followup_tool_call")
            require(diagnostic["final_answer_matches"], "final_answer_not_confirmed")
            require(diagnostic["answer_mapping_unambiguous"], "ambiguous_sdk_answer_mapping")
            require(diagnostic["sdk_output_matches_expected"], "sdk_answer_mapping_mismatch")
            row["evidence"].append({"turn": 2, "history_id_verified_at_send": True,
                                    "final_answer_verified": True, "response_sha256": trace.digest.hexdigest(),
                                    "usage": trace.usage})
        journal.save()
    row.update(status="pass", reason="single_tool_roundtrip_verified")


def run_round(journal, keys):
    for row in journal.data["results"]:
        # Rows are ordered: both nonstream, then both stream. Stop on ANY uncertainty.
        try:
            check_pair(journal, row, keys[row["site"]])
        except Halt as exc:
            row.update(status="inconclusive", reason=str(exc))
        except Exception as exc:
            # Do not log exception text: SDK/server exceptions may include secrets.
            row.update(status="inconclusive", reason="unexpected_sdk_or_payload_error")
            row["error_category"] = next((name for cls, name in (
                (KeyError, "missing_response_field"), (ValueError, "invalid_value_or_payload"),
                (TypeError, "unexpected_value_type"), (AttributeError, "unexpected_object_shape"))
                if isinstance(exc, cls)), "other_sdk_error")
        row["request_attempts"] = sum(a["site"] == row["site"] and a["mode"] == row["mode"]
                                      for a in journal.data["attempts"])
        journal.save()
        if row["status"] != "pass":
            for pending in journal.data["results"]:
                if pending["status"] == "not_run":
                    pending["reason"] = "paused_after_previous_result"
                    pending["request_attempts"] = 0
            journal.save()
            break


def read_credentials_pipe(stream):
    require(not stream.isatty(), "credentials_require_non_echo_pipe")
    try:
        data = json.loads(stream.read(8193))
    except (ValueError, TypeError):
        raise Halt("invalid_credential_input") from None
    require(isinstance(data, dict) and set(data) == set(SITES), "invalid_credential_input")
    require(all(isinstance(value, str) and 0 < len(value.strip()) <= 512
                and "\n" not in value and "\r" not in value for value in data.values()),
            "invalid_credential_input")
    return {site: value.strip() for site, value in data.items()}


def main():
    require(sys.version_info[:2] == (3, 12) and sys.prefix != sys.base_prefix, "isolated_python312_required")
    require(importlib.metadata.version("dify_plugin") == "0.9.0", "sdk090_required")
    resume = sys.argv[1:] == ["--credentials-stdin", "--resume-stream"]
    require(resume or sys.argv[1:] == ["--credentials-stdin"], "credentials_stdin_flag_required")
    output_report = RESUME_REPORT if resume else REPORT
    require(not output_report.exists(), "existing_report_do_not_reset_request_budget")
    sys.path.insert(0, str(ROOT))
    sys.dont_write_bytecode = True
    # No raw SDK error/HTTP logs, including traceback and request authentication.
    logging.disable(logging.CRITICAL)
    import dify_plugin

    print("qwen3.6-plus ONLY. " + ("Resume: at most 4 new requests from attempt 7. " if resume else "Planned 8 requests. ")
          + "Cumulative hard maximum 10; no retries or redirects.")
    print("No .env reads. No raw replies, keys or headers in the report.")
    print("Authorized budget: China CNY 10; overseas USD 2. No platform billing cap claimed.")
    keys = {}
    try:
        keys = read_credentials_pipe(sys.stdin)
        journal = Journal(output_report, parent_path=REPORT if resume else None,
                          expected_parent_sha256=ORIGINAL_REPORT_SHA256 if resume else None)
        journal.data["sdk_path"] = dify_plugin.__file__
        run_round(journal, keys)
        journal.save()
        print("New request attempts:", len(journal.data["attempts"]))
        print("Cumulative request attempts:", journal.total_attempts)
        for row in journal.data["results"]:
            print(row["site"], row["mode"], row["status"], row["reason"])
        print("Sanitized report:", output_report)
    finally:
        keys.clear()


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("Cancelled. No automatic retry.")
    except Halt as exc:
        print("Stopped:", str(exc))
        sys.exit(1)
    except Exception:
        print("Stopped: unexpected local error. Raw exception suppressed to protect credentials.")
        sys.exit(1)
