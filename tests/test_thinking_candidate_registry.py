"""Offline-only candidate protocol contracts; no candidate is publicly exposed."""

from copy import deepcopy
from pathlib import Path
import re

import pytest
import yaml

from models.llm.llm import MoyuLargeLanguageModel as Adapter


ROOT = Path(__file__).resolve().parents[1]
REGISTERED = yaml.safe_load((ROOT / "provider/moyu.yaml").read_text("utf-8"))[
    "models"
]["llm"]["predefined"]


def test_delivery_matrix_covers_exact_registered_ids_once():
    report = (ROOT / "docs/THINKING_CONTROL_CAPABILITIES.md").read_text("utf-8")
    rows = re.findall(
        r"^\| `([^`]+)` \| (双|仅国内) \| "
        r"(implemented-and-exposed|implemented-but-hidden|"
        r"blocked-needs-live-verification|no-reliable-thinking-control-evidence) \|",
        report, re.MULTILINE,
    )
    models = [model for model, _, _ in rows]
    registered = {
        yaml.safe_load((ROOT / name).read_text("utf-8"))["model"]
        for name in REGISTERED
    }
    assert len(rows) == len(set(models)) == len(registered) == 58
    assert set(models) == registered
    assert sum(site == "仅国内" for _, site, _ in rows) == 10
    counts = {status: sum(row[2] == status for row in rows) for status in {
        row[2] for row in rows
    }}
    assert counts == {
        "implemented-and-exposed": 16,
        "implemented-but-hidden": 2,
        "blocked-needs-live-verification": 14,
        "no-reliable-thinking-control-evidence": 26,
    }
    assert {model for model, _, status in rows if status == "implemented-and-exposed"} == (
        Adapter.EXPOSED_THINKING_MODELS
    )
    assert {model for model, _, status in rows if status in (
        "implemented-but-hidden", "blocked-needs-live-verification",
    )} == set(Adapter.CANDIDATE_THINKING_PROFILES) - Adapter.EXPOSED_THINKING_MODELS | {
        "gemini-3.1-flash-lite-preview"
    }

    assert "## 本轮后未开放的候选" in report


def test_exact_candidate_ids_and_public_allowlist():
    registered = {
        yaml.safe_load((ROOT / name).read_text("utf-8"))["model"]
        for name in REGISTERED
    }
    assert len(registered) == len(REGISTERED) == 58
    assert len(Adapter.CANDIDATE_THINKING_PROFILES) == 27
    assert set(Adapter.CANDIDATE_THINKING_PROFILES) <= registered
    assert set(Adapter.CANDIDATE_THINKING_PROFILES) & Adapter.EXPOSED_THINKING_MODELS == {
        "qwen3.6-35b-a3b", "qwen3.6-flash", "qwen3.7-max", "qwen3.7-plus",
        "qwen3.8-max", "glm-5.1", "glm-5.2", "kimi-k2.6", "qwen-plus",
        "qwen3-max", "gpt-5.5", "gpt-5.6-luna",
    }
    public = set()
    for name in REGISTERED:
        model = yaml.safe_load((ROOT / name).read_text("utf-8"))
        controls = {rule["name"] for rule in model.get("parameter_rules", [])} & {
            "thinking_mode", "enable_thinking", "thinking_budget", "reasoning_effort",
        }
        if controls:
            assert controls == ({"reasoning_effort"} if model["model"] in
                                Adapter.VERIFIED_EFFORT_THINKING_MODELS else
                                {"thinking_mode"})
            public.add(model["model"])
    assert public == Adapter.EXPOSED_THINKING_MODELS


@pytest.mark.parametrize("model", tuple(Adapter.CANDIDATE_THINKING_PROFILES))
def test_every_candidate_is_hidden_from_production_mapping(model):
    if model in Adapter.EXPOSED_THINKING_MODELS:
        return
    with pytest.raises(ValueError, match="unapproved_thinking_control"):
        Adapter._thinking_parameters(model, {"reasoning_effort": "low"})


