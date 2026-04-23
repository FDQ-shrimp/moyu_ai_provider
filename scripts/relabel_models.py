"""
Rewrite the `label` field of every models/llm/*.yaml to match the raw model
ID. This is a purely local script — no API call — so it is safe to run any
time the display names in Dify drift away from the upstream Moyu AI IDs.

Usage
-----
    python scripts/relabel_models.py
    python scripts/relabel_models.py --dry-run
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models" / "llm"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true",
                   help="Only print what would change; do not write files.")
    return p.parse_args()


def relabel_one(path: Path, dry_run: bool) -> tuple[bool, str]:
    """Return (changed?, description)."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return False, f"{path.name}: YAML error: {e}"

    if not isinstance(data, dict) or "model" not in data:
        return False, f"{path.name}: skipped (no `model` key)"

    model_id = str(data["model"]).strip()
    desired = {"en_US": model_id, "zh_Hans": model_id}
    current = data.get("label")

    if current == desired:
        return False, f"{path.name}: already correct"

    data["label"] = desired

    if dry_run:
        return True, f"{path.name}: would set label -> {model_id}"

    # Preserve the original top-level key order as much as possible: dump
    # with sort_keys=False; Dify does not care about key order.
    path.write_text(
        yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return True, f"{path.name}: label <- {model_id}"


def main() -> int:
    args = parse_args()
    files = sorted(MODELS_DIR.glob("*.yaml"))
    if not files:
        print(f"No YAML files found in {MODELS_DIR}")
        return 1

    changed = 0
    for path in files:
        did, msg = relabel_one(path, args.dry_run)
        prefix = "[CHG]" if did else "[OK ]"
        print(f"  {prefix} {msg}")
        if did:
            changed += 1

    verb = "would change" if args.dry_run else "changed"
    print(f"\nSummary: {verb} {changed} of {len(files)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
