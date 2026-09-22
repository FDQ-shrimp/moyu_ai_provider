"""Static structural checks for manifest / provider / model YAMLs.

These complement `scripts/preflight_check.py` but run as pytest so they
integrate into any CI flow.
"""

from __future__ import annotations

from pathlib import Path
import hashlib
import json
import zipfile

import pytest
import yaml

from scripts import sync_models

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

TOOL_CALL_MODELS = {
    "MiniMax-M3", "claude-fable-5", "claude-haiku-4-5-20251001",
    "claude-opus-4-1-20250805", "claude-opus-4-20250514",
    "claude-opus-4-5-20251101", "claude-opus-4-6", "claude-opus-4-7",
    "claude-opus-4-8", "claude-sonnet-4-20250514",
    "claude-sonnet-4-5-20250929", "claude-sonnet-4-6", "claude-sonnet-5",
    "deepseek-v4-flash", "deepseek-v4-flash-0731", "deepseek-v4-pro",
    "doubao-seed-2-1-pro-260628", "gemini-2.5-flash",
    "gemini-2.5-flash-lite", "gemini-3-flash-preview",
    "gemini-3-pro-image-preview", "gemini-3.1-flash-lite-preview",
    "gemini-3.1-pro-preview", "gemini-3.5-flash", "gemini-3.6-flash",
    "glm-5.1", "glm-5.2", "glm-5.3", "gpt-5.5", "gpt-5.6-luna",
    "gpt-5.6-sol", "gpt-5.6-terra", "kimi-k2.6", "kimi-k2.7-code",
    "kimi-k3", "qwen3.6-27b", "qwen3.6-35b-a3b", "qwen3.6-flash",
    "qwen3.6-plus", "qwen3.7-max", "qwen3.7-plus",
}

TOOL_CALL_ONLY_MODELS = {
    "MiniMax-M3", "claude-sonnet-4-5-20250929",
    "gemini-3-pro-image-preview", "kimi-k2.7-code",
}

STREAM_TOOL_CALL_MODELS = TOOL_CALL_MODELS - TOOL_CALL_ONLY_MODELS

SHARED_NO_TOOL_MODELS = {
    "claude-opus-5", "gemini-2.5-flash-image-preview", "gemini-2.5-pro",
    "gemini-3.1-flash-image-preview", "gpt-6-astra", "gpt-image-2(按次)",
    "qwen3.8-max",
}

APPROVED_TOOL_FEATURES = {
    model_id: {"tool-call"} | (
        {"stream-tool-call"} if model_id in STREAM_TOOL_CALL_MODELS else set()
    )
    for model_id in TOOL_CALL_MODELS
}


def _load(rel: str):
    with (ROOT / rel).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_manifest_is_well_formed():
    manifest = _load("manifest.yaml")
    assert manifest["type"] == "plugin"
    assert manifest["name"] == "moyu_ai_provider"
    assert manifest["author"] == "fdq-shrimp"
    assert manifest["version"] == "0.0.8"
    # Runtime metadata schema version is not the plugin release version.
    assert manifest["meta"]["version"] == "0.0.6"
    assert manifest["meta"]["runner"]["version"] == "3.12"
    assert manifest["privacy"] == "PRIVACY.md"
    assert manifest["repo"] == "https://github.com/FDQ-shrimp/moyu_ai_provider"
    assert manifest["contact"] == "fangdaq10@163.com"
    assert manifest["network"]["domains"] == ["www.moyu.cn", "www.konjac.ai"]
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


def test_registered_tool_capabilities_match_explicit_approved_allowlist():
    provider = _load("provider/moyu.yaml")
    tool_features = {"tool-call", "multi-tool-call", "stream-tool-call"}
    configured = _configured_models(provider, "llm")

    assert len(TOOL_CALL_MODELS) == 41
    assert len(STREAM_TOOL_CALL_MODELS) == 37
    assert STREAM_TOOL_CALL_MODELS < TOOL_CALL_MODELS
    assert TOOL_CALL_ONLY_MODELS == TOOL_CALL_MODELS - STREAM_TOOL_CALL_MODELS
    assert SHARED_LLM_MODELS == TOOL_CALL_MODELS | SHARED_NO_TOOL_MODELS
    assert len(SHARED_NO_TOOL_MODELS) == 7
    assert set(APPROVED_TOOL_FEATURES) < set(configured)
    for model in configured.values():
        actual = set(model.get("features", [])) & tool_features
        assert actual == APPROVED_TOOL_FEATURES.get(model["model"], set()), model["model"]
        assert "multi-tool-call" not in model.get("features", []), model["model"]


