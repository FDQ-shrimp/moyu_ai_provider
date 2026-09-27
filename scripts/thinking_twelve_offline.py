"""Test-only contracts for twelve exact Thinking Control candidates.

No production adapter imports this module. Observations retain only structural
signals and integer usage, never answer or reasoning text.
"""

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

MANUAL = frozenset({
    "claude-haiku-4-5-20251001", "claude-opus-4-5-20251101",
    "claude-sonnet-4-5-20250929",
})
ADAPTIVE = frozenset({
    "claude-sonnet-4-6", "claude-opus-4-6", "claude-opus-4-7",
    "claude-opus-4-8",
})
GEMINI = frozenset({"gemini-2.5-flash", "gemini-2.5-flash-lite"})
GPT = frozenset({"gpt-5.6-sol", "gpt-5.6-terra"})
MODELS = frozenset({"GLM-5"}) | MANUAL | ADAPTIVE | GEMINI | GPT
CONTROL_FIELDS = frozenset({
    "thinking_mode", "reasoning_effort", "thinking_budget", "thinking",
    "output_config", "enable_thinking",
})
MAX_TOKENS = 2048
MANUAL_BUDGET = 1024
ROOT = Path(__file__).resolve().parents[1]


def candidate_adapter(model):
    """In-memory schema and exact mapper, shared by SDK tests and live gate."""
    import yaml
    from dify_plugin.entities.model import AIModelEntity
    from models.llm.llm import MoyuLargeLanguageModel

    field = field_for(model)
    schema = yaml.safe_load((ROOT / "models/llm" / f"{model}.yaml").read_text("utf-8"))
    if schema["model"] != model:
        raise ValueError("candidate_schema_mismatch")
    schema["parameter_rules"] = [rule for rule in schema["parameter_rules"]
                                 if rule["name"] != field]
    schema["parameter_rules"].append({
        "name": field, "type": "string", "required": False,
        "label": {"en_US": "Verification only"}, "options": list(values_for(model)),
    })

    class Candidate(MoyuLargeLanguageModel):
        @classmethod
        def _thinking_parameters(cls, selected_model, parameters):
            return map_candidate(selected_model, parameters)

    adapter = Candidate([AIModelEntity.model_validate(schema)])

    def no_estimate(*args, **kwargs):
        raise ValueError("missing_usage_no_estimation")

    adapter._num_tokens_from_string = no_estimate
    return adapter


def field_for(model):
    if model not in MODELS:
        raise ValueError("unknown_exact_candidate")
    return "reasoning_effort" if model in GEMINI | GPT else "thinking_mode"


def values_for(model):
    field_for(model)
    return ("low", "none") if model in GEMINI | GPT else ("开启", "关闭")


def map_candidate(model, source):
    """Return a new HTTP parameter dict; reject alias/target collisions."""
    field = field_for(model)
    parameters = deepcopy(source)
    if field not in parameters:
        if CONTROL_FIELDS & parameters.keys():
            raise ValueError("conflicting_thinking_controls")
        return parameters
    value = parameters.pop(field)
    if type(value) is not str or value not in values_for(model):
        raise ValueError("invalid_candidate_control")
    if CONTROL_FIELDS & parameters.keys():
        raise ValueError("conflicting_thinking_controls")
    if model in MANUAL | ADAPTIVE:
        # Claude's exact-model sampling restrictions are checked, never
        # silently stripped from a workflow's request.
        if model in {"claude-opus-4-7", "claude-opus-4-8"}:
            if ("temperature" in parameters and parameters["temperature"] != 1.0 or
                    "top_p" in parameters and parameters["top_p"] != 1.0):
                raise ValueError("claude_nondefault_sampling_forbidden")
        if value == "开启":
            if "temperature" in parameters:
                raise ValueError("claude_thinking_temperature_forbidden")
            if "top_p" in parameters and not (0.95 <= parameters["top_p"] <= 1.0):
                raise ValueError("claude_thinking_top_p_out_of_range")
    if model in GEMINI | GPT:
        parameters["reasoning_effort"] = value
    elif model == "GLM-5":
        parameters["thinking"] = {"type": "enabled" if value == "开启" else "disabled"}
    elif model in MANUAL:
        if value == "开启":
            limit = parameters.get("max_tokens")
            if type(limit) is not int or not MANUAL_BUDGET < limit:
                raise ValueError("thinking_budget_must_be_below_max_tokens")
            parameters["thinking"] = {"type": "enabled", "budget_tokens": MANUAL_BUDGET}
        else:
            parameters["thinking"] = {"type": "disabled"}
    else:
        parameters["thinking"] = ({"type": "adaptive", "display": "summarized"}
                                  if value == "开启" else {"type": "disabled"})
    return parameters


