"""Offline orchestration checks for Function Calling expansion Batch 2."""
from __future__ import annotations

import pytest

from scripts import verify_fc_expansion_batch2 as batch2
from scripts import verify_fc_live as live


@pytest.fixture
def journal(tmp_path):
    return batch2.Journal(tmp_path / "batch2.json")


def test_scope_sites_budget_and_request_cap_are_exact(journal):
    assert len(batch2.SCHEDULE) == 11
    assert set(batch2.SCHEDULE) == {
        "claude-haiku-4-5-20251001",
        "claude-opus-4-6",
        "claude-sonnet-4-5-20250929",
        "deepseek-v4-flash",
        "gemini-2.5-pro",
        "glm-5.2",
        "gpt-5.6-sol",
        "kimi-k2.6",
        "qwen3.6-flash",
        "qwen-plus",
        "doubao-seed-2-0-pro-260215",
    }
    assert batch2.SCHEDULE["qwen-plus"] == ("china",)
    assert batch2.SCHEDULE["doubao-seed-2-0-pro-260215"] == ("china",)
    assert sum(sites == ("china", "overseas") for sites in batch2.SCHEDULE.values()) == 9
    assert journal.data["verified_models_not_retested"] == list(batch2.VERIFIED_NOT_RETESTED)
    assert journal.data["max_attempts"] == 80
    assert journal.data["budget"]["china"]["limit"] == 50
    assert journal.data["budget"]["overseas"]["limit"] == 10
    assert journal.data["budget"]["platform_hard_limit_verified"] is False
    assert len(journal.data["results"]) == 40


def test_all_nonstream_precedes_stream_and_site_gate_is_per_model(journal, monkeypatch):
    calls = []

    def fake_check(_journal, row, _key):
        calls.append((row["model"], row["site"], row["mode"]))
        if row["model"] == "glm-5.2" and row["site"] == "overseas":
            raise live.Halt("no_structured_tool_call")
        row.update(status="pass", reason="single_tool_roundtrip_verified")

    monkeypatch.setattr(live, "check_pair", fake_check)
    batch2.run_batch(journal, {site: "offline-fake-key" for site in live.SITES})
    first_stream = next(index for index, item in enumerate(calls) if item[2] == "stream")
    assert all(item[2] == "nonstream" for item in calls[:first_stream])
    assert len(calls[:first_stream]) == 20
    assert not any(model == "glm-5.2" and mode == "stream" for model, _, mode in calls)
    assert batch2.result(journal, "glm-5.2", "china", "stream")["reason"] == \
        "skipped_nonstream_site_gate"
    assert journal.data["halted"] is False


@pytest.mark.parametrize("reason", sorted(batch2.batch1.BATCH_STOP_REASONS))
def test_systemic_reason_stops_entire_batch(journal, monkeypatch, reason):
    monkeypatch.setattr(
        live,
        "check_pair",
        lambda *_: (_ for _ in ()).throw(live.Halt(reason)),
    )
    batch2.run_batch(journal, {site: "offline-fake-key" for site in live.SITES})
    assert journal.data["halted"] is True
    assert journal.data["halt_reason"] == reason
    assert all(
        row["reason"] == "batch_halted_after_systemic_error"
        for row in journal.data["results"]
        if row["status"] == "not_run"
    )


def test_attempt_counter_scope_and_no_overseas_for_china_only(journal):
    live.MODEL = "qwen-plus"
    journal.begin_attempt("china", False, 1)
    journal.begin_attempt("china", False, 2)
    with pytest.raises(live.Halt, match="request_scope_exceeded"):
        journal.begin_attempt("overseas", False, 1)
    with pytest.raises(live.Halt, match="unexpected_retry_or_turn"):
        journal.begin_attempt("china", False, 2)


@pytest.mark.parametrize("model", batch2.SCHEDULE)
def test_every_batch2_candidate_is_one_registered_runtime_model(model):
    old = live.MODEL
    try:
        live.MODEL = model
        adapter, *_ = live.runtime()
        assert adapter.model_schemas[0].model == model
    finally:
        live.MODEL = old


def test_previous_verified_models_are_disjoint_from_batch2():
    assert set(batch2.VERIFIED_NOT_RETESTED).isdisjoint(batch2.SCHEDULE)
