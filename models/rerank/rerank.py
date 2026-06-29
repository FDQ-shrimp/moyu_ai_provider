"""
Moyu AI rerank adapter.

Moyu exposes a Jina-compatible `POST /v1/rerank` endpoint (verified live for
qwen3-rerank: it returns `results[].relevance_score`), which is exactly the
shape Dify's `OAICompatRerankModel` speaks. We therefore only need to point
the base class at Moyu's endpoint and normalise the credential dict shape.

This module never reads `.env`; the `api_key` comes from the provider
credential form in `provider/moyu.yaml`.
"""

from __future__ import annotations

import logging

from dify_plugin import OAICompatRerankModel
from dify_plugin.config.logger_format import plugin_logger_handler
from dify_plugin.entities.model.rerank import RerankResult

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(plugin_logger_handler)


class MoyuRerankModel(OAICompatRerankModel):
    """Adapter for the Moyu AI Jina-compatible rerank endpoint."""

    BASE_URL = "https://www.moyu.info/v1"

    def _invoke(
        self,
        model: str,
        credentials: dict,
        query: str,
        docs: list[str],
        score_threshold: float | None = None,
        top_n: int | None = None,
        user: str | None = None,
    ) -> RerankResult:
        patched = self._patched_credentials(credentials)
        # Moyu's rerank endpoint rejects a missing / non-positive `top_n`
        # ("parameter top_n should be larger than 0"). Dify's base class
        # forwards `top_n` verbatim and passes None during credential
        # validation, so default it to the document count here.
        effective_top_n = top_n if (top_n and top_n > 0) else len(docs)
        logger.info(
            "moyu rerank invoke model=%s docs=%d top_n=%s", model, len(docs), effective_top_n
        )
        try:
            return super()._invoke(
                model, patched, query, docs, score_threshold, effective_top_n, user
            )
        except Exception:
            logger.exception("moyu rerank failed model=%s", model)
            raise

    def validate_credentials(self, model: str, credentials: dict) -> None:
        patched = self._patched_credentials(credentials)
        super().validate_credentials(model, patched)

    @classmethod
    def _patched_credentials(cls, credentials: dict) -> dict:
        """Return a copy of `credentials` normalised for the OAI base class.

        `OAICompatRerankModel` reads `endpoint_url` and posts to
        `<endpoint_url>/rerank`, so we set it to Moyu's `/v1` base URL.
        """
        patched = dict(credentials or {})
        patched["api_key"] = (patched.get("api_key") or "").strip()
        patched["endpoint_url"] = cls.BASE_URL
        return patched
