"""Offline checks for the live runner; no credentials or live connections."""
import json
import io
import hashlib

import pytest
import requests

from scripts import verify_fc_live as live
from tests.test_llm_sdk_contract import completion, response, sse_response


@pytest.fixture
def journal(tmp_path):
    return live.Journal(tmp_path / "report.json")


@pytest.fixture
def wire(monkeypatch):
    pending, captured = [], []

    def dispatch(session, request, **kwargs):
        assert session.trust_env is False
        assert kwargs["allow_redirects"] is False
        assert kwargs["timeout"] == (10, 60)
        return session.get_adapter(request.url).send(request, **kwargs)

    def adapter_send(adapter, request, **kwargs):
        retry = adapter.max_retries
        assert all(getattr(retry, k) == 0 for k in ("total", "connect", "read", "redirect", "status", "other"))
        captured.append((request.url, json.loads(request.body)))
        assert pending, "Unexpected request"
        item = pending.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    # Offline safety blocks Session.send. This local dispatcher only reaches the
    # fake HTTPAdapter transport below; the irreversible socket audit remains on.
    monkeypatch.setattr(requests.sessions.Session, "send", dispatch)
    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", adapter_send)
    yield pending, captured


def queue_pair(pending, stream=False):
    pending.extend([sse_response() if stream else response(completion()),
                    sse_response(tool_call=False) if stream else response(completion(tool_call=False, content="5"))])
    if stream:
        pending[-1]._content = pending[-1]._content.replace(b'"hel"', b'"5"').replace(b'"lo"', b'""')


def test_full_live_plan_through_real_plugin_and_sdk_offline(journal, wire):
    pending, sent = wire
    for streaming in (False, False, True, True):
        queue_pair(pending, streaming)
    live.run_round(journal, {s: "offline-fake-key" for s in live.SITES})
    assert len(sent) == len(journal.data["attempts"]) == 8
    assert [r["status"] for r in journal.data["results"]] == ["pass"] * 4
    assert [r["mode"] for r in journal.data["attempts"]] == ["nonstream"] * 4 + ["stream"] * 4
    for row in journal.data["results"]:
        assert row["evidence"][0]["local_add_executed"]
        assert row["evidence"][1]["history_id_verified_at_send"]
        assert row["evidence"][1]["final_answer_verified"]
    saved = journal.path.read_text()
    assert "offline-fake-key" not in saved and "Authorization" not in saved
    assert "call_add_1" not in saved  # Hash only, not arbitrary upstream strings.
    assert not pending


@pytest.mark.parametrize("status, reason", [(401, "authentication_or_permission"), (402, "quota_or_balance"),
                                          (429, "rate_limit_or_quota"), (404, "model_or_endpoint_not_found"),
                                          (500, "upstream_system_error"), (307, "redirect_blocked")])
def test_error_stops_without_retry_or_next_site(journal, wire, status, reason):
    reply = response({"error": "sensitive arbitrary text must not be logged"})
    reply.status_code = status
    wire[0].append(reply)
    live.run_round(journal, {s: "offline-fake-key" for s in live.SITES})
    assert len(wire[1]) == len(journal.data["attempts"]) == 1
    assert journal.data["results"][0]["reason"] == reason
    assert all(r["status"] == "not_run" for r in journal.data["results"][1:])
    assert "sensitive arbitrary" not in journal.path.read_text()


def test_plain_five_is_not_tool_success(journal, wire):
    wire[0].append(response(completion(tool_call=False, content="5")))
    live.run_round(journal, {s: "offline-fake-key" for s in live.SITES})
    assert journal.data["results"][0]["reason"] == "no_structured_tool_call"
    assert journal.data["results"][0]["status"] == "inconclusive"
    assert len(wire[1]) == 1


def test_truncation_is_not_unsupported(journal, wire):
    payload = completion()
    payload["choices"][0]["finish_reason"] = "length"
    wire[0].append(response(payload))
    live.run_round(journal, {s: "offline-fake-key" for s in live.SITES})
    assert journal.data["results"][0]["reason"] == "truncated"
    assert len(wire[1]) == 1


def test_overseas_nonstream_failure_prevents_all_streaming(journal, wire):
    queue_pair(wire[0])
    wire[0].append(response(completion(tool_call=False, content="5")))
    live.run_round(journal, {s: "offline-fake-key" for s in live.SITES})
    assert len(wire[1]) == 3
    assert [r["status"] for r in journal.data["results"]] == ["pass", "inconclusive", "not_run", "not_run"]


