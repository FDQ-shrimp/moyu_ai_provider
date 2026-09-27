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

    1. Supplying Moyu's current domestic endpoint as the default (`BASE_URL`)
       while preserving an endpoint selected in the provider credentials.
    2. Normalising the credential dict shape the base class expects
       (`api_key`, `endpoint_url`, `mode`, `function_calling_type`). This is what
       `_patch_credentials` does.

Important: this module never reads `.env`. The `api_key` it receives comes
from the user-facing provider credential form defined in
`provider/moyu.yaml`.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Generator
from copy import copy
from typing import Optional, Union

from requests import Response

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

    # Default base URL for Moyu's OpenAI-compatible REST API.
    # Chat completions live at `<BASE_URL>/chat/completions`.
    BASE_URL = "https://www.moyu.cn/v1"
    THINKING_MODELS = frozenset({
        "qwen3.6-27b", "qwen3.6-plus", "qwen3.6-35b-a3b",
        "qwen3.6-flash", "qwen3.7-max", "qwen3.7-plus", "qwen3.8-max",
        "qwen-plus", "qwen3-max",
    })
    OBJECT_THINKING_MODELS = frozenset({"glm-5.1", "glm-5.2", "kimi-k2.6"})
    DEEPSEEK_THINKING_MODELS = frozenset({"deepseek-v4-flash", "deepseek-v4-pro"})
    VERIFIED_EFFORT_THINKING_MODELS = frozenset({"gpt-5.5", "gpt-5.6-luna"})
    CHINA_ONLY_THINKING_MODELS = frozenset({"qwen-plus", "qwen3-max", "deepseek-v4-flash"})
    OVERSEAS_ONLY_THINKING_MODELS = VERIFIED_EFFORT_THINKING_MODELS
    OVERSEAS_URL = "https://www.konjac.ai/v1"
    VERIFIED_SITE_ENDPOINTS = {
        "deepseek-v4-flash": frozenset({BASE_URL}),
        "deepseek-v4-pro": frozenset({BASE_URL, OVERSEAS_URL}),
        "gpt-5.5": frozenset({OVERSEAS_URL}),
        "gpt-5.6-luna": frozenset({OVERSEAS_URL}),
    }
    EXPOSED_THINKING_MODELS = (THINKING_MODELS | OBJECT_THINKING_MODELS |
                               DEEPSEEK_THINKING_MODELS | VERIFIED_EFFORT_THINKING_MODELS)
    # Exact-ID protocol registry. Only EXPOSED_THINKING_MODELS are consulted
    # by the production path; all other profiles remain offline candidates.
    CANDIDATE_THINKING_PROFILES = {
        **{model: ("qwen-toggle", ()) for model in (
            "qwen3.6-35b-a3b", "qwen3.6-flash", "qwen3.7-max",
            "qwen3.7-plus", "qwen3.8-max", "qwen-plus", "qwen3-max",
        )},
        **{model: ("object-toggle", ()) for model in (
            "glm-5.1", "glm-5.2", "GLM-5", "kimi-k2.6",
        )},
        **{model: ("effort", values) for model, values in {
            "gpt-5.5": ("none", "low", "medium", "high", "xhigh"),
            "gpt-5.6-luna": ("none", "low", "medium", "high", "xhigh", "max"),
            "gpt-5.6-sol": ("none", "low", "medium", "high", "xhigh", "max"),
            "gpt-5.6-terra": ("none", "low", "medium", "high", "xhigh", "max"),
            "gpt-6-astra": ("low", "medium", "high", "xhigh", "max"),
            "gemini-2.5-flash": ("none", "low", "medium", "high"),
            "gemini-2.5-flash-lite": ("none", "low", "medium", "high"),
            "gemini-2.5-pro": ("low", "medium", "high"),
            "gemini-3-flash-preview": ("minimal", "low", "medium", "high"),
            "gemini-3.1-pro-preview": ("low", "medium", "high"),
            "gemini-3.5-flash": ("minimal", "low", "medium", "high"),
            "gemini-3.6-flash": ("minimal", "low", "medium", "high"),
            "kimi-k3": ("low", "high", "max"),
        }.items()},
        "claude-haiku-4-5-20251001": ("claude-budget", ()),
        "claude-sonnet-4-6": ("claude-budget", ()),
        "claude-sonnet-5": ("claude-adaptive", ("low", "medium", "high")),
    }
    THINKING_CONTROL_FIELDS = frozenset({
        "thinking_mode", "enable_thinking", "thinking_budget",
        "reasoning_effort", "thinking", "output_config",
    })

    def get_model_schema(self, model, credentials=None):
        schema = super().get_model_schema(model, credentials)
        endpoint = self._patched_credentials(credentials or {}).get("endpoint_url")
        site_blocked = (
            (model in self.CHINA_ONLY_THINKING_MODELS and endpoint != self.BASE_URL) or
            (model in self.VERIFIED_SITE_ENDPOINTS and
             endpoint not in self.VERIFIED_SITE_ENDPOINTS[model])
        )
        if schema is not None and site_blocked:
            # Dify asks for parameter rules with provider credentials. Never
            # advertise a control on a site without this exact model's evidence.
            control_name = ("reasoning_effort" if model in self.VERIFIED_EFFORT_THINKING_MODELS
                            else "thinking_mode")
            return schema.model_copy(update={
                "parameter_rules": [rule for rule in schema.parameter_rules
                                    if rule.name != control_name]
            })
        return schema

    def _validate_and_filter_model_parameters(self, model, model_parameters, credentials):
        # Migrate saved values from the previous boolean UI before the SDK
        # filters undeclared fields. Never mutate a workflow's input dict.
        parameters = dict(model_parameters)
        if model in self.THINKING_MODELS:
            legacy = parameters.pop("enable_thinking", None)
            if parameters.get("thinking_mode") is None and legacy is not None:
                if type(legacy) is not bool:
                    raise ValueError("invalid_legacy_thinking_boolean")
                setting = "开启" if legacy else "关闭"
                parameters["thinking_mode"] = setting
            # An explicit dropdown choice supersedes a saved legacy value.
        return super()._validate_and_filter_model_parameters(model, parameters, credentials)

    @classmethod
    def _thinking_parameters(cls, model, model_parameters):
        parameters = dict(model_parameters)
        if model in cls.DEEPSEEK_THINKING_MODELS:
            setting = parameters.pop("thinking_mode", "开启")
            if type(setting) is not str or setting not in ("关闭", "开启"):
                raise ValueError("invalid_thinking_mode")
            if "thinking" in parameters:
                raise ValueError("conflicting_thinking_controls")
            parameters["thinking"] = {"type": "enabled" if setting == "开启" else "disabled"}
            return parameters
        if model in cls.VERIFIED_EFFORT_THINKING_MODELS:
            if "reasoning_effort" in parameters:
                effort = parameters["reasoning_effort"]
                if type(effort) is not str or effort not in ("none", "low"):
                    raise ValueError("unverified_reasoning_effort")
                if "thinking" in parameters or "output_config" in parameters:
                    raise ValueError("conflicting_thinking_controls")
            return parameters
        if model in cls.OBJECT_THINKING_MODELS:
            # Match the user-approved default-off dropdown. SDK 0.9.0 cannot
            # declare an object rule, so transform the string after filtering.
            parameters.setdefault("thinking_mode", "关闭")
            return cls._candidate_thinking_parameters(model, parameters)
        if model not in cls.THINKING_MODELS:
            # Do not let a private candidate mapping become an accidental
            # production feature via a direct _invoke call.
            if cls.THINKING_CONTROL_FIELDS.intersection(parameters):
                raise ValueError("unapproved_thinking_control")
            return parameters
        if "thinking_mode" in parameters:
            setting = parameters.pop("thinking_mode")
            if not isinstance(setting, str) or setting not in ("关闭", "开启"):
                raise ValueError("invalid_thinking_mode")
            enabled = setting == "开启"
            if "enable_thinking" in parameters and parameters["enable_thinking"] is not enabled:
                raise ValueError("conflicting_thinking_controls")
        else:
            enabled = parameters.get("enable_thinking", False)
            if type(enabled) is not bool:
                raise ValueError("invalid_legacy_thinking_boolean")
        parameters["enable_thinking"] = enabled
        return parameters

    @classmethod
    def _candidate_thinking_parameters(cls, model, model_parameters):
        """Pure, explicit-ID candidate mapper for offline contract tests only.

        Never called by the production request path. The nested Claude/GLM
        and compatible effort shapes require relay validation before exposure.
        """
        if model not in cls.CANDIDATE_THINKING_PROFILES:
            raise ValueError("unknown_thinking_candidate")
        protocol, options = cls.CANDIDATE_THINKING_PROFILES[model]
        parameters = dict(model_parameters)
        if protocol in ("qwen-toggle", "object-toggle"):
            source = "thinking_mode"
            if source not in parameters:
                return parameters
            choice = parameters.pop(source)
            if type(choice) is not str or choice not in ("关闭", "开启"):
                raise ValueError("invalid_thinking_mode")
            target = "enable_thinking" if protocol == "qwen-toggle" else "thinking"
            if target in parameters:
                raise ValueError("conflicting_thinking_controls")
            parameters[target] = (choice == "开启") if protocol == "qwen-toggle" else {
                "type": "enabled" if choice == "开启" else "disabled"
            }
        elif protocol == "effort":
            # This is a Chat Completions candidate, not the official native
            # Responses/Gemini wire contract and not an approved live mapping.
            choice = parameters.get("reasoning_effort")
            if choice is not None and (type(choice) is not str or choice not in options):
                raise ValueError("invalid_reasoning_effort")
        elif protocol == "claude-budget":
            if "thinking_budget" not in parameters:
                return parameters
            budget = parameters.pop("thinking_budget")
            if type(budget) is not int or budget < 1024:
                raise ValueError("invalid_thinking_budget")
            if "thinking" in parameters:
                raise ValueError("conflicting_thinking_controls")
            parameters["thinking"] = {"type": "enabled", "budget_tokens": budget}
        elif protocol == "claude-adaptive":
            if "reasoning_effort" not in parameters:
                return parameters
            choice = parameters.pop("reasoning_effort")
            if type(choice) is not str or choice not in options:
                raise ValueError("invalid_reasoning_effort")
            if "thinking" in parameters or "output_config" in parameters:
                raise ValueError("conflicting_thinking_controls")
            parameters["thinking"] = {"type": "adaptive"}
            parameters["output_config"] = {"effort": choice}
        return parameters

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
        site_blocked = (
            (model in self.CHINA_ONLY_THINKING_MODELS and
             patched["endpoint_url"] != self.BASE_URL) or
            (model in self.VERIFIED_SITE_ENDPOINTS and
             patched["endpoint_url"] not in self.VERIFIED_SITE_ENDPOINTS[model])
        )
        if site_blocked:
            if self.THINKING_CONTROL_FIELDS.intersection(model_parameters):
                if model in {"qwen-plus", "qwen3-max"}:
                    raise ValueError("domestic_only_thinking_control")
                raise ValueError("unverified_site_thinking_control")
            parameters = dict(model_parameters)
        else:
            parameters = self._thinking_parameters(model, model_parameters)
        logger.info("moyu invoke start model=%s stream=%s", model, stream)
        try:
            result = super()._invoke(
                model,
                patched,
                prompt_messages,
                parameters,
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

    def _handle_generate_response(
        self,
        model: str,
        credentials: dict,
        response: Response,
        prompt_messages: list[PromptMessage],
    ) -> LLMResult:
        # SDK 0.9.0 indexes message["content"], although a tool-only reply
        # can omit it. Normalize only that shape; SDK still parses tool calls,
        # usage and errors. Keep the original transport response unchanged.
        if credentials.get("function_calling_type") == "tool_call":
            payload = response.json()
            message = payload["choices"][0].get("message", {})
            if isinstance(message, dict) and message.get("tool_calls") and "content" not in message:
                message["content"] = ""
                response = copy(response)
                response._content = json.dumps(payload).encode("utf-8")
                response.encoding = "utf-8"
        return super()._handle_generate_response(model, credentials, response, prompt_messages)

    # ---------------------------------------------------------------------
    # Credential normalisation
    # ---------------------------------------------------------------------

    @classmethod
    def _patched_credentials(cls, credentials: dict) -> dict:
        """Return a shallow copy of `credentials` normalised for the OAI base.

        Dify stores what the user typed (`api_key` and optional
        `endpoint_url`) in the credential dict.
        `OAICompatLargeLanguageModel` expects:

            * `api_key`      — the raw bearer token
            * `endpoint_url` — full base URL including `/v1`
            * `mode`         — "chat" for chat-completion models
            * `function_calling_type` — modern tools/tool_calls wire protocol

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
        endpoint_url = str(credentials.get("endpoint_url") or "").strip()
        credentials["endpoint_url"] = (endpoint_url or cls.BASE_URL).rstrip("/")
        credentials["mode"] = "chat"
        # Keep the protocol active even when tools is empty: the final Agent
        # turn still needs assistant tool_calls and role=tool history.
        # This transport setting does not advertise any model capability.
        credentials["function_calling_type"] = "tool_call"
