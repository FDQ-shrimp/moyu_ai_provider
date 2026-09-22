"""Offline scope, cap, gating and resume checks for full remaining validation."""
from __future__ import annotations

import hashlib
import json

import pytest

from scripts import verify_fc_full_remaining as full
from scripts import verify_fc_live as live


def fake_parents(tmp_path, monkeypatch):
    parents = {}
    for name in full.PARENTS:
        path = tmp_path / f"{name}.json"
        path.write_text("{}", encoding="utf-8")
        parents[name] = (path, hashlib.sha256(path.read_bytes()).hexdigest())
    monkeypatch.setattr(full, "PARENTS", parents)


@pytest.fixture
def journal(tmp_path, monkeypatch):
    fake_parents(tmp_path, monkeypatch)
    return full.Journal(tmp_path / "progress.json")


def test_exact_plan_counts_caps_and_exclusions(journal):
    assert full.LIMIT == 320
    assert full.SITE_LIMITS == {"china": 178, "overseas": 142}
    assert full.BUDGET["china"]["limit"] == 100
    assert full.BUDGET["overseas"]["limit"] == 20
    assert len(journal.data["results"]) == 160
    assert sum(row["site"] == "china" for row in journal.data["results"]) == 89
    assert sum(row["site"] == "overseas" for row in journal.data["results"]) == 71
    planned = {row["model"] for row in journal.data["results"]}
    assert len(planned) == 49
    assert planned.isdisjoint(full.EXCLUDED)
    assert "gemini-2.5-pro" not in planned
    assert "claude-sonnet-4-5-20250929" not in planned


def test_only_batch2_stream_is_scheduled(journal):
    rows = [row for row in journal.data["results"] if row["batch"] == 2]
    assert len(rows) == 16
    assert {row["mode"] for row in rows} == {"stream"}
    assert {row["model"] for row in rows} == set(full.BATCH2_STREAM)


def test_china_only_models_never_schedule_overseas(journal):
    china_only = {
        "qwen-plus",
        "doubao-seed-2-0-pro-260215",
        "DeepSeek-R1-0528",
        "qwen3-max",
        "DeepSeek-V3-0324",
        "GLM-5",
        "doubao-seed-2-0-code-preview-260215",
        "doubao-seed-2-0-lite-260215",
        "qwen3-vl-plus",
        "doubao-seed-2-0-mini-260215",
    }
    assert all(
        row["site"] == "china"
        for row in journal.data["results"]
        if row["model"] in china_only
    )


def test_nonstream_gate_requires_protocol_and_strict_text(journal):
    sites = full.BATCHES[3]["MiniMax-M3"]
    for site in sites:
        row = full.find_result(journal, 3, "MiniMax-M3", site, "nonstream")
        row.update(tool_protocol_status="pass", strict_final_text_status="pass")
    assert all(
        full.accepted(full.find_result(journal, 3, "MiniMax-M3", site, "nonstream"))
        for site in sites
    )
    full.find_result(journal, 3, "MiniMax-M3", "overseas", "nonstream")[
        "strict_final_text_status"
    ] = "fail"
    assert not all(
        full.accepted(full.find_result(journal, 3, "MiniMax-M3", site, "nonstream"))
        for site in sites
    )


def test_scope_and_site_request_caps_are_enforced(journal):
    row = full.find_result(journal, 2, "qwen-plus", "china", "stream")
    live.MODEL = row["model"]
    journal.begin_attempt("china", True, 1)
    journal.begin_attempt("china", True, 2)
    with pytest.raises(live.Halt, match="unexpected_retry_or_turn"):
        journal.begin_attempt("china", True, 2)
    live.MODEL = "gemini-2.5-pro"
    with pytest.raises(live.Halt, match="request_scope_exceeded"):
        journal.begin_attempt("china", False, 1)


def test_resume_marks_interrupted_row_without_repeating(tmp_path, monkeypatch):
    fake_parents(tmp_path, monkeypatch)
    path = tmp_path / "progress.json"
    journal = full.Journal(path)
    row = full.find_result(journal, 2, "qwen-plus", "china", "stream")
    live.MODEL = row["model"]
    journal.begin_attempt("china", True, 1)
    resumed = full.Journal(path, resume=True)
    row = full.find_result(resumed, 2, "qwen-plus", "china", "stream")
    assert row["status"] == "inconclusive"
    assert row["reason"] == "interrupted_after_recorded_dispatch"
    assert row["request_attempts"] == 1


def test_common_infrastructure_stop_requires_two_models_same_site(journal):
    first = full.find_result(journal, 2, "claude-haiku-4-5-20251001", "china", "stream")
    second = full.find_result(journal, 2, "claude-opus-4-6", "china", "stream")
    for number, row in enumerate((first, second), 1):
        row.update(status="inconclusive", reason="transport_error_no_retry")
        journal.data["attempts"].append(
            {
                "number": number,
                "batch": row["batch"],
                "model": row["model"],
                "site": row["site"],
                "mode": row["mode"],
                "turn": 1,
                "error_category": "read_timeout",
                "transport_stage": "wait_response_headers",
            }
        )
    assert full.apply_stop_policy(journal, first) is False
    assert full.apply_stop_policy(journal, second) is True
    assert journal.data["halt_reason"] == (
        "multiple_models_consecutive_common_infrastructure_error"
    )


@pytest.mark.parametrize(
    "model",
    sorted(set(full.BATCH2_STREAM) | {model for batch in full.BATCHES.values() for model in batch}),
)
def test_every_planned_model_is_one_registered_runtime_model(model):
    old = live.MODEL
    try:
        live.MODEL = model
        adapter, *_ = live.runtime()
        assert adapter.model_schemas[0].model == model
    finally:
        live.MODEL = old