def test_timeout_attempt_is_counted_and_persisted(journal, wire):
    wire[0].append(requests.exceptions.Timeout("secret-looking-value"))
    live.run_round(journal, {s: "offline-fake-key" for s in live.SITES})
    saved = json.loads(journal.path.read_text())
    assert len(saved["attempts"]) == 1
    assert saved["attempts"][0]["outcome"] == "transport_error_no_retry"
    assert saved["attempts"][0]["exception_type"] == "Timeout"
    assert saved["attempts"][0]["headers_received"] is False
    assert saved["attempts"][0]["transport_stage"] == "before_response_headers"
    assert saved["attempts"][0]["elapsed_ms"] >= 0
    assert "secret-looking-value" not in journal.path.read_text()


@pytest.mark.parametrize("exception,kind,category,stage", [
    (requests.exceptions.ConnectTimeout("secret-connect"), "ConnectTimeout", "connect_timeout", "connect"),
    (requests.exceptions.ReadTimeout("secret-read"), "ReadTimeout", "read_timeout", "wait_response_headers"),
])
def test_specific_timeout_before_headers_is_safely_classified(
        journal, wire, exception, kind, category, stage):
    wire[0].append(exception)
    live.run_round(journal, {s: "offline-fake-key" for s in live.SITES})
    saved = json.loads(journal.path.read_text())["attempts"][0]
    assert saved["exception_type"] == kind and saved["error_category"] == category
    assert saved["headers_received"] is False and saved["transport_stage"] == stage
    assert "secret-connect" not in journal.path.read_text()
    assert "secret-read" not in journal.path.read_text()


def test_stream_read_timeout_after_headers_is_safely_classified(journal, wire):
    reply = sse_response()

    def broken_lines(*_args, **_kwargs):
        raise requests.exceptions.ReadTimeout("secret-stream-read")
        yield  # pragma: no cover - keep this function a generator

    reply.iter_lines = broken_lines
    wire[0].append(reply)
    row = journal.data["results"][2]
    with pytest.raises(live.Halt, match="^transport_error_no_retry$"):
        live.check_pair(journal, row, "offline-fake-key")
    saved = json.loads(journal.path.read_text())["attempts"][0]
    assert saved["http_status"] == 200 and saved["headers_received"] is True
    assert saved["exception_type"] == "ReadTimeout" and saved["error_category"] == "read_timeout"
    assert saved["transport_stage"] == "sse_body_read_after_headers"
    assert saved["elapsed_to_headers_ms"] >= 0 and saved["elapsed_after_headers_ms"] >= 0
    assert "secret-stream-read" not in journal.path.read_text()


def test_tenth_attempt_allowed_eleventh_blocked_at_send(journal, wire):
    for _ in range(9):
        journal.begin_attempt("china", False, 1)
    queue_pair(wire[0])
    live.run_round(journal, {s: "offline-fake-key" for s in live.SITES})
    assert len(journal.data["attempts"]) == 10
    assert len(wire[1]) == 1
    assert journal.data["results"][0]["reason"] == "request_cap_reached"


def test_existing_report_cannot_reset_budget(journal):
    with pytest.raises(FileExistsError):
        live.Journal(journal.path)


def test_wrong_destination_blocked_before_count_or_send(journal, wire):
    meter = live.MeteredAdapter(journal, "china", False, 1)
    prepared = requests.Request("POST", "https://unapproved.invalid/", json={}).prepare()
    with pytest.raises(live.Halt, match="unapproved_destination"):
        meter.send(prepared)
    assert not journal.data["attempts"] and not wire[1]


def test_history_mismatch_blocked_before_second_send(journal, wire):
    meter = live.MeteredAdapter(journal, "china", False, 2, {"id": "expected"})
    prepared = requests.Request("POST", live.SITES["china"] + "/chat/completions", json={
        "model": live.MODEL, "stream": False, "max_tokens": live.MAX_TOKENS,
        "messages": [{"role": "assistant", "tool_calls": []}, {"role": "tool", "tool_call_id": "wrong"}]}).prepare()
    with pytest.raises(live.Halt, match="tool_history_mismatch"):
        meter.send(prepared)
    assert not journal.data["attempts"] and not wire[1]


