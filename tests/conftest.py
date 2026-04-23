"""
Pytest configuration for the Moyu AI plugin tests.

These tests run fully offline. To avoid requiring the real `dify_plugin`
package to be importable in CI, we inject a minimal fake module tree
covering only the symbols our source files import at module load time.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

# Ensure the project root is on sys.path so `import provider.moyu`,
# `import models.llm.llm`, etc., work.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _install_fake_dify_plugin() -> None:
    """Install a minimal fake `dify_plugin` package if the real one is missing."""
    if "dify_plugin" in sys.modules:
        return

    try:
        import dify_plugin  # noqa: F401
        return
    except ImportError:
        pass

    # --- root package ---
    pkg = types.ModuleType("dify_plugin")
    pkg.__path__ = []  # mark as a package

    class ModelProvider:
        def validate_provider_credentials(self, credentials: dict) -> None:  # pragma: no cover
            raise NotImplementedError

    class OAICompatLargeLanguageModel:
        def _invoke(self, *args, **kwargs):  # pragma: no cover
            raise NotImplementedError

        def validate_credentials(self, *args, **kwargs):  # pragma: no cover
            return None

    class DifyPluginEnv:
        pass

    class Plugin:
        def __init__(self, env):  # pragma: no cover
            self._env = env

        def run(self):  # pragma: no cover
            pass

    pkg.ModelProvider = ModelProvider
    pkg.OAICompatLargeLanguageModel = OAICompatLargeLanguageModel
    pkg.DifyPluginEnv = DifyPluginEnv
    pkg.Plugin = Plugin
    sys.modules["dify_plugin"] = pkg

    # --- errors.model ---
    errors_pkg = types.ModuleType("dify_plugin.errors")
    errors_pkg.__path__ = []
    errors_model = types.ModuleType("dify_plugin.errors.model")

    class CredentialsValidateFailedError(Exception):
        pass

    errors_model.CredentialsValidateFailedError = CredentialsValidateFailedError
    sys.modules["dify_plugin.errors"] = errors_pkg
    sys.modules["dify_plugin.errors.model"] = errors_model
    pkg.errors = errors_pkg
    errors_pkg.model = errors_model

    # --- config.logger_format ---
    config_pkg = types.ModuleType("dify_plugin.config")
    config_pkg.__path__ = []
    logger_fmt = types.ModuleType("dify_plugin.config.logger_format")
    import logging

    logger_fmt.plugin_logger_handler = logging.StreamHandler()
    sys.modules["dify_plugin.config"] = config_pkg
    sys.modules["dify_plugin.config.logger_format"] = logger_fmt
    pkg.config = config_pkg
    config_pkg.logger_format = logger_fmt

    # --- entities.model.{llm,message} ---
    entities_pkg = types.ModuleType("dify_plugin.entities")
    entities_pkg.__path__ = []
    model_pkg = types.ModuleType("dify_plugin.entities.model")
    model_pkg.__path__ = []

    llm_mod = types.ModuleType("dify_plugin.entities.model.llm")

    class LLMResult:  # placeholder
        pass

    llm_mod.LLMResult = LLMResult

    msg_mod = types.ModuleType("dify_plugin.entities.model.message")

    class PromptMessage:
        pass

    class PromptMessageTool:
        pass

    msg_mod.PromptMessage = PromptMessage
    msg_mod.PromptMessageTool = PromptMessageTool

    sys.modules["dify_plugin.entities"] = entities_pkg
    sys.modules["dify_plugin.entities.model"] = model_pkg
    sys.modules["dify_plugin.entities.model.llm"] = llm_mod
    sys.modules["dify_plugin.entities.model.message"] = msg_mod
    pkg.entities = entities_pkg
    entities_pkg.model = model_pkg
    model_pkg.llm = llm_mod
    model_pkg.message = msg_mod


_install_fake_dify_plugin()
