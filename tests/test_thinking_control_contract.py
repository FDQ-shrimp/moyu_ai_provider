"""Production Qwen thinking controls through the real SDK, entirely offline."""

from copy import deepcopy
import json
from pathlib import Path

from dify_plugin.entities.model import AIModelEntity
from dify_plugin.entities.model.message import AssistantPromptMessage, ToolPromptMessage, UserPromptMessage
import pytest
import yaml

from models.llm.llm import MoyuLargeLanguageModel
from tests.test_llm_sdk_contract import (
    CALL, KEY, USAGE, assert_call, calls_from, completion, response, sse_response,
    tool, transport,  # pytest fixtures; transport mocks only requests.post
)

ROOT = Path(__file__).resolve().parents[1]
MODEL = "qwen3.6-27b"
MODELS = (MODEL, "qwen3.6-plus", "qwen3.6-35b-a3b", "qwen3.6-flash",
          "qwen3.7-max", "qwen3.7-plus", "qwen3.8-max")
ENDPOINTS = ["https://www.moyu.cn/v1", "https://www.konjac.ai/v1"]


def make_adapter(model=MODEL):
    data = yaml.safe_load((ROOT / "models/llm" / f"{model}.yaml").read_text("utf-8"))
    return MoyuLargeLanguageModel([AIModelEntity.model_validate(data)])


def invoke_public(adapter, endpoint, setting, *, stream, model=MODEL, tools=None, messages=None,
                  parameter_name="thinking_mode"):
    credentials = {"api_key": KEY, "endpoint_url": endpoint}
    params = {"temperature": 0.6, "top_p": 0.8, "max_tokens": 128}
    if setting is not None:
        params[parameter_name] = setting
    original = deepcopy((credentials, params))
    result = list(adapter.invoke(
        model=model, credentials=credentials, model_parameters=params,
        prompt_messages=messages or [UserPromptMessage(content="Use add for 2 + 3.")],
        tools=tools, stream=stream, stop=["END"], user="offline-thinking-test",
    ))
    assert (credentials, params) == original
    return result


def assert_switch(body, setting, model=MODEL):
    assert body["enable_thinking"] is (setting == "开启")
    assert "thinking_mode" not in body
    assert "extra_body" not in body
    assert "chat_template_kwargs" not in body
    assert body["model"] == model
    assert body["temperature"] == 0.6
    assert body["top_p"] == 0.8
    assert body["max_tokens"] == 128
    assert body["stop"] == ["END"]
    assert body["user"] == "offline-thinking-test"


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize("setting", [None, "开启", "关闭"], ids=["default-off", "on", "off"])
@pytest.mark.parametrize("stream", [False, True])
def test_production_chat_three_states(transport, model, endpoint, setting, stream):
    pending, sent = transport
    pending.append(sse_response(tool_call=False) if stream else
                   response(completion(tool_call=False, content="hello")))
    chunks = invoke_public(make_adapter(model), endpoint, setting, stream=stream, model=model)
    assert "".join(c.delta.message.content or "" for c in chunks) == "hello"
    assert not calls_from(chunks)
    assert len(sent) == 1
    assert sent[0]["url"] == endpoint + "/chat/completions"
    body = sent[0]["json"]
    assert_switch(body, setting, model)
    assert body["stream"] is stream
    assert not {"tools", "tool_choice", "functions"} & body.keys()


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("endpoint", ENDPOINTS)
@pytest.mark.parametrize("setting", [None, "开启", "关闭"], ids=["default-off", "on", "off"])
@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("next_tools", [None, []], ids=["no-tools", "empty-tools"])
def test_production_tool_roundtrip(transport, tool, model, endpoint, setting, stream, next_tools):
    pending, sent = transport
    adapter = make_adapter(model)
    pending.append(sse_response() if stream else response(completion()))
    first = invoke_public(adapter, endpoint, setting, stream=stream, model=model, tools=[tool])
    parsed = calls_from(first)
    assert len(parsed) == 1
    assert_call(parsed[0])
    args = json.loads(parsed[0].function.arguments)
    local_result = args["a"] + args["b"]
    assert local_result == 5
    final_response = response(completion(tool_call=False, content="5"))
    if stream:
        final_response.headers["Content-Type"] = "text/event-stream"
        events = [
            {"id": "offline-final", "model": model, "choices": [{
                "index": 0, "delta": {"content": "5"}, "finish_reason": None}]},
            {"id": "offline-final", "model": model, "choices": [{
                "index": 0, "delta": {}, "finish_reason": "stop"}],
             "usage": dict(USAGE)},
        ]
        final_response._content = ("".join(
            "data: " + json.dumps(event) + "\n\n" for event in events
        ) + "data: [DONE]\n\n").encode("utf-8")
    pending.append(final_response)
    final = invoke_public(adapter, endpoint, setting, stream=stream, model=model, tools=next_tools,
        messages=[UserPromptMessage(content="Use add for 2 + 3."),
                  # The final SSE event may contain only finish/usage. Rebuild
                  # history from all SDK-parsed chunks, not the terminal event.
                  AssistantPromptMessage(
                      content="".join(c.delta.message.content or "" for c in first),
                      tool_calls=parsed),
                  ToolPromptMessage(content=str(local_result), tool_call_id=parsed[0].id)])
    assert "".join(c.delta.message.content or "" for c in final) == "5"
    assert len(sent) == 2
    for request in sent:
        assert request["url"] == endpoint + "/chat/completions"
        assert_switch(request["json"], setting, model)
    assert sent[0]["json"]["tool_choice"] == "auto"
    assert sent[0]["json"]["tools"][0]["function"]["name"] == "add"
    history = sent[1]["json"]["messages"]
    assert history[1]["tool_calls"] == [CALL]
    assert history[2] == {"role": "tool", "content": "5", "tool_call_id": parsed[0].id}
    assert "tools" not in sent[1]["json"]
    assert "tool_choice" not in sent[1]["json"]


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("invalid", ["false", "true", "enabled", "", True, False, 0, 1, {}])
def test_production_rejects_invalid_dropdown_before_transport(transport, model, invalid):
    with pytest.raises(ValueError):
        invoke_public(make_adapter(model), ENDPOINTS[0], invalid, stream=False, model=model)
    assert transport[1] == []


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("legacy", [True, False])
def test_previous_boolean_workflow_values_are_preserved(transport, model, legacy):
    transport[0].append(response(completion(tool_call=False, content="hello")))
    invoke_public(make_adapter(model), ENDPOINTS[0], legacy, stream=False, model=model,
                  parameter_name="enable_thinking")
    assert transport[1][0]["json"]["enable_thinking"] is legacy
    assert "thinking_mode" not in transport[1][0]["json"]


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("setting,legacy", [("关闭", True), ("开启", False)])
def test_new_dropdown_choice_overrides_saved_legacy_value(transport, model, setting, legacy):
    params = {"thinking_mode": setting, "enable_thinking": legacy}
    original = deepcopy(params)
    transport[0].append(response(completion(tool_call=False, content="hello")))
    list(make_adapter(model).invoke(
        model=model, credentials={"api_key": KEY, "endpoint_url": ENDPOINTS[0]},
        prompt_messages=[UserPromptMessage(content="hello")],
        model_parameters=params, stream=False,
    ))
    assert params == original
    assert transport[1][0]["json"]["enable_thinking"] is (setting == "开启")
    assert "thinking_mode" not in transport[1][0]["json"]


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("invalid", ["false", "true", 0, 1, {}])
def test_invalid_legacy_boolean_is_rejected_without_request(transport, model, invalid):
    with pytest.raises(ValueError, match="invalid_legacy_thinking_boolean"):
        invoke_public(make_adapter(model), ENDPOINTS[0], invalid, stream=False, model=model,
                      parameter_name="enable_thinking")
    assert transport[1] == []


