"""Test-only GLM-5.2 enum-to-object mapping through Moyu + SDK 0.9.0.

The subclass and schema below exist only in this test module. They are a
candidate for review, not a change to the production adapter or model YAML.
Only the HTTP transport boundary is mocked.
"""
from copy import deepcopy
import json
from pathlib import Path

from dify_plugin.entities.model import AIModelEntity
from dify_plugin.entities.model.message import (
    AssistantPromptMessage, ToolPromptMessage, UserPromptMessage,
)
import pytest
import yaml

from models.llm.llm import MoyuLargeLanguageModel
from tests.test_llm_sdk_contract import (
    CALL, KEY, USAGE, assert_call, calls_from, completion, response,
    sse_response, tool, transport,
)


ROOT = Path(__file__).resolve().parents[1]
MODEL = "glm-5.2"
SITES = ("https://www.moyu.cn/v1", "https://www.konjac.ai/v1")
RULE = {"name": "thinking_mode", "type": "string", "required": False,
        "options": ["enabled", "disabled"],
        "label": {"en_US": "Thinking mode (test only)"}}


def map_glm_parameters(model, original):
    """Pure mapping; a collision is an error, never an overwrite."""
    mapped = deepcopy(original)
    if model != MODEL or "thinking_mode" not in mapped:
        return mapped
    setting = mapped.pop("thinking_mode")
    if setting not in ("enabled", "disabled") or not isinstance(setting, str):
        raise ValueError("invalid_glm_thinking_mode")
    if "thinking" in mapped:
        raise ValueError("conflicting_glm_thinking_parameter")
    mapped["thinking"] = {"type": setting}
    return mapped


class CandidateMoyuAdapter(MoyuLargeLanguageModel):
    """Test-only subclass; all normal transport/parsing stays in production code."""

    @classmethod
    def _thinking_parameters(cls, model, model_parameters):
        # The production guard intentionally rejects hidden candidate fields.
        # This legacy test-only mapper exercises the SDK with an in-memory rule.
        return dict(model_parameters)

    def invoke(self, model, credentials, prompt_messages, model_parameters=None,
               tools=None, stop=None, stream=True, user=None):
        # SDK 0.9.0 filters undeclared object fields before _invoke. Reject an
        # explicit collision here so it cannot be silently lost by that filter.
        if (model == MODEL and model_parameters is not None
                and "thinking_mode" in model_parameters
                and "thinking" in model_parameters):
            raise ValueError("conflicting_glm_thinking_parameter")
        yield from super().invoke(
            model=model, credentials=credentials, prompt_messages=prompt_messages,
            model_parameters=model_parameters, tools=tools, stop=stop,
            stream=stream, user=user,
        )

    def _invoke(self, model, credentials, prompt_messages, model_parameters,
                tools=None, stop=None, stream=True, user=None):
        return super()._invoke(
            model, credentials, prompt_messages,
            map_glm_parameters(model, model_parameters),
            tools, stop, stream, user,
        )


def make_adapter(model=MODEL):
    data = yaml.safe_load((ROOT / "models/llm" / f"{model}.yaml").read_text("utf-8"))
    if model == MODEL:
        data["parameter_rules"] = [rule for rule in data["parameter_rules"]
                                   if rule["name"] != "thinking_mode"]
        data["parameter_rules"].append(deepcopy(RULE))
    return CandidateMoyuAdapter([AIModelEntity.model_validate(data)])


def call(adapter, model, site, parameters, *, stream=False, tools=None, messages=None):
    credentials = {"api_key": KEY, "endpoint_url": site}
    before = deepcopy((credentials, parameters))
    chunks = list(adapter.invoke(
        model=model, credentials=credentials,
        prompt_messages=messages or [UserPromptMessage(content="Use add for 2 + 3.")],
        model_parameters=parameters, tools=tools, stop=["END"],
        stream=stream, user="offline-glm-mapping",
    ))
    assert (credentials, parameters) == before
    return chunks


def final_sse():
    result = response({})
    result.headers["Content-Type"] = "text/event-stream"
    events = [
        {"id": "offline-final", "model": MODEL, "choices": [{
            "index": 0, "delta": {"content": "5"}, "finish_reason": None}]},
        {"id": "offline-final", "model": MODEL, "choices": [{
            "index": 0, "delta": {}, "finish_reason": "stop"}],
         "usage": dict(USAGE)},
    ]
    result._content = ("".join("data: " + json.dumps(event) + "\n\n" for event in events)
                       + "data: [DONE]\n\n").encode("utf-8")
    return result


def assert_common(body, setting, stream):
    assert body["model"] == MODEL and body["stream"] is stream
    assert body["thinking"] == {"type": setting}
    assert "thinking_mode" not in body
    assert body["temperature"] == 0.6 and body["top_p"] == 0.8
    assert body["max_tokens"] == 128
    assert body["stop"] == ["END"] and body["user"] == "offline-glm-mapping"


