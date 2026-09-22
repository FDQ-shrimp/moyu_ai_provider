"""Offline orchestration checks for the Batch 2 non-stream continuation."""
from __future__ import annotations

import hashlib
import json

import pytest

from scripts import verify_fc_expansion_batch2_nonstream_resume as resume
from scripts import verify_fc_live as live


def make_history(tmp_path, monkeypatch):
    parent = tmp_path / "batch2.json"
    parent.write_text(
        json.dumps(
            {
                "request_attempts": 17,
                "halted": True,
                "halt_reason": "transport_error_no_retry",
            }
        ),
        encoding="utf-8",
    )
    retest = tmp_path / "gemini-retest.json"
    retest.write_text(
        json.dumps(
            {
                "request_attempts": 1,
                "result": {
                    "model": "gemini-2.5-pro",
                    "status": "inconclusive",
                    "reason": "transport_error_no_retry",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(resume, "PARENT", parent)
    monkeypatch.setattr(resume, "PARENT_SHA256", hashlib.sha256(parent.read_bytes()).hexdigest())
    monkeypatch.setattr(resume, "GEMINI_RETEST", retest)
    monkeypatch.setattr(
        resume,
        "GEMINI_RETEST_SHA256",
        hashlib.sha256(retest.read_bytes()).hexdigest(),
    )
    return resume.Journal(tmp_path / "resume.json")


@pytest.fixture
def journal(tmp_path, monkeypatch):
    return make_history(tmp_path, monkeypatch)


def test_scope_and_twenty_request_limit_are_exact(journal):
    assert resume.SCHEDULE == {
        "glm-5.2": ("china", "overseas"),
        "gpt-5.6-sol": ("china", "overseas"),
        "kimi-k2.6": ("china", "overseas"),
        "qwen3.6-flash": ("china", "overseas"),
        "qwen-plus": ("china",),
        "doubao-seed-2-0-pro-260215": ("china",),
    }
    assert journal.data["max_attempts"] == 20
    assert len(journal.data["results"]) == 10
    assert journal.data["mode"] == "nonstream"
    assert journal.data["automatic_retries"] is False
    assert journal.data["redirects"] is False
    assert journal.data["model_listing"] is False
    assert journal.data["credential_probing"] is False


def test_scope_rejects_stream_other_model_and_overseas_for_china_only(journal):
    live.MODEL = "qwen-plus"
    with pytest.raises(live.Halt, match="resume_scope_exceeded"):
        journal.begin_attempt("china", True, 1)
    with pytest.raises(live.Halt, match="resume_scope_exceeded"):
        journal.begin_attempt("overseas", False, 1)
    live.MODEL = "gemini-2.5-pro"
    with pytest.raises(live.Halt, match="resume_scope_exceeded"):
        journal.begin_attempt("china", False, 1)


def test_outcomes_separate_protocol_from_strict_final_text(journal):
    row = resume.result(journal, "glm-5.2", "china")
    row.update(status="inconclusive", reason="final_answer_not_confirmed")
    row["evidence"] = [
        {
            "turn": 1,
            "structured_upstream_and_sdk_match": True,
            "local_add_executed": True,
            "local_result": 5,
        }
    ]
    row["diagnostics"] = [
        {"turn": 1},
        {
            "turn": 2,
            "sdk_parse_completed": True,
            "sdk_output_matches_expected": True,
            "finish_reason": "stop",
            "final_answer_matches": False,
        },
    ]
    journal.data["attempts"] = [
        {"model": row["model"], "site": row["site"], "turn": 1},
        {
            "model": row["model"],
            "site": row["site"],
            "turn": 2,
            "request_protocol_validated": True,
            "http_status": 200,
        },
    ]
    resume.annotate_outcomes(journal, row)
    assert row["tool_protocol_status"] == "pass"
    assert row["strict_final_text_status"] == "fail"
    assert row["strict_final_answer_matches"] is False


def test_single_model_timeout_continues_but_second_model_same_site_stops(journal, monkeypatch):
    def fake_check(_journal, row, _key):
        if row["site"] == "china" and row["model"] in {"glm-5.2", "gpt-5.6-sol"}:
            raise live.Halt("transport_error_no_retry")
        row.update(status="pass", reason="single_tool_roundtrip_verified")

    monkeypatch.setattr(live, "check_pair", fake_check)
    resume.run_batch(journal, {site: "offline-fake-key" for site in live.SITES})
    assert resume.result(journal, "glm-5.2", "overseas")["status"] == "pass"
    assert journal.data["halted"] is True
    assert journal.data["halt_reason"] == "multiple_models_common_infrastructure_error"
    assert resume.result(journal, "kimi-k2.6", "china")["status"] == "not_run"


def test_authentication_error_stops_immediately(journal, monkeypatch):
    monkeypatch.setattr(
        live,
        "check_pair",
        lambda *_: (_ for _ in ()).throw(live.Halt("authentication_or_permission")),
    )
    resume.run_batch(journal, {site: "offline-fake-key" for site in live.SITES})
    assert journal.data["halted"] is True
    assert journal.data["halt_reason"] == "authentication_or_permission"


@pytest.mark.parametrize("model", resume.SCHEDULE)
def test_every_candidate_is_one_registered_runtime_model(model):
    old = live.MODEL
    try:
        live.MODEL = model
        adapter, *_ = live.runtime()
        assert adapter.model_schemas[0].model == model
    finally:
        live.MODEL = old
