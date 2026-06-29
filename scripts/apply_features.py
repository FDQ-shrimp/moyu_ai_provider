"""Recompute the `features` field of every existing models/llm/*.yaml.

Unlike sync_models.py (which regenerates the whole catalogue from the live
API and would re-introduce models we deliberately removed), this script only
*relabels* the curated set already on disk. It uses the same evidence-based
`infer_features()` logic from sync_models.py, so VISION tags stay consistent.

Usage:
    python scripts/apply_features.py            # apply
    python scripts/apply_features.py --dry-run  # preview only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_models import infer_features  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ROOT / "models" / "llm"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    files = sorted(MODELS_DIR.glob("*.yaml"))
    if not files:
        print(f"No YAML files in {MODELS_DIR}")
        return 1

    changed = 0
    for path in files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or "model" not in data:
            continue
        model_id = str(data["model"]).strip()
        desired = infer_features(model_id)
        current = data.get("features")
        if current == desired:
            continue
        gained = "vision" in desired and "vision" not in (current or [])
        lost = "vision" in (current or []) and "vision" not in desired
        tag = "+VISION" if gained else ("-VISION" if lost else "~")
        print(f"  [{tag}] {model_id}: {current} -> {desired}")
        changed += 1
        if not args.dry_run:
            data["features"] = desired
            path.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

    verb = "would change" if args.dry_run else "changed"
    print(f"\nSummary: {verb} {changed} of {len(files)} files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