@pytest.mark.parametrize("site", SITES)
@pytest.mark.parametrize("setting", ("enabled", "disabled"))
@pytest.mark.parametrize("stream", (False, True))
def test_chat_constructs_exact_object_with_real_sdk(transport, site, setting, stream):
    pending, sent = transport
    pending.append(sse_response(tool_call=False) if stream else
                   response(completion(tool_call=False, content="hello")))
    params = {"temperature": 0.6, "top_p": 0.8,
              "max_tokens": 128, "thinking_mode": setting}
    chunks = call(make_adapter(), MODEL, site, params, stream=stream)
    assert "".join(c.delta.message.content or "" for c in chunks) == "hello"
    assert len(sent) == 1 and sent[0]["url"] == site + "/chat/completions"
    assert_common(sent[0]["json"], setting, stream)
    assert not {"tools", "tool_choice"} & sent[0]["json"].keys()


@pytest.mark.parametrize("site", SITES)
@pytest.mark.parametrize("setting", ("enabled", "disabled"))
@pytest.mark.parametrize("stream", (False, True))
def test_function_calling_roundtrip_preserves_object_and_tool_history(
    transport, tool, site, setting, stream,
):
    pending, sent = transport
    adapter = make_adapter()
    params = {"temperature": 0.6, "top_p": 0.8,
              "max_tokens": 128, "thinking_mode": setting}
    pending.append(sse_response() if stream else response(completion()))
    first = call(adapter, MODEL, site, params, stream=stream, tools=[tool])
    parsed = calls_from(first)
    assert len(parsed) == 1
    assert_call(parsed[0])
    args = json.loads(parsed[0].function.arguments)
    local_result = args["a"] + args["b"]
    assert local_result == 5
    pending.append(final_sse() if stream else response(completion(tool_call=False, content="5")))
    messages = [UserPromptMessage(content="Use add for 2 + 3."),
                AssistantPromptMessage(content="".join(c.delta.message.content or "" for c in first),
                                       tool_calls=parsed),
                ToolPromptMessage(content=str(local_result), tool_call_id=parsed[0].id)]
    final = call(adapter, MODEL, site, params, stream=stream, messages=messages)
    assert "".join(c.delta.message.content or "" for c in final) == "5"
    assert len(sent) == 2
    for request in sent:
        assert request["url"] == site + "/chat/completions"
        assert_common(request["json"], setting, stream)
    assert sent[0]["json"]["tool_choice"] == "auto"
    assert sent[0]["json"]["tools"][0]["function"]["name"] == "add"
    assert sent[1]["json"]["messages"][-2]["tool_calls"] == [CALL]
    assert sent[1]["json"]["messages"][-1] == {
        "role": "tool", "content": "5", "tool_call_id": parsed[0].id,
    }
    assert not {"tools", "tool_choice"} & sent[1]["json"].keys()


def test_absent_setting_keeps_upstream_default(transport):
    pending, sent = transport
    pending.append(response(completion(tool_call=False, content="hello")))
    call(make_adapter(), MODEL, SITES[0], {"max_tokens": 128})
    assert "thinking" not in sent[0]["json"]
    assert "thinking_mode" not in sent[0]["json"]


@pytest.mark.parametrize("invalid", ("auto", "ENABLED", "", 0, True))
def test_invalid_enum_is_rejected_before_http(transport, invalid):
    with pytest.raises(ValueError):
        call(make_adapter(), MODEL, SITES[0],
             {"max_tokens": 128, "thinking_mode": invalid})
    assert transport[1] == []


def test_mapping_rejects_collision_without_mutating_original():
    original = {"thinking_mode": "enabled", "thinking": {"type": "disabled"},
                "max_tokens": 128}
    before = deepcopy(original)
    with pytest.raises(ValueError, match="conflicting_glm_thinking_parameter"):
        map_glm_parameters(MODEL, original)
    assert original == before


def test_public_entry_rejects_collision_before_sdk_filter(transport):
    original = {"thinking_mode": "enabled", "thinking": {"type": "disabled"},
                "max_tokens": 128}
    before = deepcopy(original)
    with pytest.raises(ValueError, match="conflicting_glm_thinking_parameter"):
        call(make_adapter(), MODEL, SITES[0], original)
    assert original == before
    assert transport[1] == []


def test_other_model_does_not_gain_thinking_parameter(transport):
    pending, sent = transport
    pending.append(response(completion(tool_call=False, content="hello")))
    call(make_adapter("kimi-k3"), "kimi-k3", SITES[0],
         {"max_tokens": 128, "thinking_mode": "enabled"})
    assert "thinking" not in sent[0]["json"]
    assert "thinking_mode" not in sent[0]["json"]
