"""
Moyu AI model provider.

Responsibilities
----------------
* Declare the provider-level credential validation entry point.
* Keep provider-level validation *cheap and deterministic*:
  - An empty API Key is rejected immediately with a clear error.
  - Real authentication is deferred to the first model invocation, which
    goes through `MoyuLargeLanguageModel.validate_credentials` /
    `_invoke`. This avoids penalising users when a specific upstream model
    is temporarily unavailable on the Moyu side.

The user only ever fills one field in the Dify UI: `api_key`, declared in
`provider/moyu.yaml`. Nothing in this module reads `.env`.
"""

from __future__ import annotations

import logging

from dify_plugin import ModelProvider
from dify_plugin.errors.model import CredentialsValidateFailedError

logger = logging.getLogger(__name__)


class MoyuProvider(ModelProvider):
    def validate_provider_credentials(self, credentials: dict) -> None:
        api_key = (credentials.get("api_key") or "").strip()
        if not api_key:
            # Keep the message short but bilingual-friendly; Dify surfaces it
            # verbatim to the user.
            raise CredentialsValidateFailedError(
                "API Key is required. 请填写魔芋AI API Key。"
            )

        # Intentional: no upstream call here. The underlying Moyu API has
        # per-model availability quirks that can intermittently 5xx, and we
        # do not want the whole provider setup to fail because one model is
        # unhealthy. Real validation happens during the first actual call.
        logger.debug("moyu provider credentials shape validated (key_len=%d)", len(api_key))