@pytest.mark.parametrize("model,choice,expected", [
    ("qwen3.6-flash", "关闭", {"enable_thinking": False}),
    ("qwen3.8-max", "开启", {"enable_thinking": True}),
    ("glm-5.2", "开启", {"thinking": {"type": "enabled"}}),
    ("GLM-5", "关闭", {"thinking": {"type": "disabled"}}),
    ("kimi-k2.6", "开启", {"thinking": {"type": "enabled"}}),
])
def test_toggle_candidate_mapping_is_pure(model, choice, expected):
    original = {"thinking_mode": choice, "temperature": 0.6, "top_p": 0.8,
                "max_tokens": 128, "stop": ["END"]}
    before = deepcopy(original)
    mapped = Adapter._candidate_thinking_parameters(model, original)
    assert original == before
    assert mapped == {**expected, "temperature": 0.6, "top_p": 0.8,
                      "max_tokens": 128, "stop": ["END"]}


@pytest.mark.parametrize("model,effort", [
    ("gpt-5.5", "none"), ("gpt-5.6-sol", "max"),
    ("gpt-6-astra", "low"), ("gemini-2.5-flash", "low"),
    ("gemini-3-flash-preview", "minimal"), ("kimi-k3", "high"),
])
def test_effort_candidate_preserves_exact_option(model, effort):
    original = {"reasoning_effort": effort, "max_tokens": 128}
    assert Adapter._candidate_thinking_parameters(model, original) == original
    assert Adapter._candidate_thinking_parameters(model, original) is not original


@pytest.mark.parametrize("model,invalid", [
    ("gpt-6-astra", "none"), ("gemini-2.5-pro", "none"),
    ("kimi-k3", "medium"), ("gpt-5.5", "max"),
    ("glm-5.2", "auto"), ("qwen3.6-flash", True),
])
def test_exact_option_restrictions(model, invalid):
    key = "thinking_mode" if Adapter.CANDIDATE_THINKING_PROFILES[model][0].endswith(
        "toggle") else "reasoning_effort"
    with pytest.raises(ValueError):
        Adapter._candidate_thinking_parameters(model, {key: invalid})


def test_nested_budget_and_adaptive_candidate_mapping():
    assert Adapter._candidate_thinking_parameters(
        "claude-haiku-4-5-20251001", {"thinking_budget": 2048}
    ) == {"thinking": {"type": "enabled", "budget_tokens": 2048}}
    assert Adapter._candidate_thinking_parameters(
        "claude-sonnet-5", {"reasoning_effort": "medium"}
    ) == {"thinking": {"type": "adaptive"}, "output_config": {"effort": "medium"}}
    with pytest.raises(ValueError, match="invalid_thinking_budget"):
        Adapter._candidate_thinking_parameters(
            "claude-sonnet-4-6", {"thinking_budget": True}
        )


@pytest.mark.parametrize("model,params", [
    ("glm-5.2", {"thinking_mode": "开启", "thinking": {"type": "disabled"}}),
    ("qwen3.6-flash", {"thinking_mode": "开启", "enable_thinking": False}),
    ("claude-sonnet-4-6", {"thinking_budget": 2048, "thinking": {}}),
    ("claude-sonnet-5", {"reasoning_effort": "low", "output_config": {}}),
])
def test_candidate_conflicts_do_not_overwrite(model, params):
    before = deepcopy(params)
    with pytest.raises(ValueError, match="conflicting_thinking_controls"):
        Adapter._candidate_thinking_parameters(model, params)
    assert params == before


@pytest.mark.parametrize("model", tuple(Adapter.CANDIDATE_THINKING_PROFILES))
def test_unset_candidate_keeps_upstream_default(model):
    original = {"temperature": 0.5, "top_p": 0.8, "max_tokens": 128}
    assert Adapter._candidate_thinking_parameters(model, original) == original