@dataclass(frozen=True)
class Observation:
    valid: bool
    final_answer: bool
    reasoning_content: bool
    thinking_block: bool
    signature: bool
    thoughts_tokens: int | None
    reasoning_tokens: int | None


def observe_response(payload):
    """Read native and OpenAI-compatible shapes without storing raw content."""
    empty = Observation(False, False, False, False, False, None, None)
    if not isinstance(payload, dict):
        return empty
    choices = payload.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message")
    elif payload.get("type") == "message":
        message = payload
    elif isinstance(payload.get("candidates"), list) and payload["candidates"] and isinstance(payload["candidates"][0], dict):
        native_content = payload["candidates"][0].get("content")
        if not isinstance(native_content, dict) or not isinstance(native_content.get("parts"), list):
            return empty
        parts = native_content["parts"]
        if any(not isinstance(part, dict) for part in parts):
            return empty
        message = {"content": [
            {"type": "thinking" if part.get("thought") is True else "text",
             "thinking" if part.get("thought") is True else "text": part.get("text")}
            for part in parts
        ]}
    else:
        return empty
    if not isinstance(message, dict):
        return empty
    content = message.get("content")
    blocks = content if isinstance(content, list) else []
    if any(not isinstance(block, dict) for block in blocks):
        return empty
    thinking = [block for block in blocks if block.get("type") == "thinking"]
    answer = bool(content.strip()) if isinstance(content, str) else any(
        block.get("type") == "text" and isinstance(block.get("text"), str)
        and bool(block["text"].strip()) for block in blocks)
    reasoning = message.get("reasoning_content")
    if reasoning is not None and not isinstance(reasoning, str):
        return empty
    usage = payload.get("usage") or {}
    metadata = payload.get("usageMetadata") or {}
    if not isinstance(usage, dict) or not isinstance(metadata, dict):
        return empty
    details = usage.get("completion_tokens_details") or {}
    if not isinstance(details, dict):
        return empty
    counts = (metadata.get("thoughtsTokenCount"), details.get("reasoning_tokens"))
    if any(count is not None and (type(count) is not int or count < 0) for count in counts):
        return empty
    return Observation(True, answer, bool(reasoning and reasoning.strip()), bool(thinking),
                       any(isinstance(block.get("signature"), str) and
                           bool(block["signature"]) for block in thinking), *counts)


def contrast(model, enabled, disabled, *, sdk_parsed):
    """A conservative, protocol-level gate; unknown fields remain unconfirmed."""
    field_for(model)
    if not sdk_parsed or not all(o.valid and o.final_answer for o in (enabled, disabled)):
        return "unconfirmed"
    if (disabled.reasoning_tokens is not None and disabled.reasoning_tokens > 0 or
            disabled.thoughts_tokens is not None and disabled.thoughts_tokens > 0):
        return "unconfirmed"
    if model in MANUAL | ADAPTIVE:
        return "verified" if (enabled.thinking_block and enabled.signature and
                              not disabled.thinking_block and not disabled.reasoning_content) else "unconfirmed"
    if model == "GLM-5":
        return "verified" if enabled.reasoning_content and not disabled.reasoning_content else "unconfirmed"
    if model in GEMINI and enabled.thoughts_tokens is not None and disabled.thoughts_tokens is not None:
        on, off = enabled.thoughts_tokens, disabled.thoughts_tokens
    else:
        on, off = enabled.reasoning_tokens, disabled.reasoning_tokens
    return "verified" if on is not None and on > 0 and off == 0 else "unconfirmed"
