"""
Entry point for the Moyu AI Dify model-provider plugin.

Design notes
------------
* Local remote-debug workflow (developer-only):
    - Developer creates a `.env` file next to this module containing
      REMOTE_INSTALL_* and INSTALL_METHOD variables issued by Dify.
    - These variables are consumed by the Dify plugin runtime itself,
      NOT by any user-facing feature of this plugin.
* Packaged install (end user):
    - The `.env` file is excluded from the .difypkg via `.difyignore`.
    - Dify injects its own runtime env vars; no local file is needed.
    - The end user only supplies their Moyu AI API Key via the provider
      credential form (see `provider/moyu.yaml`).

Therefore this module never references `api_key` or any user credential.
It only bootstraps the plugin runtime.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dify_plugin import DifyPluginEnv, Plugin

# `python-dotenv` is optional at runtime: in a packaged install the library is
# still importable (it's declared in requirements.txt), but no `.env` file is
# shipped, so load_dotenv becomes a no-op.
try:
    from dotenv import load_dotenv

    _env_path = Path(__file__).resolve().parent / ".env"
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
except ImportError:
    # python-dotenv is not available — safe to ignore for non-debug installs.
    pass

logger = logging.getLogger("moyu_plugin")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

# Only log a coarse indicator of the runtime mode, never the debug key itself.
logger.info(
    "moyu plugin runtime starting (install_method=%s)",
    os.getenv("INSTALL_METHOD", "packaged"),
)

plugin = Plugin(DifyPluginEnv())

if __name__ == "__main__":
    plugin.run()
