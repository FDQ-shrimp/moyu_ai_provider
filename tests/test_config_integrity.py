"""Static structural checks for manifest / provider / model YAMLs.

These complement `scripts/preflight_check.py` but run as pytest so they
integrate into any CI flow.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent

SHARED_LLM_MODELS = {
    "MiniMax-M3",
    "claude-fable-5",
    "claude-haiku-4-5-20251001",
    "claude-opus-4-1-20250805",
    "claude-opus-4-20250514",
    "claude-opus-4-5-20251101",
    "claude-opus-4-6",
    "claude-opus-4-7",
    "claude-opus-4-8",
    "claude-opus-5",
    "claude-sonnet-4-20250514",
    "claude-sonnet-4-5-20250929",
    "claude-sonnet-4-6",
    "claude-sonnet-5",
    "deepseek-v4-flash",
    "deepseek-v4-flash-0731",
    "deepseek-v4-pro",
    "doubao-seed-2-1-pro-260628",
    "gemini-2.5-flash",
    "gemini-2.5-flash-image-preview",
    "gemini-2.5-flash-lite",
    "gemini-2.5-pro",
    "gemini-3-flash-preview",
    "gemini-3-pro-image-preview",
    "gemini-3.1-flash-image-preview",
    "gemini-3.1-flash-lite-preview",
    "gemini-3.1-pro-preview",
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "glm-5.1",
    "glm-5.2",
    "glm-5.3",
    "gpt-5.5",
    "gpt-5.6-luna",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-6-astra",
    "gpt-image-2(按次)",
    "kimi-k2.6",
    "kimi-k2.7-code",
    "kimi-k3",
    "qwen3.6-27b",
    "qwen3.6-35b-a3b",
    "qwen3.6-flash",
    "qwen3.6-plus",
    "qwen3.7-max",
    "qwen3.7-plus",
    "qwen3.8-max",
}

CHINA_ONLY_LLM_MODELS = {
    "DeepSeek-R1-0528",
    "DeepSeek-V3-0324",
    "GLM-5",
    "doubao-seed-2-0-code-preview-260215",
    "doubao-seed-2-0-lite-260215",
    "doubao-seed-2-0-mini-260215",
    "doubao-seed-2-0-pro-260215",
    "qwen-plus",
    "qwen3-max",
    "qwen3-vl-plus",
}

SHARED_EMBEDDING_MODELS = {
    "gemini-embedding-001",
    "gemini-embedding-2-preview",
}

CHINA_ONLY_EMBEDDING_MODELS = {
    "text-embedding-v2",
    "text-embedding-v4",
}

KNOWN_UNAVAILABLE_LLM_MODELS = {
    "DeepSeek-V3.1",
    "gemini-3-pro-preview",
    "gpt-image-2",
    "qwen-image-3.0",
    "veo-3",
    "veo-3-fast",
    "veo-3.1",
    "veo-3.1-fast",
    "wan2.6-image",
    "wan2.7-image",
}


def _load(rel: str):
    with (ROOT / rel).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_manifest_is_well_formed():
    manifest = _load("manifest.yaml")
    assert manifest["type"] == "plugin"
    assert manifest["name"] == "moyu_ai_provider"
    assert manifest["author"] == "fdq-shrimp"
    assert manifest["version"] == "0.0.6"
    assert manifest["meta"]["version"] == manifest["version"]
    assert manifest["privacy"] == "PRIVACY.md"
    assert manifest["repo"] == "https://github.com/FDQ-shrimp/moyu_ai_provider"
    assert manifest["contact"] == "fangdaq10@163.com"
    assert manifest["label"]["en_US"]
    assert manifest["plugins"]["models"] == ["provider/moyu.yaml"]
    icon = manifest["icon"]
    assert (ROOT / icon).is_file(), f"icon not found: {icon}"
    entry = manifest["meta"]["runner"]["entrypoint"]
    assert (ROOT / f"{entry}.py").is_file()
    permissions = manifest["resource"]["permission"]["model"]
    assert permissions["enabled"] is True
    assert permissions["llm"] is True
    assert permissions["text_embedding"] is True
    assert permissions["rerank"] is False


def test_release_documents_match_current_sites_and_license():
    privacy = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    assert "https://www.moyu.cn/v1" in privacy
    assert "https://www.konjac.ai/v1" in privacy
    assert "fangdaq10@163.com" in privacy
    assert license_text.startswith("MIT License")
    assert "Copyright (c) 2026 fdq-shrimp" in license_text


def test_marketplace_sdk_minimum_version_requirement():
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "dify_plugin>=0.9.0" in requirements.splitlines()


def test_manifest_and_provider_model_types_match():
    manifest = _load("manifest.yaml")
    provider = _load("provider/moyu.yaml")
    permissions = manifest["resource"]["permission"]["model"]
    enabled_types = {
        key.replace("_", "-")
        for key, enabled in permissions.items()
        if key != "enabled" and enabled
    }

    assert enabled_types == set(provider["supported_model_types"])


def test_provider_declares_api_key_secret_input():
    provider = _load("provider/moyu.yaml")
    forms = provider["provider_credential_schema"]["credential_form_schemas"]
    api_key_form = next((f for f in forms if f["variable"] == "api_key"), None)
    assert api_key_form is not None, "provider must declare an `api_key` field"
    assert api_key_form["type"] == "secret-input"
    assert api_key_form["required"] is True


def test_provider_declares_fixed_api_key_site_selector():
    provider = _load("provider/moyu.yaml")
    forms = provider["provider_credential_schema"]["credential_form_schemas"]
    endpoint_form = next(
        (f for f in forms if f["variable"] == "endpoint_url"), None
    )

    assert endpoint_form is not None
    assert endpoint_form["type"] == "select"
    assert endpoint_form["required"] is False
    assert endpoint_form["default"] == "https://www.moyu.cn/v1"
    assert endpoint_form["label"]["zh_Hans"] == "API Key 所属站点"
    assert [option["value"] for option in endpoint_form["options"]] == [
        "https://www.moyu.cn/v1",
        "https://www.konjac.ai/v1",
    ]
    assert [option["label"]["zh_Hans"] for option in endpoint_form["options"]] == [
        "国内站",
        "海外站",
    ]


def test_provider_source_files_exist():
    provider = _load("provider/moyu.yaml")
    py = provider["extra"]["python"]
    assert (ROOT / py["provider_source"]).is_file()
    for src in py["model_sources"]:
        assert (ROOT / src).is_file(), f"model source missing: {src}"


def test_predefined_catalog_references_existing_files():
    provider = _load("provider/moyu.yaml")
    for model_type in ("llm", "text_embedding"):
        predefined = provider["models"][model_type]["predefined"]
        assert predefined, f"{model_type} predefined model list cannot be empty"
        for pattern in predefined:
            assert "*" not in pattern, "release catalog must use an explicit allowlist"
            matches = list(ROOT.glob(pattern))
            assert matches, f"predefined pattern {pattern!r} matched 0 files"

    assert "rerank" not in provider["models"]
    assert "models/rerank/rerank.py" not in provider["extra"]["python"]["model_sources"]


def _configured_models(provider: dict, model_type: str) -> dict[str, dict]:
    configured: dict[str, dict] = {}
    for rel in provider["models"][model_type]["predefined"]:
        data = _load(rel)
        assert data["model"] not in configured, f"duplicate configured model: {data['model']}"
        configured[data["model"]] = data
    return configured


def test_provider_exposes_verified_shared_and_china_only_catalog():
    provider = _load("provider/moyu.yaml")
    llms = _configured_models(provider, "llm")
    embeddings = _configured_models(provider, "text_embedding")

    assert set(llms) == SHARED_LLM_MODELS | CHINA_ONLY_LLM_MODELS
    assert len(llms) == 58
    assert set(embeddings) == SHARED_EMBEDDING_MODELS | CHINA_ONLY_EMBEDDING_MODELS
    assert len(embeddings) == 4


def test_china_only_models_are_clearly_labeled():
    provider = _load("provider/moyu.yaml")
    llms = _configured_models(provider, "llm")
    embeddings = _configured_models(provider, "text_embedding")

    for model_id in CHINA_ONLY_LLM_MODELS:
        assert llms[model_id]["label"]["zh_Hans"].endswith("（仅国内站）")
        assert llms[model_id]["label"]["en_US"].endswith(" (China only)")

    for model_id in CHINA_ONLY_EMBEDDING_MODELS:
        assert embeddings[model_id]["label"]["zh_Hans"].endswith("（仅国内站）")
        assert embeddings[model_id]["label"]["en_US"].endswith(" (China only)")


def test_known_unavailable_models_are_not_registered():
    provider = _load("provider/moyu.yaml")
    llms = _configured_models(provider, "llm")

    assert KNOWN_UNAVAILABLE_LLM_MODELS.isdisjoint(llms)


def test_gpt_6_astra_does_not_expose_unsupported_sampling_parameters():
    provider = _load("provider/moyu.yaml")
    llms = _configured_models(provider, "llm")
    parameter_names = {rule["name"] for rule in llms["gpt-6-astra"]["parameter_rules"]}

    assert parameter_names == {"max_tokens"}


@pytest.mark.parametrize(
    ("path", "expected_type"),
    [
        *[(path, "llm") for path in sorted((ROOT / "models" / "llm").glob("*.yaml"))],
        *[
            (path, "text-embedding")
            for path in sorted((ROOT / "models" / "text_embedding").glob("*.yaml"))
        ],
        *[
            (path, "rerank")
            for path in sorted((ROOT / "models" / "rerank").glob("*.yaml"))
        ],
    ],
)
def test_each_model_yaml_has_required_fields(path: Path, expected_type: str):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path.name} must be a mapping"
    for key in ("model", "label", "model_type", "model_properties"):
        assert key in data, f"{path.name}: missing `{key}`"
    assert data["model_type"] == expected_type
    if expected_type == "llm":
        assert data["model_properties"].get("mode") == "chat"


def test_difyignore_excludes_env():
    text = (ROOT / ".difyignore").read_text(encoding="utf-8")
    lines = {ln.strip() for ln in text.splitlines()}
    assert ".env" in lines, ".difyignore must list `.env` to prevent debug key leakage"
