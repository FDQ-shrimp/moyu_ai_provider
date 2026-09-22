"""Offline orchestration checks for expansion batch one."""
from __future__ import annotations

import io

import pytest

from scripts import verify_fc_expansion as expansion
from scripts import verify_fc_live as live


@pytest.fixture
def journal(tmp_path):
    return expansion.Journal(tmp_path / "batch.json")


def test_scope_and_budget_are_exact(journal):
    assert expansion.MODELS == (
        "claude-fable-5", "claude-sonnet-4-6", "deepseek-v4-pro",
        "glm-5.3", "gemini-2.5-flash", "gpt-5.5")
    assert journal.data["existing_verified_model_not_retested"] == "qwen3.6-plus"
    assert journal.data["max_attempts"] == 48
    assert journal.data["budget"]["china"]["limit"] == 30
    assert journal.data["budget"]["overseas"]["limit"] == 6
    assert journal.data["budget"]["platform_hard_limit_verified"] is False


def test_all_nonstream_precedes_stream_and_gate_is_per_model(journal, monkeypatch):
    calls = []

    def fake_check(_journal, row, _key):
        calls.append((row["model"], row["site"], row["mode"]))
        # One ordinary model-specific uncertainty: continue batch, then skip its streams.
        if row["model"] == "glm-5.3" and row["site"] == "overseas":
            raise live.Halt("no_structured_tool_call")
        row.update(status="pass", reason="single_tool_roundtrip_verified")

    monkeypatch.setattr(live, "check_pair", fake_check)
    expansion.run_batch(journal, {site: "offline-fake-key" for site in live.SITES})
    first_stream = next(i for i, item in enumerate(calls) if item[2] == "stream")
    assert all(item[2] == "nonstream" for item in calls[:first_stream])
    assert len(calls[:first_stream]) == len(expansion.MODELS) * 2
    assert not any(model == "glm-5.3" and mode == "stream" for model, _, mode in calls)
    assert expansion.result(journal, "glm-5.3", "china", "stream")["reason"] == \
        "skipped_nonstream_bilateral_gate"
    assert journal.data["halted"] is False


@pytest.mark.parametrize("reason", sorted(expansion.BATCH_STOP_REASONS))
def test_systemic_reason_stops_entire_batch(journal, monkeypatch, reason):
    monkeypatch.setattr(live, "check_pair", lambda *_: (_ for _ in ()).throw(live.Halt(reason)))
    expansion.run_batch(journal, {site: "offline-fake-key" for site in live.SITES})
    assert journal.data["halted"] is True and journal.data["halt_reason"] == reason
    assert all(row["reason"] == "batch_halted_after_systemic_error"
               for row in journal.data["results"] if row["status"] == "not_run")


def test_attempt_counter_is_at_actual_send_boundary_and_forbids_retry(journal):
    live.MODEL = expansion.MODELS[0]
    first = journal.begin_attempt("china", False, 1)
    second = journal.begin_attempt("china", False, 2)
    assert [first["number"], second["number"]] == [1, 2]
    with pytest.raises(live.Halt, match="unexpected_retry_or_turn"):
        journal.begin_attempt("china", False, 2)


def test_credentials_use_one_non_echo_line_and_are_not_saved(journal):
    data = expansion.read_credentials_line(io.StringIO(
        '{"china":"offline-domestic","overseas":"offline-overseas"}\n'))
    assert data == {"china": "offline-domestic", "overseas": "offline-overseas"}
    saved = journal.path.read_text(encoding="utf-8")
    assert "offline-domestic" not in saved and "offline-overseas" not in saved


@pytest.mark.parametrize("model", expansion.MODELS)
def test_every_candidate_is_exactly_one_registered_runtime_model(model):
    old = live.MODEL
    try:
        live.MODEL = model
        adapter, *_ = live.runtime()
        assert adapter.model_schemas[0].model == model
    finally:
        live.MODEL = old
