"""Static structural checks for manifest / provider / model YAMLs.

These complement `scripts/preflight_check.py` but run as pytest so they
integrate into any CI flow.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent


def _load(rel: str):
    with (ROOT / rel).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_manifest_is_well_formed():
    manifest = _load("manifest.yaml")
    assert manifest["type"] == "plugin"
    assert manifest["name"]
    assert manifest["label"]["en_US"]
    assert manifest["plugins"]["models"] == ["provider/moyu.yaml"]
    icon = manifest["icon"]
    assert (ROOT / icon).is_file(), f"icon not found: {icon}"
    entry = manifest["meta"]["runner"]["entrypoint"]
    assert (ROOT / f"{entry}.py").is_file()


def test_provider_declares_api_key_secret_input():
    provider = _load("provider/moyu.yaml")
    forms = provider["provider_credential_schema"]["credential_form_schemas"]
    api_key_form = next((f for f in forms if f["variable"] == "api_key"), None)
    assert api_key_form is not None, "provider must declare an `api_key` field"
    assert api_key_form["type"] == "secret-input"
    assert api_key_form["required"] is True


def test_provider_source_files_exist():
    provider = _load("provider/moyu.yaml")
    py = provider["extra"]["python"]
    assert (ROOT / py["provider_source"]).is_file()
    for src in py["model_sources"]:
        assert (ROOT / src).is_file(), f"model source missing: {src}"


def test_predefined_glob_matches_files():
    provider = _load("provider/moyu.yaml")
    predefined = provider["models"]["llm"]["predefined"]
    assert predefined, "predefined model list cannot be empty"
    for pattern in predefined:
        matches = list(ROOT.glob(pattern))
        assert matches, f"predefined pattern {pattern!r} matched 0 files"


@pytest.mark.parametrize(
    "path", sorted((ROOT / "models" / "llm").glob("*.yaml"))
)
def test_each_model_yaml_has_required_fields(path: Path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path.name} must be a mapping"
    for key in ("model", "label", "model_type", "model_properties"):
        assert key in data, f"{path.name}: missing `{key}`"
    assert data["model_type"] == "llm"
    assert data["model_properties"].get("mode") == "chat"


def test_difyignore_excludes_env():
    text = (ROOT / ".difyignore").read_text(encoding="utf-8")
    lines = {ln.strip() for ln in text.splitlines()}
    assert ".env" in lines, ".difyignore must list `.env` to prevent debug key leakage"
