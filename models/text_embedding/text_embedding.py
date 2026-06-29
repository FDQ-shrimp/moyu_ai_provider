"""
Moyu AI text-embedding adapter.

Moyu exposes an OpenAI-compatible `POST /v1/embeddings` endpoint (verified
live for text-embedding-v2/v4 and gemini-embedding-*), so we reuse Dify's
`OAICompatEmbeddingModel`, which already handles batching, token accounting
and error normalisation.

Plugin-specific work is limited to pointing the base class at Moyu's endpoint
and normalising the credential dict shape. This module never reads `.env`;
the `api_key` comes from the provider credential form in `provider/moyu.yaml`.
"""

from __future__ import annotations

import logging

from dify_plugin import OAICompatEmbeddingModel
from dify_plugin.config.logger_format import plugin_logger_handler
from dify_plugin.entities.model import EmbeddingInputType
from dify_plugin.entities.model.text_embedding import TextEmbeddingResult

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(plugin_logger_handler)


class MoyuTextEmbeddingModel(OAICompatEmbeddingModel):
    """Adapter for the Moyu AI OpenAI-compatible embeddings endpoint."""

    BASE_URL = "https://www.moyu.info/v1"

    def _invoke(
        self,
        model: str,
        credentials: dict,
        texts: list[str],
        user: str | None = None,
        input_type: EmbeddingInputType = EmbeddingInputType.DOCUMENT,
    ) -> TextEmbeddingResult:
        patched = self._patched_credentials(credentials)
        logger.info("moyu embedding invoke model=%s texts=%d", model, len(texts))
        try:
            return super()._invoke(model, patched, texts, user, input_type)
        except Exception:
            logger.exception("moyu embedding failed model=%s", model)
            raise

    def validate_credentials(self, model: str, credentials: dict) -> None:
        patched = self._patched_credentials(credentials)
        super().validate_credentials(model, patched)

    @classmethod
    def _patched_credentials(cls, credentials: dict) -> dict:
        """Return a copy of `credentials` normalised for the OAI base class.

        `OAICompatEmbeddingModel` expects `api_key` and `endpoint_url`
        (the base URL including `/v1`). It appends `embeddings` itself.
        """
        patched = dict(credentials or {})
        patched["api_key"] = (patched.get("api_key") or "").strip()
        patched["endpoint_url"] = cls.BASE_URL
        return patched