def test_approved_models_only_add_exact_flags_to_0_0_6_baseline():
    provider = _load("provider/moyu.yaml")
    paths = {
        _load(path)["model"]: path for path in provider["models"]["llm"]["predefined"]
    }
    baseline = ROOT.parent / "moyu_ai_provider-0.0.6.difypkg"

    assert baseline.is_file()
    with zipfile.ZipFile(baseline) as archive:
        for model_id in sorted(TOOL_CALL_MODELS):
            path = paths[model_id]
            expected = yaml.safe_load(archive.read(path))
            expected["features"].append("tool-call")
            if model_id in STREAM_TOOL_CALL_MODELS:
                expected["features"].append("stream-tool-call")
            actual = _load(path)
            assert actual == expected, model_id
            assert len(actual["features"]) == len(set(actual["features"])), model_id


def test_all_122_llm_yamls_reject_multi_tool_call():
    paths = sorted((ROOT / "models" / "llm").glob("*.yaml"))

    assert len(paths) == 122
    for path in paths:
        model = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "multi-tool-call" not in model.get("features", []), path.name


def test_sync_generator_preserves_exact_verified_public_capabilities():
    assert sync_models.TOOL_CALL_MODELS == TOOL_CALL_MODELS
    assert sync_models.STREAM_TOOL_CALL_MODELS == STREAM_TOOL_CALL_MODELS

    for model_id in SHARED_LLM_MODELS | CHINA_ONLY_LLM_MODELS:
        features = set(sync_models.infer_features(model_id))
        actual = features & {"tool-call", "stream-tool-call", "multi-tool-call"}
        assert actual == APPROVED_TOOL_FEATURES.get(model_id, set()), model_id


