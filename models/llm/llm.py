"""
Moyu AI Large Language Model adapter.

Why subclass `OAICompatLargeLanguageModel`?
-------------------------------------------
Moyu AI exposes an OpenAI-compatible HTTP API (same request/response shapes
for `/chat/completions`). Dify ships a first-class base class for exactly
this case, `OAICompatLargeLanguageModel`, which handles:

    * streaming vs non-streaming
    * tool / function calling parameter passing
    * token usage accounting
    * error normalisation to Dify's own exception types

So the plugin-specific work reduces to:

    1. Pointing the base class at Moyu's endpoint (`BASE_URL`).
    2. Normalising the credential dict shape the base class expects
       (`api_key`, `endpoint_url`, `mode`). This is what
       `_patch_credentials` does.

Important: this module never reads `.env`. The `api_key` it receives comes
from the user-facing provider credential form defined in
`provider/moyu.yaml`.
"""

from __future__ import annotations

import logging
from collections.abc import Generator
from typing import Optional, Union

from dify_plugin import OAICompatLargeLanguageModel
from dify_plugin.config.logger_format import plugin_logger_handler
from dify_plugin.entities.model.llm import LLMResult
from dify_plugin.entities.model.message import PromptMessage, PromptMessageTool

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(plugin_logger_handler)


class MoyuLargeLanguageModel(OAICompatLargeLanguageModel):
    """Adapter for the Moyu AI OpenAI-compatible LLM endpoint."""

    # Base URL for Moyu's OpenAI-compatible REST API.
    # Chat completions live at `<BASE_URL>/chat/completions`.
    BASE_URL = "https://www.moyu.info/v1"

    def _invoke(
        self,
        model: str,
        credentials: dict,
        prompt_messages: list[PromptMessage],
        model_parameters: dict,
        tools: Optional[list[PromptMessageTool]] = None,
        stop: Optional[list[str]] = None,
        stream: bool = True,
        user: Optional[str] = None,
    ) -> Union[LLMResult, Generator]:
        patched = self._patched_credentials(credentials)
        logger.info("moyu invoke start model=%s stream=%s", model, stream)
        try:
            result = super()._invoke(
                model,
                patched,
                prompt_messages,
                model_parameters,
                tools,
                stop,
                stream,
                user,
            )
            logger.info("moyu invoke success model=%s", model)
            return result
        except Exception as e:
            # Log class + short message only — never log the api_key itself.
            logger.exception(
                "moyu invoke failed model=%s err_type=%s",
                model,
                type(e).__name__,
            )
            raise

    def validate_credentials(self, model: str, credentials: dict) -> None:
        """Called by Dify when the user saves the provider configuration.

        We delegate to the OAI-compatible base class, which performs a tiny
        real request to confirm the key works for at least the target model.
        """
        patched = self._patched_credentials(credentials)
        super().validate_credentials(model, patched)

    # ---------------------------------------------------------------------
    # Credential normalisation
    # ---------------------------------------------------------------------

    @classmethod
    def _patched_credentials(cls, credentials: dict) -> dict:
        """Return a shallow copy of `credentials` normalised for the OAI base.

        Dify stores what the user typed (`api_key`) in the credential dict.
        `OAICompatLargeLanguageModel` expects:

            * `api_key`      — the raw bearer token
            * `endpoint_url` — full base URL including `/v1`
            * `mode`         — "chat" for chat-completion models

        We never mutate the caller's dict (avoids leaking state across calls).
        """
        patched = dict(credentials or {})
        cls._patch_credentials(patched)
        return patched

    @classmethod
    def _patch_credentials(cls, credentials: dict) -> None:
        """In-place version retained for compatibility with tests/tools."""
        api_key = (credentials.get("api_key") or "").strip()
        credentials["api_key"] = api_key
        credentials["endpoint_url"] = cls.BASE_URL
        credentials["mode"] = "chat"
