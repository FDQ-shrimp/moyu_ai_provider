"""Run SDK 0.9.0 checks with dotenv, inherited settings and networking disabled.

Use the dedicated Python 3.12 environment. No main.py or live probes are run.
Pass --preflight for the existing release preflight; otherwise pass pytest args.
"""

from __future__ import annotations

import importlib.metadata
import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"

from tests.offline_safety import block_transports, enable

enable()
if sys.version_info[:2] != (3, 12):
    raise SystemExit("Offline SDK checks require Python 3.12")
if sys.prefix == sys.base_prefix:
    raise SystemExit("Use an isolated project venv, not a shared base environment")
if importlib.metadata.version("dify_plugin") != "0.9.0":
    raise SystemExit("First-phase SDK contract checks require dify_plugin==0.9.0")

# Import before pytest: SDK gevent patching must precede test collection.
import dify_plugin

block_transports()
print(f"Interpreter: {sys.executable}")
print(f"Python: {sys.version.split()[0]}")
print(f"SDK: {importlib.metadata.version('dify_plugin')}")
print(f"SDK path: {dify_plugin.__file__}")
print("Safety: dotenv/settings sources disabled; real network and subprocesses blocked")

if sys.argv[1:] == ["--preflight"]:
    runpy.run_path(str(ROOT / "scripts" / "preflight_check.py"), run_name="__main__")
else:
    import pytest

    args = sys.argv[1:] or [str(ROOT / "tests"), "-q"]
    raise SystemExit(pytest.main(["-p", "no:cacheprovider", *args]))
