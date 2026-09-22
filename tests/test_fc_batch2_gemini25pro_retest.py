"""Offline scope/history checks for the controlled Batch 2 Gemini retest."""
from __future__ import annotations

import hashlib
import io
import json

import pytest

from scripts import verify_fc_batch2_gemini25pro_retest as retest
from scripts import verify_fc_live as live


def make_parent(tmp_path, monkeypatch):
    parent = tmp_path / "parent.json"
    data = {
        "request_attempts": 17,
        "halted": True,
        "halt_reason": "transport_error_no_retry",
        "attempts": [
            {
                "number": 17,
                "model": retest.MODEL,
                "site": retest.SITE,
                "mode": retest.MODE,
                "turn": 1,
                "exception_type": "ReadTimeout",
                "headers_received": False,
            }
        ],
        "results": [
            {
                "model": retest.MODEL,
                "site": retest.SITE,
                "mode": retest.MODE,
                "status": "inconclusive",
                "reason": "transport_error_no_retry",
            }
        ],
    }
    parent.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(retest, "PARENT", parent)
    monkeypatch.setattr(
        retest,
        "PARENT_SHA256",
        hashlib.sha256(parent.read_bytes()).hexdigest(),
    )
    return retest.Journal(tmp_path / "retest.json")


def test_retest_scope_is_exactly_one_model_site_mode_and_two_requests(tmp_path, monkeypatch):
    journal = make_parent(tmp_path, monkeypatch)
    live.MODEL = retest.MODEL
    first = journal.begin_attempt(retest.SITE, False, 1)
    second = journal.begin_attempt(retest.SITE, False, 2)
    assert [first["turn"], second["turn"]] == [1, 2]
    with pytest.raises(live.Halt, match="request_cap_or_retry_blocked"):
        journal.begin_attempt(retest.SITE, False, 2)
    assert journal.data["max_attempts"] == 2
    assert journal.data["automatic_retries"] is False
    assert journal.data["redirects"] is False
    assert journal.data["model_listing"] is False
    assert journal.data["credential_probing"] is False


def test_retest_rejects_other_site_model_or_stream(tmp_path, monkeypatch):
    journal = make_parent(tmp_path, monkeypatch)
    live.MODEL = retest.MODEL
    with pytest.raises(live.Halt, match="retest_scope_exceeded"):
        journal.begin_attempt("overseas", False, 1)
    with pytest.raises(live.Halt, match="retest_scope_exceeded"):
        journal.begin_attempt(retest.SITE, True, 1)
    live.MODEL = "gemini-2.5-flash"
    with pytest.raises(live.Halt, match="retest_scope_exceeded"):
        journal.begin_attempt(retest.SITE, False, 1)
    assert journal.total_attempts == 0


def test_retest_accepts_only_china_key_without_saving_it(tmp_path, monkeypatch):
    journal = make_parent(tmp_path, monkeypatch)
    key = retest.read_key_line(io.StringIO('{"china":"offline-secret"}\n'))
    assert key == "offline-secret"
    assert "offline-secret" not in journal.path.read_text(encoding="utf-8")
    with pytest.raises(live.Halt, match="invalid_credential_input"):
        retest.read_key_line(io.StringIO('{"overseas":"wrong-site"}\n'))


def test_parent_hash_and_original_attempt_must_remain_unchanged(tmp_path, monkeypatch):
    journal = make_parent(tmp_path, monkeypatch)
    retest.PARENT.write_text("changed", encoding="utf-8")
    live.MODEL = retest.MODEL
    with pytest.raises(live.Halt, match="parent_report_hash_mismatch"):
        journal.begin_attempt(retest.SITE, False, 1)
