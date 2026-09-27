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
    assert manifest["version"] == "0.0.9" and manifest["meta"]["version"] == "0.0.6"
    assert report.failed == []


def test_preflight_still_rejects_invalid_format_version(monkeypatch):
    data = yaml.safe_load((local_package.ROOT / "manifest.yaml").read_bytes())
    data = deepcopy(data)
    data["meta"]["version"] = "invalid"
    monkeypatch.setattr(preflight_check, "_load_yaml", lambda _: data)
    report = preflight_check.Report()
    preflight_check.check_manifest(report)
    assert any("runtime metadata version is not valid semver" in failure for failure in report.failed)


def test_package_baseline_only_allows_approved_thinking_parameters():
    files = local_package.selected_files()
    changed = local_package.compare_baseline(files)
    assert "models/llm/qwen3.6-27b.yaml" in changed
    assert "models/llm/qwen3.6-plus.yaml" in changed
    thinking_models = set()
    for name in files:
        if name.startswith("models/llm/") and name.endswith(".yaml"):
            model = yaml.safe_load((local_package.ROOT / name).read_bytes())
            if local_package.check_thinking_parameter(model):
                thinking_models.add(model["model"])
    assert thinking_models == local_package.THINKING_MODELS


@pytest.mark.parametrize("model_id", ["qwen3.6-27b", "qwen3.6-plus"])
@pytest.mark.parametrize("invalid_rule", [
    {"default": False},
    {"default": True},
    {"required": False},
    {"type": "boolean"},
    {"default": "开启"},
    {"options": ["开启", "关闭", "默认"]},
    {"label": {"en_US": "Thinking mode", "zh_Hans": "思考"}},
])
def test_package_rejects_changed_thinking_rule(model_id, invalid_rule):
    rule = deepcopy(local_package.THINKING_PARAMETER_RULE)
    rule.update(invalid_rule)
    with pytest.raises(ValueError, match="Unexpected thinking parameter rule"):
        local_package.check_thinking_parameter({"model": model_id, "parameter_rules": [rule]})


@pytest.mark.parametrize("rules", [[], [local_package.THINKING_PARAMETER_RULE] * 2])
def test_package_rejects_missing_or_duplicate_thinking_rule(rules):
    with pytest.raises(ValueError, match="Unexpected thinking parameter rule"):
        local_package.check_thinking_parameter({"model": "qwen3.6-plus", "parameter_rules": rules})


@pytest.mark.parametrize("model_id", ["kimi-k3", "gemini-2.5-flash", "gpt-5.6-sol", "GLM-5"])
def test_package_rejects_thinking_parameter_on_unapproved_model(model_id):
    with pytest.raises(ValueError, match="Unexpected thinking parameter rule"):
        local_package.check_thinking_parameter({
            "model": model_id, "parameter_rules": [deepcopy(local_package.THINKING_PARAMETER_RULE)]
        })


def test_package_approved_thinking_rule_is_required_dropdown_default_off():
    rule = local_package.THINKING_PARAMETER_RULE
    assert rule["type"] == "string"
    assert rule["required"] is True
    assert rule["label"]["zh_Hans"] == "思考模式"
    assert rule["default"] == "关闭"
    assert rule["options"] == ["关闭", "开启"]
