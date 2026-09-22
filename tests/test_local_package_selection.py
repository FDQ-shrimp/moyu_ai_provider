"""Offline safeguards for the explicit local-test package staging list."""
from copy import deepcopy

import pytest
import yaml

from scripts import local_package, preflight_check


def test_local_package_selects_registered_catalog_and_no_internal_files():
    files = local_package.selected_files()
    assert len(files) == 76
    assert len([p for p in files if p.startswith("models/llm/") and p.endswith(".yaml")]) == 58
    assert len([p for p in files if p.startswith("models/text_embedding/") and p.endswith(".yaml")]) == 4
    assert not any(p.startswith(("tests/", "scripts/", "docs/", "models/rerank/")) for p in files)
    assert not {".env", "AGENTS.md", "CODEX_HANDOFF.md", "ci_checks.html"} & files
    assert "models/llm/qwen3.6-plus.yaml" in files
    assert {"main.py", "requirements.txt", "models/llm/llm.py", "provider/moyu.yaml",
            "README.md", "readme/README_zh_Hans.md", "PRIVACY.md", "LICENSE"} <= files


def test_package_secret_scanner_never_prints_matched_value():
    fake = ("sk-" + "fake" * 12).encode()
    with pytest.raises(ValueError) as captured:
        local_package.check_secrets("example.txt", fake)
    assert fake.decode() not in str(captured.value)
    assert "example.txt" in str(captured.value)


def test_package_scanner_allows_documentation_about_credentials():
    local_package.check_secrets("example.md", b"api_key comes from the provider form; never ship .env")


def test_preflight_accepts_independent_manifest_format_version():
    report = preflight_check.Report()
    manifest = preflight_check.check_manifest(report)
    assert manifest["version"] == "0.0.8" and manifest["meta"]["version"] == "0.0.6"
    assert report.failed == []


def test_preflight_still_rejects_invalid_format_version(monkeypatch):
    data = yaml.safe_load((local_package.ROOT / "manifest.yaml").read_bytes())
    data = deepcopy(data)
    data["meta"]["version"] = "invalid"
    monkeypatch.setattr(preflight_check, "_load_yaml", lambda _: data)
    report = preflight_check.Report()
    preflight_check.check_manifest(report)
    assert any("runtime metadata version is not valid semver" in failure for failure in report.failed)