@pytest.mark.parametrize("model", ("kimi-k3", "gemini-2.5-flash", "gpt-5.5", "GLM-5"))
def test_other_models_do_not_gain_wire_thinking_default(transport, model):
    transport[0].append(response(completion(tool_call=False, content="hello")))
    invoke_public(make_adapter(model), ENDPOINTS[0], None, stream=False, model=model)
    assert "enable_thinking" not in transport[1][0]["json"]
    assert "thinking_mode" not in transport[1][0]["json"]


def test_only_approved_models_declare_required_dropdown_default_off():
    declared = set()
    for path in (ROOT / "models/llm").glob("*.yaml"):
        data = yaml.safe_load(path.read_text("utf-8"))
        assert not any(rule["name"] == "enable_thinking"
                       for rule in data.get("parameter_rules", []))
        rules = [rule for rule in data.get("parameter_rules", [])
                 if rule["name"] == "thinking_mode"]
        if not rules:
            continue
        declared.add(data["model"])
        assert len(rules) == 1
        rule = rules[0]
        assert rule["type"] == "string" and rule["required"] is True
        assert rule["label"] == {"en_US": "Thinking mode", "zh_Hans": "思考模式"}
        expected_default = ("开启" if data["model"] in
                            MoyuLargeLanguageModel.DEEPSEEK_THINKING_MODELS else "关闭")
        assert rule["default"] == expected_default and rule["options"] == ["关闭", "开启"]
        assert "use_template" not in rule
        public_rule = next(r for r in AIModelEntity.model_validate(data).parameter_rules
                           if r.name == "thinking_mode")
        assert public_rule.default == expected_default and public_rule.required is True
    assert declared == (MoyuLargeLanguageModel.EXPOSED_THINKING_MODELS -
                        MoyuLargeLanguageModel.VERIFIED_EFFORT_THINKING_MODELS)


@pytest.mark.parametrize("model", ("gemini-2.5-flash", "gpt-5.6-sol", "GLM-5"))
def test_blocked_models_do_not_expose_unapproved_reasoning_controls(model):
    data = yaml.safe_load((ROOT / "models/llm" / f"{model}.yaml").read_text("utf-8"))
    assert not {"enable_thinking", "reasoning_effort", "thinking", "thinking_mode"} & {
        r["name"] for r in data["parameter_rules"]
    }