def test_noninteractive_credentials_pipe_does_not_prompt_or_print(capsys):
    keys = live.read_credentials_pipe(io.StringIO(json.dumps({"china": " fake-cn ", "overseas": "fake-intl"})))
    assert keys == {"china": "fake-cn", "overseas": "fake-intl"}
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("payload", ['not json', '{}', '{"china":"fake"}',
                                     '{"china":"", "overseas":"fake"}'])
def test_bad_noninteractive_credentials_fail_without_disclosure(payload):
    with pytest.raises(live.Halt, match="^invalid_credential_input$"):
        live.read_credentials_pipe(io.StringIO(payload))


def test_wrong_site_key_blocked_before_send(journal, wire):
    meter = live.MeteredAdapter(journal, "china", False, 1, expected_key="fake-domestic")
    prepared = requests.Request("POST", live.SITES["china"] + "/chat/completions",
                                headers={"Authorization": "Bearer fake-overseas"}, json={}).prepare()
    with pytest.raises(live.Halt, match="site_credential_mismatch"):
        meter.send(prepared)
    assert not journal.data["attempts"] and not wire[1]


def test_budget_record_does_not_claim_platform_cap(journal):
    assert journal.data["budget"]["china"]["limit"] == 10
    assert journal.data["budget"]["overseas"]["limit"] == 2
    assert journal.data["budget"]["platform_hard_limit_verified"] is False
    assert journal.data["cost_estimate"] is None


def test_sdk_reasoning_wrapper_is_verified_without_deleting_text(journal, wire):
    # Characterization, not a claim about the unsaved live sixth response:
    # upstream final content is 5, but SDK combines reasoning with the answer.
    queue_pair(wire[0], stream=True)
    reasoning = {"id": "offline-stream", "model": live.MODEL, "choices": [{
        "index": 0, "delta": {"reasoning_content": "Use the returned tool result."},
        "finish_reason": None}]}
    wire[0][-1]._content = ("data: " + json.dumps(reasoning) + "\n\n").encode() + wire[0][-1]._content
    row = journal.data["results"][2]
    live.check_pair(journal, row, "offline-fake-key")
    assert len(wire[1]) == 2
    assert row["status"] == "pass"
    assert row["evidence"][0]["local_add_executed"] is True


def final_sse(deltas, finish="stop", usage=None):
    chunks = [{"id": "offline-only", "model": live.MODEL,
               "choices": [{"index": 0, "delta": delta, "finish_reason": None}]}
              for delta in deltas]
    chunks.append({"id": "offline-only", "model": live.MODEL,
                   "choices": [{"index": 0, "delta": {}, "finish_reason": finish}],
                   "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
                   if usage is None else usage})
    reply = response({})
    reply.headers["Content-Type"] = "text/event-stream"
    reply._content = ("".join("data: " + json.dumps(c) + "\n\n" for c in chunks)
                      + "data: [DONE]\n\n").encode()
    return reply


@pytest.mark.parametrize("deltas,finish,reason,answer_match", [
    ([{"reasoning_content": "private reasoning"}, {"content": "5"}], "stop", None, True),
    ([{"reasoning_content": "private reasoning says 5"}, {"content": "6"}], "stop", "final_answer_not_confirmed", False),
    ([{"reasoning_content": "private reasoning says 5"}], "stop", "final_answer_not_confirmed", False),
    ([{"content": "5"}], "length", "truncated", True),
    ([{"content": "5"}], "stop", None, True),
    ([{"reasoning_content": "private "}, {"reasoning_content": "reasoning 5"},
      {"content": "\n"}, {"content": "5"}, {"content": "\n"}], "stop", None, True),
    ([{"content": "<think>5</think>6"}], "stop", "final_answer_not_confirmed", False),
    ([{"reasoning_content": "private reasoning", "content": "5"}], "stop", "ambiguous_sdk_answer_mapping", True),
])
def test_stream_answer_separation_and_saved_diagnostics(journal, wire, deltas, finish, reason, answer_match):
    wire[0].extend([sse_response(), final_sse(deltas, finish)])
    row = journal.data["results"][2]
    if reason is None:
        live.check_pair(journal, row, "offline-fake-key")
        assert row["status"] == "pass"
    else:
        with pytest.raises(live.Halt, match="^" + reason + "$"):
            live.check_pair(journal, row, "offline-fake-key")
    saved = json.loads(journal.path.read_text())["results"][2]["diagnostics"][-1]
    assert saved["final_answer_matches"] is answer_match
    assert saved["reasoning_field_present"] is any("reasoning_content" in d for d in deltas)
    assert saved["finish_reason"] == finish
    assert saved["sdk_parse_completed"] is True
    assert saved["usage"]["total_tokens"] == 15
    assert len(saved["response_sha256"]) == 64
    assert "private reasoning" not in journal.path.read_text()
    if reason is None:
        assert saved["sdk_output_matches_expected"] is True
        assert saved["answer_mapping_unambiguous"] is True


