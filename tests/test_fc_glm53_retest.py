"""Offline scope and history checks for the one-shot glm-5.3 retest."""
from __future__ import annotations

import hashlib
import io
import json

import pytest

from scripts import verify_fc_glm53_retest as retest
from scripts import verify_fc_live as live


def make_parent(tmp_path, monkeypatch):
    parent = tmp_path / "parent.json"
    data = {"request_attempts": 40, "results": [
        {"model": retest.MODEL, "site": retest.SITE, "mode": "stream",
         "status": "inconclusive", "reason": "transport_error_no_retry"}]}
    parent.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(retest, "PARENT", parent)
    monkeypatch.setattr(retest, "PARENT_SHA256", hashlib.sha256(parent.read_bytes()).hexdigest())
    monkeypatch.setattr(retest, "REPORT", tmp_path / "retest.json")
    return retest.Journal()


def test_retest_scope_is_one_model_site_mode_and_two_requests(tmp_path, monkeypatch):
    journal = make_parent(tmp_path, monkeypatch)
    live.MODEL = retest.MODEL
    first = journal.begin_attempt(retest.SITE, True, 1)
    second = journal.begin_attempt(retest.SITE, True, 2)
    assert [first["turn"], second["turn"]] == [1, 2]
    with pytest.raises(live.Halt, match="request_cap_or_retry_blocked"):
        journal.begin_attempt(retest.SITE, True, 2)
    assert journal.data["max_attempts"] == 2
    assert journal.data["automatic_retries"] is False and journal.data["redirects"] is False
    assert journal.data["model_listing"] is False and journal.data["credential_probing"] is False


def test_retest_rejects_other_site_or_mode(tmp_path, monkeypatch):
    journal = make_parent(tmp_path, monkeypatch)
    live.MODEL = retest.MODEL
    with pytest.raises(live.Halt, match="retest_scope_exceeded"):
        journal.begin_attempt("china", True, 1)
    with pytest.raises(live.Halt, match="retest_scope_exceeded"):
        journal.begin_attempt(retest.SITE, False, 1)
    assert journal.total_attempts == 0


def test_retest_accepts_only_overseas_key_without_saving_it(tmp_path, monkeypatch):
    journal = make_parent(tmp_path, monkeypatch)
    key = retest.read_key_line(io.StringIO('{"overseas":"offline-secret"}\n'))
    assert key == "offline-secret"
    assert "offline-secret" not in journal.path.read_text(encoding="utf-8")


def test_retest_parent_hash_must_remain_unchanged(tmp_path, monkeypatch):
    journal = make_parent(tmp_path, monkeypatch)
    retest.PARENT.write_text("changed", encoding="utf-8")
    live.MODEL = retest.MODEL
    with pytest.raises(live.Halt, match="parent_report_hash_mismatch"):
        journal.begin_attempt(retest.SITE, True, 1)