def test_approved_tool_capabilities_have_exact_site_model_evidence():
    ledger = _load("docs/VERIFIED_TOOL_CAPABILITIES.yaml")
    assert ledger["record_schema"] == 3
    assert ledger["scope"] == "single_tool_only"
    assert ledger["catalog"] == {
        "registered_llm": 58,
        "shared": 48,
        "china_only": 10,
        "public_tool_call": 41,
        "public_stream_tool_call": 37,
        "public_multi_tool_call": 0,
        "china_only_verified": 10,
    }
    assert ledger["decision_policy"]["strict_final_text_is_capability_gate"] is False
    assert set(ledger["allowlists"]["shared_tool_call"]) == TOOL_CALL_MODELS
    assert set(ledger["allowlists"]["shared_stream_tool_call"]) == STREAM_TOOL_CALL_MODELS
    assert set(ledger["allowlists"]["tool_call_only"]) == TOOL_CALL_ONLY_MODELS
    assert set(ledger["allowlists"]["shared_no_tool"]) == SHARED_NO_TOOL_MODELS
    assert set(ledger["allowlists"]["china_only_verified_not_public"]) == CHINA_ONLY_LLM_MODELS

    reports = {}
    for name, evidence in ledger["reports"].items():
        data = (ROOT / evidence["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == evidence["sha256"]
        reports[name] = json.loads(data)

    models = {model["model_id"]: model for model in ledger["models"]}
    assert set(models) == TOOL_CALL_MODELS | CHINA_ONLY_LLM_MODELS
    provider = _load("provider/moyu.yaml")
    registered_paths = {
        _load(path)["model"]: path for path in provider["models"]["llm"]["predefined"]
    }
    assert set(models) <= set(registered_paths)

    def report_results(report):
        return report.get("results", [report.get("result")])

    def protocol_complete(result, report, model_id, site, mode):
        if result["status"] == "pass":
            return True
        if result.get("reason") != "final_answer_not_confirmed":
            return False
        first = next(
            (item for item in result.get("evidence", []) if item.get("turn") == 1),
            None,
        )
        second = next(
            (item for item in result.get("diagnostics", []) if item.get("turn") == 2),
            None,
        )
        second_attempt = next(
            (
                item
                for item in report["attempts"]
                if item.get("model", report.get("model")) == model_id
                and item["site"] == site
                and item["mode"] == mode
                and item["turn"] == 2
            ),
            None,
        )
        return bool(
            first
            and first.get("structured_upstream_and_sdk_match") is True
            and first.get("local_add_executed") is True
            and first.get("local_result") == 5
            and second_attempt
            and second_attempt.get("request_protocol_validated") is True
            and second_attempt.get("http_status") == 200
            and second
            and second.get("sdk_parse_completed") is True
            and second.get("sdk_output_matches_expected") is True
            and second.get("finish_reason") == "stop"
        )

    for model_id, model in models.items():
        assert model["yaml_path"] == registered_paths[model_id]
        shared = model_id in TOOL_CALL_MODELS
        assert model["availability"] == ("shared" if shared else "china-only")
        assert set(model["public_features"]) == APPROVED_TOOL_FEATURES.get(model_id, set())
        expected_verified = (
            APPROVED_TOOL_FEATURES[model_id]
            if shared
            else {"tool-call", "stream-tool-call"}
        )
        assert set(model["verified_features"]) == expected_verified
        assert model["multi_tool"] == "untested"
        expected_sites = {"china", "overseas"} if shared else {"china"}
        assert set(model["evidence"]) == expected_sites
        for site_name, site_evidence in model["evidence"].items():
            modes = {"nonstream"}
            if "stream-tool-call" in expected_verified:
                modes.add("stream")
            assert set(site_evidence) == modes
            for mode, evidence in site_evidence.items():
                report = reports[evidence["report"]]
                result = next(
                    result
                    for result in report_results(report)
                    if result
                    and result["model"] == model_id
                    and result["site"] == site_name
                    and result["mode"] == mode
                )
                assert evidence["status"] == "protocol_pass"
                assert protocol_complete(result, report, model_id, site_name, mode)
                expected_strict = (
                    "not_exact"
                    if result.get("reason") == "final_answer_not_confirmed"
                    else "exact"
                )
                assert evidence["strict_final_text"] == expected_strict
                actual_requests = [
                    attempt["number"]
                    for attempt in report["attempts"]
                    if attempt["site"] == site_name
                    and attempt.get("model", report.get("model")) == model_id
                    and attempt["mode"] == mode
                ]
                assert actual_requests == evidence["requests"]

    deferred = {item["model_id"]: item for item in ledger["deferred_shared_models"]}
    assert set(deferred) == SHARED_NO_TOOL_MODELS
    assert all(item["public_features"] == [] for item in deferred.values())

    history = {event["event"]: event for event in ledger["history_events"]}
    qwen_history = history["qwen_china_stream_initial_inconclusive"]
    assert qwen_history["report"] == "qwen_original"
    assert qwen_history["requests"] == [5, 6]
    assert qwen_history["status"] == "inconclusive"
    qwen_initial = next(
        result
        for result in reports["qwen_original"]["results"]
        if result["site"] == "china" and result["mode"] == "stream"
    )
    assert qwen_initial["status"] == "inconclusive"

    glm_history = history["glm53_overseas_stream_initial_inconclusive"]
    assert glm_history["report"] == "batch1"
    assert glm_history["requests"] == [39, 40]
    assert glm_history["status"] == "inconclusive"
    glm_initial = next(
        result
        for result in reports["batch1"]["results"]
        if result["model"] == "glm-5.3"
        and result["site"] == "overseas"
        and result["mode"] == "stream"
    )
    assert glm_initial["status"] == "inconclusive"
    glm_attempt_40 = next(
        attempt for attempt in reports["batch1"]["attempts"] if attempt["number"] == 40
    )
    assert glm_attempt_40["outcome"] == "transport_error_no_retry"
    assert glm_attempt_40["error_category"] == "timeout"

    glm_overseas = models["glm-5.3"]["evidence"]["overseas"]
    assert glm_overseas["stream"]["report"] == "glm53_stream_retest"
    assert glm_overseas["stream"]["requests"] == [1, 2]

    gpt_observation = models["gpt-5.5"]["observations"][0]
    assert gpt_observation == {
        "kind": "latency_stability",
        "report": "batch1_stream_remaining",
        "request": 6,
        "elapsed_to_headers_ms": 57547,
        "note": "China streaming turn 2 passed but is retained as a latency stability observation.",
    }
    gpt_attempt_6 = next(
        attempt
        for attempt in reports["batch1_stream_remaining"]["attempts"]
        if attempt["number"] == 6
    )
    assert gpt_attempt_6["model"] == "gpt-5.5"
    assert gpt_attempt_6["site"] == "china"
    assert gpt_attempt_6["mode"] == "stream"
    assert gpt_attempt_6["turn"] == 2
    assert gpt_attempt_6["http_status"] == 200
    assert gpt_attempt_6["headers_received"] is True
    assert gpt_attempt_6["elapsed_to_headers_ms"] == gpt_observation["elapsed_to_headers_ms"]


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
