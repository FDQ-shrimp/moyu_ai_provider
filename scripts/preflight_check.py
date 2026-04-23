"""
Pre-release preflight check for the Moyu AI Dify model-provider plugin.

What this script verifies (purely local, no network):
    1. Critical files exist:
         manifest.yaml, provider/moyu.yaml, provider/moyu.py,
         models/llm/llm.py, icon.png, at least one model YAML.
    2. All top-level YAML files parse successfully.
    3. manifest.yaml references are coherent:
         - `plugins.models` points at provider/moyu.yaml
         - `icon` file exists on disk
         - `meta.runner.entrypoint` resolves to main.py
    4. provider/moyu.yaml is coherent:
         - `extra.python.provider_source` file exists
         - every `extra.python.model_sources` file exists
         - every `models.llm.predefined` glob matches >=1 file
         - `icon_small` / `icon_large` reference existing assets
         - `provider_credential_schema` exposes a field named `api_key`
           as type `secret-input`
    5. Every model YAML in models/llm/*.yaml has the minimum keys
       (`model`, `label`, `model_type: llm`, `model_properties.mode`).
    6. `.difyignore` excludes `.env` (prevents debug key leakage).
    7. Source code does not hardcode a REMOTE_INSTALL_KEY or api_key
       literal that could leak via the package.

Exit status
-----------
    0  -> all checks passed (release-ready)
    1  -> at least one blocking issue was found

Usage
-----
    python scripts/preflight_check.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:
    print("[FATAL] PyYAML is required: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


ROOT = Path(__file__).resolve().parent.parent

# ANSI helpers (cross-platform safe: Windows 10+ consoles honour them).
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"


class Report:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.warnings: list[str] = []

    def ok(self, msg: str) -> None:
        self.passed.append(msg)
        print(f"  {GREEN}[OK]{RESET}  {msg}")

    def fail(self, msg: str) -> None:
        self.failed.append(msg)
        print(f"  {RED}[FAIL]{RESET} {msg}")

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)
        print(f"  {YELLOW}[WARN]{RESET} {msg}")


def _section(title: str) -> None:
    print(f"\n== {title} ==")


# ----------------------------------------------------------------------
# Individual checks
# ----------------------------------------------------------------------

REQUIRED_FILES = [
    "manifest.yaml",
    "provider/moyu.yaml",
    "provider/moyu.py",
    "models/llm/llm.py",
    "main.py",
    "requirements.txt",
    "icon.png",
    ".difyignore",
]


def check_required_files(report: Report) -> None:
    _section("1. Critical files")
    for rel in REQUIRED_FILES:
        p = ROOT / rel
        if p.is_file():
            report.ok(f"exists: {rel}")
        else:
            report.fail(f"missing: {rel}")

    llm_yaml_files = list((ROOT / "models" / "llm").glob("*.yaml"))
    if llm_yaml_files:
        report.ok(f"model YAML files found: {len(llm_yaml_files)}")
    else:
        report.fail("no model YAML files under models/llm/*.yaml")


def _load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def check_manifest(report: Report) -> dict | None:
    _section("2. manifest.yaml")
    manifest_path = ROOT / "manifest.yaml"
    if not manifest_path.is_file():
        report.fail("manifest.yaml missing — cannot continue manifest checks")
        return None

    try:
        manifest = _load_yaml(manifest_path)
    except yaml.YAMLError as e:
        report.fail(f"manifest.yaml is not valid YAML: {e}")
        return None

    if not isinstance(manifest, dict):
        report.fail("manifest.yaml root must be a mapping")
        return None

    for key in ("type", "name", "label", "description", "icon",
                "version", "plugins", "meta", "author"):
        if key in manifest:
            report.ok(f"manifest has `{key}`")
        else:
            report.fail(f"manifest missing `{key}`")

    if manifest.get("type") != "plugin":
        report.fail(f"manifest.type must be 'plugin', got {manifest.get('type')!r}")

    models = (manifest.get("plugins") or {}).get("models") or []
    if "provider/moyu.yaml" in models:
        report.ok("plugins.models references provider/moyu.yaml")
    else:
        report.fail(f"plugins.models must include 'provider/moyu.yaml', got {models}")

    icon_rel = manifest.get("icon")
    if icon_rel and (ROOT / icon_rel).is_file():
        report.ok(f"icon file exists: {icon_rel}")
    elif icon_rel:
        report.fail(f"icon file not found on disk: {icon_rel}")

    meta = manifest.get("meta") or {}
    runner = meta.get("runner") or {}
    entrypoint = runner.get("entrypoint")
    if entrypoint and (ROOT / f"{entrypoint}.py").is_file():
        report.ok(f"meta.runner.entrypoint resolves to {entrypoint}.py")
    else:
        report.fail(f"meta.runner.entrypoint `{entrypoint}` has no matching .py file")

    perm = (manifest.get("resource") or {}).get("permission") or {}
    model_perm = perm.get("model") or {}
    if model_perm.get("enabled") and model_perm.get("llm"):
        report.ok("resource.permission.model.{enabled,llm} both true")
    else:
        report.fail("resource.permission.model.enabled or .llm is not true")

    return manifest


def check_provider(report: Report) -> dict | None:
    _section("3. provider/moyu.yaml")
    provider_path = ROOT / "provider" / "moyu.yaml"
    if not provider_path.is_file():
        report.fail("provider/moyu.yaml missing")
        return None

    try:
        provider = _load_yaml(provider_path)
    except yaml.YAMLError as e:
        report.fail(f"provider/moyu.yaml is not valid YAML: {e}")
        return None

    for key in ("provider", "label", "description", "icon_small",
                "icon_large", "supported_model_types",
                "configurate_methods", "provider_credential_schema",
                "models", "extra"):
        if key in provider:
            report.ok(f"provider has `{key}`")
        else:
            report.fail(f"provider missing `{key}`")

    if "llm" in (provider.get("supported_model_types") or []):
        report.ok("supported_model_types contains 'llm'")
    else:
        report.fail("supported_model_types must contain 'llm'")

    if "predefined-model" in (provider.get("configurate_methods") or []):
        report.ok("configurate_methods contains 'predefined-model'")
    else:
        report.fail("configurate_methods must contain 'predefined-model'")

    # provider_credential_schema must expose exactly api_key as secret-input.
    cred_schema = (provider.get("provider_credential_schema") or {})
    forms = cred_schema.get("credential_form_schemas") or []
    api_key_form = next(
        (f for f in forms if (f or {}).get("variable") == "api_key"), None
    )
    if not api_key_form:
        report.fail("provider_credential_schema must declare a field named `api_key`")
    else:
        report.ok("provider_credential_schema declares `api_key`")
        if api_key_form.get("type") != "secret-input":
            report.fail(f"`api_key` field type must be 'secret-input', got {api_key_form.get('type')!r}")
        else:
            report.ok("`api_key` field uses type `secret-input`")
        if not api_key_form.get("required"):
            report.warn("`api_key` field is not marked required")
        else:
            report.ok("`api_key` field is required")

    # Any field other than api_key should be flagged — a public plugin should
    # not ask the user for debug variables.
    extra_vars = [f.get("variable") for f in forms if (f or {}).get("variable") != "api_key"]
    if extra_vars:
        report.warn(f"provider credential schema exposes additional fields: {extra_vars}")

    # Icon asset paths.
    for side in ("icon_small", "icon_large"):
        entry = provider.get(side) or {}
        if isinstance(entry, dict):
            for locale, rel in entry.items():
                if (ROOT / rel).is_file():
                    report.ok(f"{side}[{locale}] exists: {rel}")
                else:
                    report.fail(f"{side}[{locale}] file not found: {rel}")

    # Python source references.
    extra = provider.get("extra") or {}
    python_cfg = extra.get("python") or {}
    prov_src = python_cfg.get("provider_source")
    if prov_src and (ROOT / prov_src).is_file():
        report.ok(f"extra.python.provider_source exists: {prov_src}")
    else:
        report.fail(f"extra.python.provider_source missing or invalid: {prov_src}")

    model_srcs = python_cfg.get("model_sources") or []
    for src in model_srcs:
        if (ROOT / src).is_file():
            report.ok(f"extra.python.model_sources exists: {src}")
        else:
            report.fail(f"extra.python.model_sources missing: {src}")

    # Predefined model glob references.
    predefined = ((provider.get("models") or {}).get("llm") or {}).get("predefined") or []
    for pattern in predefined:
        matches = list(ROOT.glob(pattern))
        if matches:
            report.ok(f"predefined glob `{pattern}` matched {len(matches)} file(s)")
        else:
            report.fail(f"predefined glob `{pattern}` matched 0 files")

    return provider


def check_model_yamls(report: Report) -> None:
    _section("4. models/llm/*.yaml")
    model_files = sorted((ROOT / "models" / "llm").glob("*.yaml"))
    if not model_files:
        report.fail("no model YAML files to validate")
        return

    required_keys = {"model", "label", "model_type"}
    bad_files = 0
    for path in model_files:
        try:
            data = _load_yaml(path)
        except yaml.YAMLError as e:
            report.fail(f"invalid YAML: {path.name}: {e}")
            bad_files += 1
            continue

        if not isinstance(data, dict):
            report.fail(f"{path.name}: root must be a mapping")
            bad_files += 1
            continue

        missing = required_keys - data.keys()
        if missing:
            report.fail(f"{path.name}: missing keys {sorted(missing)}")
            bad_files += 1
            continue

        if data.get("model_type") != "llm":
            report.fail(f"{path.name}: model_type must be 'llm'")
            bad_files += 1
            continue

        mode = ((data.get("model_properties") or {}).get("mode"))
        if mode != "chat":
            report.warn(f"{path.name}: model_properties.mode is {mode!r} (expected 'chat')")

    if bad_files == 0:
        report.ok(f"all {len(model_files)} model YAML files validated")
    else:
        report.fail(f"{bad_files} / {len(model_files)} model YAML files have issues")


def check_difyignore(report: Report) -> None:
    _section("5. .difyignore (debug-key leak prevention)")
    difyignore = ROOT / ".difyignore"
    if not difyignore.is_file():
        report.fail(".difyignore missing")
        return
    content = difyignore.read_text(encoding="utf-8")
    if re.search(r"(?m)^\s*\.env\s*$", content):
        report.ok(".difyignore excludes `.env`")
    else:
        report.fail(".difyignore does NOT exclude `.env` — debug key may leak into .difypkg")

    # scripts/, tests/, docs/ are dev-only; excluding them keeps the package tidy.
    for pattern in ("scripts/", "tests/", "docs/"):
        if re.search(rf"(?m)^\s*{re.escape(pattern)}\s*$", content):
            report.ok(f".difyignore excludes `{pattern}`")
        else:
            report.warn(f".difyignore does not exclude `{pattern}` (dev-only content will be packaged)")


def check_no_hardcoded_secrets(report: Report) -> None:
    _section("6. Source hygiene (no hardcoded keys)")
    suspicious_paths = [
        ROOT / "main.py",
        ROOT / "provider" / "moyu.py",
        ROOT / "models" / "llm" / "llm.py",
    ]
    # Anything that looks like `sk-<40+ chars>` or a UUID assigned to a key-ish name.
    uuid_pattern = re.compile(
        r"REMOTE_INSTALL_KEY\s*=\s*[\"']?[0-9a-f]{8}-[0-9a-f]{4}",
        re.IGNORECASE,
    )
    api_key_pattern = re.compile(r"api_key\s*=\s*[\"']sk-[A-Za-z0-9]{20,}", re.IGNORECASE)
    found = False
    for p in suspicious_paths:
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        if uuid_pattern.search(text):
            report.fail(f"{p.relative_to(ROOT)} appears to hardcode REMOTE_INSTALL_KEY")
            found = True
        if api_key_pattern.search(text):
            report.fail(f"{p.relative_to(ROOT)} appears to hardcode an api_key literal")
            found = True
    if not found:
        report.ok("no hardcoded debug key or api_key literals detected in source")


def check_readme_privacy(report: Report) -> None:
    _section("7. Release docs")
    for rel in ("README.md", "readme/README_zh_Hans.md", "privacy.md", "RELEASE_CHECKLIST.md"):
        if (ROOT / rel).is_file():
            report.ok(f"doc exists: {rel}")
        else:
            report.warn(f"doc missing: {rel}")


# ----------------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------------

def main() -> int:
    print(f"Moyu AI plugin preflight check — root: {ROOT}")
    report = Report()

    check_required_files(report)
    check_manifest(report)
    check_provider(report)
    check_model_yamls(report)
    check_difyignore(report)
    check_no_hardcoded_secrets(report)
    check_readme_privacy(report)

    print("\n== Summary ==")
    print(f"  passed:   {len(report.passed)}")
    print(f"  warnings: {len(report.warnings)}")
    print(f"  failed:   {len(report.failed)}")

    summary = {
        "passed": report.passed,
        "warnings": report.warnings,
        "failed": report.failed,
    }
    (ROOT / "scripts" / "preflight_report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nFull report: {ROOT / 'scripts' / 'preflight_report.json'}")

    return 0 if not report.failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