def test_sdk_parse_failure_retains_diagnostics_and_unknown_usage(journal, wire):
    # Malformed usage fails inside the real SDK without triggering tokenizer downloads.
    wire[0].extend([sse_response(), final_sse([{"content": "5"}], usage={"prompt_tokens": 10, "completion_tokens": "invalid"})])
    row = journal.data["results"][2]
    with pytest.raises(TypeError):
        live.check_pair(journal, row, "offline-fake-key")
    saved = json.loads(journal.path.read_text())["results"][2]["diagnostics"][-1]
    assert saved["final_answer_matches"] is True
    assert saved["sdk_parse_completed"] is False
    assert saved["sdk_output_matches_expected"] is None
    assert saved["usage"] == {"prompt_tokens": 10, "completion_tokens": None, "total_tokens": None}


def test_sdk_text_mismatch_is_not_accepted():
    trace = live.Trace()
    trace.observe({"choices": [{"index": 0, "delta": {"content": "5"}, "finish_reason": "stop"}]}, True)
    assert trace.diagnostics("6", True)["sdk_output_matches_expected"] is False
    assert trace.diagnostics("6", True)["usage"] == {
        "prompt_tokens": None, "completion_tokens": None, "total_tokens": None}


@pytest.fixture
def historical_report(tmp_path):
    history = live.Journal(tmp_path / "history.json")
    for site, stream in (("china", False), ("overseas", False), ("china", True)):
        for turn in (1, 2):
            history.begin_attempt(site, stream, turn)
    for row, status in zip(history.data["results"], ("pass", "pass", "inconclusive", "not_run")):
        row["status"] = status
    history.save()
    return history.path, hashlib.sha256(history.path.read_bytes()).hexdigest()


def test_stream_resume_preserves_original_and_starts_at_seven(tmp_path, wire, historical_report):
    path, digest = historical_report
    original = path.read_bytes()
    resumed = live.Journal(tmp_path / "resume.json", parent_path=path, expected_parent_sha256=digest)
    assert resumed.total_attempts == 6
    assert all(r["mode"] == "stream" for r in resumed.data["results"])
    queue_pair(wire[0], True)
    queue_pair(wire[0], True)
    live.run_round(resumed, {s: "offline-fake-key" for s in live.SITES})
    assert [a["number"] for a in resumed.data["attempts"]] == [7, 8, 9, 10]
    assert resumed.total_attempts == 10
    assert len(wire[1]) == 4
    with pytest.raises(live.Halt, match="request_cap_reached"):
        resumed.begin_attempt("overseas", True, 2)
    assert path.read_bytes() == original
    assert json.loads(original)["results"][2]["status"] == "inconclusive"


def test_resume_rejects_wrong_parent_hash(tmp_path, historical_report):
    with pytest.raises(live.Halt, match="parent_report_hash_mismatch"):
        live.Journal(tmp_path / "resume.json", parent_path=historical_report[0], expected_parent_sha256="invalid")
    assert not (tmp_path / "resume.json").exists()


def test_resume_pauses_after_china_inconclusive(tmp_path, wire, historical_report):
    resumed = live.Journal(tmp_path / "resume.json", parent_path=historical_report[0],
                           expected_parent_sha256=historical_report[1])
    wire[0].append(sse_response(tool_call=False))
    live.run_round(resumed, {s: "offline-fake-key" for s in live.SITES})
    assert resumed.total_attempts == 7 and len(wire[1]) == 1
    assert resumed.data["results"][1]["status"] == "not_run"


def test_parent_changed_after_start_blocks_dispatch(tmp_path, historical_report):
    path, digest = historical_report
    resumed = live.Journal(tmp_path / "resume.json", parent_path=path, expected_parent_sha256=digest)
    # This is a temporary synthetic history fixture, never the real report.
    with path.open("a") as handle:
        handle.write("\n")
    with pytest.raises(live.Halt, match="parent_report_hash_mismatch"):
        resumed.begin_attempt("china", True, 1)
    assert resumed.total_attempts == 6
