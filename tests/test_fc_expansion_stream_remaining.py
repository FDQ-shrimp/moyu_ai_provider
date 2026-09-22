"""Offline scope and orchestration tests for the Batch 1 stream continuation."""
from __future__ import annotations

import hashlib
import json

import pytest

from scripts import verify_fc_expansion_stream_remaining as continuation
from scripts import verify_fc_live as live


def make_parents(tmp_path, monkeypatch):
    batch = tmp_path / "batch.json"
    batch.write_text(json.dumps({"results": [
        {"model": model, "site": site, "mode": mode,
         "status": "pass" if mode == "nonstream" else "not_run"}
        for model in continuation.MODELS for mode in ("nonstream", "stream") for site in live.SITES
    ]}), encoding="utf-8")
    glm = tmp_path / "glm.json"
    glm.write_text(json.dumps({"scope": {"model": "glm-5.3"},
                               "result": {"status": "pass"}, "request_attempts": 2}), encoding="utf-8")
    monkeypatch.setattr(continuation, "BATCH_REPORT", batch)
    monkeypatch.setattr(continuation, "BATCH_SHA256", hashlib.sha256(batch.read_bytes()).hexdigest())
    monkeypatch.setattr(continuation, "GLM_RETEST_REPORT", glm)
    monkeypatch.setattr(continuation, "GLM_RETEST_SHA256", hashlib.sha256(glm.read_bytes()).hexdigest())
    monkeypatch.setattr(continuation, "REPORT", tmp_path / "continuation.json")
    return continuation.Journal()


def test_scope_is_exactly_two_models_two_sites_stream_and_eight_requests(tmp_path, monkeypatch):
    journal = make_parents(tmp_path, monkeypatch)
    assert continuation.MODELS == ("gemini-2.5-flash", "gpt-5.5")
    assert len(journal.data["results"]) == 4 and journal.data["max_attempts"] == 8
    assert all(row["mode"] == "stream" for row in journal.data["results"])
    assert journal.data["automatic_retries"] is False and journal.data["redirects"] is False
    assert journal.data["model_listing"] is False and journal.data["credential_probing"] is False


def test_protocol_failure_continues_but_systemic_failure_halts(tmp_path, monkeypatch):
    journal = make_parents(tmp_path, monkeypatch)
    calls = []

    def check(_journal, row, _key):
        calls.append((row["model"], row["site"]))
        if len(calls) == 1:
            raise live.Halt("no_structured_tool_call")
        if len(calls) == 3:
            raise live.Halt("authentication_or_permission")
        row.update(status="pass", reason="single_tool_roundtrip_verified")

    monkeypatch.setattr(live, "check_pair", check)
    continuation.run(journal, {site: "offline-fake-key" for site in live.SITES})
    assert calls == [("gemini-2.5-flash", "china"),
                     ("gemini-2.5-flash", "overseas"), ("gpt-5.5", "china")]
    assert journal.data["halted"] is True
    assert continuation.result(journal, "gpt-5.5", "overseas")["reason"] == \
        "batch_halted_after_systemic_error"


def test_attempt_scope_and_no_retry(tmp_path, monkeypatch):
    journal = make_parents(tmp_path, monkeypatch)
    live.MODEL = continuation.MODELS[0]
    journal.begin_attempt("china", True, 1)
    journal.begin_attempt("china", True, 2)
    with pytest.raises(live.Halt, match="unexpected_retry_or_turn"):
        journal.begin_attempt("china", True, 2)
    with pytest.raises(live.Halt, match="continuation_scope_exceeded"):
        journal.begin_attempt("china", False, 1)


def test_parent_hash_change_blocks_dispatch(tmp_path, monkeypatch):
    journal = make_parents(tmp_path, monkeypatch)
    continuation.BATCH_REPORT.write_text("changed", encoding="utf-8")
    live.MODEL = continuation.MODELS[0]
    with pytest.raises(live.Halt, match="batch_report_hash_mismatch"):
        journal.begin_attempt("china", True, 1)
