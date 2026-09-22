"""Stage registered files only; audit/extract a CLI-built release package.

Does not run the plugin, install dependencies, read dotenv, or access networking.
Packaging itself is performed separately using the existing dify-plugin CLI.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import stat
import zipfile

import yaml

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT.parent / "moyu_ai_provider-0.0.6.difypkg"
BASELINE_SHA256 = "0b7e2f188108f1a8bb09cf786c4964f4bb12bc7162ba1b4b8a1cdd2cb9545980"
RELEASE = "0.0.8"
TOOL_FLAGS = {"tool-call", "stream-tool-call", "multi-tool-call"}
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
STREAM_TOOL_CALL_MODELS = TOOL_CALL_MODELS - {
    "MiniMax-M3", "claude-sonnet-4-5-20250929",
    "gemini-3-pro-image-preview", "kimi-k2.7-code",
}
PUBLIC_FILES = {
    ".difyignore", "manifest.yaml", "main.py", "requirements.txt", "LICENSE", "PRIVACY.md",
    "README.md", "readme/README_zh_Hans.md", "icon.png", "_assets/icon.png",
}
CHANGED_FILES = {
    "manifest.yaml", "models/llm/llm.py", "README.md", "readme/README_zh_Hans.md"
}


def ensure(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def selected_files(root=ROOT):
    manifest = yaml.safe_load((root / "manifest.yaml").read_bytes())
    ensure(manifest["plugins"]["models"] == ["provider/moyu.yaml"], "Unexpected provider registration")
    provider = yaml.safe_load((root / "provider/moyu.yaml").read_bytes())
    ensure(set(provider["models"]) == {"llm", "text_embedding"}, "Unexpected model types")
    ensure(len(provider["models"]["llm"]["predefined"]) == 58, "Unexpected LLM count")
    ensure(len(provider["models"]["text_embedding"]["predefined"]) == 4, "Unexpected embedding count")
    files = PUBLIC_FILES | {"provider/moyu.yaml", provider["extra"]["python"]["provider_source"]}
    files.update(provider["extra"]["python"]["model_sources"])
    for group in provider["models"].values():
        files.update(group["predefined"])
    for name in files:
        relative = Path(name)
        ensure(not relative.is_absolute() and ".." not in relative.parts
               and not any(c in name for c in "*?[]\\"), "Non-explicit package path")
        ensure(relative.name != ".env" and not relative.name.startswith(".env."), "Dotenv is forbidden")
        source = root / relative
        ensure(source.resolve().is_relative_to(root.resolve()) and source.is_file()
               and not source.is_symlink(), "Missing/unsafe source path")
    ensure(len(files) == 76, "Unexpected package file count")
    return files


def check_secrets(name, content):
    if Path(name).suffix.lower() in {".png", ".jpg", ".ico"}:
        return
    # Report paths only, never a matched value. No real key is needed for scanning.
    patterns = [rb"sk-[A-Za-z0-9_-]{20,}",
                rb"REMOTE_INSTALL_KEY\s*=\s*[\"']?[0-9a-fA-F]{8}-[0-9a-fA-F]{4}",
                rb"Bearer\s+[A-Za-z0-9_-]{30,}"]
    ensure(not any(re.search(pattern, content) for pattern in patterns), "Possible credential in " + name)


def compare_baseline(files):
    ensure(sha256(BASELINE.read_bytes()) == BASELINE_SHA256, "Original 0.0.6 package hash changed")
    with zipfile.ZipFile(BASELINE) as archive:
        ensure(set(archive.namelist()) == files, "Registration/runtime file scope differs from 0.0.6")
        baseline_manifest = yaml.safe_load(archive.read("manifest.yaml"))
        baseline_manifest["version"] = RELEASE
        ensure(yaml.safe_load((ROOT / "manifest.yaml").read_bytes()) == baseline_manifest,
               "Manifest changed beyond approved release version")
        registered_llms = {
            yaml.safe_load((ROOT / name).read_bytes())["model"]: name
            for name in files
            if name.startswith("models/llm/") and name.endswith(".yaml")
        }
        ensure(set(registered_llms) >= TOOL_CALL_MODELS, "Approved model is not registered")
        for model_id, name in registered_llms.items():
            expected = yaml.safe_load(archive.read(name))
            if model_id in TOOL_CALL_MODELS:
                expected["features"].append("tool-call")
            if model_id in STREAM_TOOL_CALL_MODELS:
                expected["features"].append("stream-tool-call")
            ensure(yaml.safe_load((ROOT / name).read_bytes()) == expected,
                   "Model changed beyond approved capabilities: " + model_id)
        expected_model_files = {registered_llms[model_id] for model_id in TOOL_CALL_MODELS}
        expected_changed = CHANGED_FILES | expected_model_files
        changed = {name for name in files if archive.read(name) != (ROOT / name).read_bytes()}
        ensure(changed == expected_changed,
               "Unexpected cumulative production file changes: " + str(sorted(changed)))
    return sorted(changed)


def stage(destination):
    files = selected_files()
    compare_baseline(files)
    destination = Path(destination).resolve()
    ensure(not destination.exists(), "Stage already exists; refusing overwrite")
    ensure(not destination.is_relative_to(ROOT), "Stage must be outside source repository")
    destination.mkdir(parents=False)
    for name in sorted(files):
        content = (ROOT / name).read_bytes()
        check_secrets(name, content)
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    print(json.dumps({"stage": str(destination), "files": len(files), "llm": 58, "embedding": 4}))


def audit(package, unpack, report_path=None):
    files = selected_files()
    changed = compare_baseline(files)
    package, unpack = Path(package).resolve(), Path(unpack).resolve()
    ensure(package != BASELINE.resolve(), "Cannot audit original as new release package")
    ensure(not unpack.exists() and not unpack.is_relative_to(ROOT), "Unsafe/existing unpack directory")
    hashes = {}
    with zipfile.ZipFile(package) as archive:
        names = archive.namelist()
        ensure(len(names) == len(set(names)) and set(names) == files, "Unexpected/duplicate archive members")
        ensure(archive.testzip() is None, "ZIP CRC check failed")
        for info in archive.infolist():
            ensure(not stat.S_ISLNK(info.external_attr >> 16), "Symlink in package")
            content = archive.read(info.filename)
            ensure(content == (ROOT / info.filename).read_bytes(), "Package/source mismatch: " + info.filename)
            check_secrets(info.filename, content)
            hashes[info.filename] = sha256(content)
        manifest = yaml.safe_load(archive.read("manifest.yaml"))
        ensure(manifest["version"] == RELEASE and manifest["meta"]["version"] == "0.0.6"
               and manifest["meta"]["runner"]["version"] == "3.12", "Wrong internal version")
        tool_count = stream_count = multi_count = 0
        approved_tool_models = {}
        for name in files:
            if name.startswith("models/llm/") and name.endswith(".yaml"):
                model = yaml.safe_load(archive.read(name))
                model_id = model["model"]
                expected = ({"tool-call"} if model_id in TOOL_CALL_MODELS else set())
                if model_id in STREAM_TOOL_CALL_MODELS:
                    expected.add("stream-tool-call")
                ensure(set(model.get("features", [])) & TOOL_FLAGS == expected,
                       "Unexpected tool capability: " + name)
                tool_count += "tool-call" in expected
                stream_count += "stream-tool-call" in expected
                multi_count += "multi-tool-call" in expected
                if expected:
                    approved_tool_models[model_id] = sorted(expected)
        ensure((tool_count, stream_count, multi_count) == (41, 37, 0),
               "Unexpected packaged tool capability counts")
        # Extract only after verifying every member against the explicit safe list.
        unpack.mkdir()
        archive.extractall(unpack)
    for name, digest in hashes.items():
        ensure(sha256((unpack / name).read_bytes()) == digest, "Extracted file mismatch")
    ensure(sha256(BASELINE.read_bytes()) == BASELINE_SHA256, "Original package changed during audit")
    report = {
        "package": str(package), "version": RELEASE, "sha256": sha256(package.read_bytes()),
        "size_bytes": package.stat().st_size, "unpacked_at": str(unpack),
        "baseline_sha256": BASELINE_SHA256, "baseline_unchanged": True,
        "files": len(files), "llm_yaml": 58, "embedding_yaml": 4, "rerank_files": 0,
        "same_file_scope_as_0_0_6": True, "all_files_match_current_source": True,
        "llm_adapter_sha256": hashes["models/llm/llm.py"],
        "tool_call_models": tool_count, "stream_tool_call_models": stream_count,
        "multi_tool_call_models": multi_count,
        "approved_tool_models": approved_tool_models,
        "changed_from_0_0_6": changed, "credential_pattern_scan": "passed",
        "internal_files_and_unregistered_models_absent": True, "file_sha256": hashes,
    }
    report_path = Path(report_path).resolve() if report_path else ROOT / "scripts" / "local_package_audit_0.0.8.json"
    ensure(not report_path.exists(), "Audit report path already exists")
    with report_path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps({key: value for key, value in report.items() if key != "file_sha256"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("stage", "audit"))
    parser.add_argument("path")
    parser.add_argument("--unpack")
    parser.add_argument("--report")
    args = parser.parse_args()
    if args.mode == "stage":
        stage(args.path)
    else:
        ensure(args.unpack is not None, "--unpack is required")
        audit(args.path, args.unpack, args.report)
