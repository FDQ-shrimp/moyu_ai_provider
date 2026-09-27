"""Site-scoped public Thinking Control contracts through SDK 0.9.0, offline."""

from copy import deepcopy
import json
from pathlib import Path

from dify_plugin.entities.model import AIModelEntity
from dify_plugin.entities.model.message import (
    AssistantPromptMessage, ToolPromptMessage, UserPromptMessage,
)
import pytest
import yaml

from models.llm.llm import MoyuLargeLanguageModel as Adapter
from tests.test_llm_sdk_contract import (
    KEY, USAGE, CALL, assert_call, calls_from, completion, response,
    sse_response, tool, transport,
)

ROOT = Path(__file__).resolve().parents[1]
CHINA = Adapter.BASE_URL
OVERSEAS = Adapter.OVERSEAS_URL
CASES = (
    ("deepseek-v4-flash", CHINA, "thinking_mode", "开启", {"thinking": {"type": "enabled"}}),
    ("deepseek-v4-flash", CHINA, "thinking_mode", "关闭", {"thinking": {"type": "disabled"}}),
    ("deepseek-v4-pro", CHINA, "thinking_mode", "开启", {"thinking": {"type": "enabled"}}),
    ("deepseek-v4-pro", OVERSEAS, "thinking_mode", "关闭", {"thinking": {"type": "disabled"}}),
    ("gpt-5.5", OVERSEAS, "reasoning_effort", "low", {"reasoning_effort": "low"}),
    ("gpt-5.5", OVERSEAS, "reasoning_effort", "none", {"reasoning_effort": "none"}),
    ("gpt-5.6-luna", OVERSEAS, "reasoning_effort", "low", {"reasoning_effort": "low"}),
    ("gpt-5.6-luna", OVERSEAS, "reasoning_effort", "none", {"reasoning_effort": "none"}),
)


def adapter(model):
    data = yaml.safe_load((ROOT / "models/llm" / f"{model}.yaml").read_text("utf-8"))
    return Adapter([AIModelEntity.model_validate(data)])


def run(model, site, parameters, *, stream=False, tools=None, messages=None):
    credentials = {"api_key": KEY, "endpoint_url": site}
    original = deepcopy((credentials, parameters))
    result = list(adapter(model).invoke(
        model=model, credentials=credentials, model_parameters=parameters,
        prompt_messages=messages or [UserPromptMessage(content="Use add for 2 + 3.")],
        tools=tools, stream=stream, stop=["END"], user="offline-site-thinking",
    ))
    assert (credentials, parameters) == original
    return result


@pytest.mark.parametrize("model,site,field,choice,expected", CASES)
@pytest.mark.parametrize("stream", (False, True))
def test_public_chat_control_reaches_exact_site(transport, model, site, field, choice, expected, stream):
    pending, sent = transport
    pending.append(sse_response(tool_call=False) if stream else
                   response(completion(tool_call=False, content="hello")))
    parameters = {"temperature": 0.6, "top_p": 0.8, "max_tokens": 128,
                  field: choice}
    chunks = run(model, site, parameters, stream=stream)
    assert "".join(c.delta.message.content or "" for c in chunks) == "hello"
    assert len(sent) == 1 and sent[0]["url"] == site + "/chat/completions"
    body = sent[0]["json"]
    assert all(body[key] == value for key, value in expected.items())
    assert field not in body or field == "reasoning_effort"
    assert body["temperature"] == 0.6 and body["top_p"] == 0.8
    assert body["max_tokens"] == 128 and body["stop"] == ["END"]
    assert body["stream"] is stream and body["model"] == model


@pytest.mark.parametrize("model,site,field,choice,expected", CASES)
@pytest.mark.parametrize("stream", (False, True))
def test_public_tool_roundtrip_keeps_control(transport, tool, model, site,
                                             field, choice, expected, stream):
    pending, sent = transport
    pending.append(sse_response() if stream else response(completion()))
    params = {"temperature": 0.6, "top_p": 0.8, "max_tokens": 128, field: choice}
    first = run(model, site, params, stream=stream, tools=[tool])
    parsed = calls_from(first)
    assert len(parsed) == 1
    assert_call(parsed[0])
    assert json.loads(parsed[0].function.arguments) == {"a": 2, "b": 3}
    final = response(completion(tool_call=False, content="5"))
    if stream:
        final.headers["Content-Type"] = "text/event-stream"
        events = [
            {"id": "offline-final", "model": model, "choices": [{
                "index": 0, "delta": {"content": "5"}, "finish_reason": None}]},
            {"id": "offline-final", "model": model, "choices": [{
                "index": 0, "delta": {}, "finish_reason": "stop"}],
             "usage": dict(USAGE)},
        ]
        final._content = ("".join("data: " + json.dumps(e) + "\n\n" for e in events)
                          + "data: [DONE]\n\n").encode()
    pending.append(final)
    history = [
        UserPromptMessage(content="Use add for 2 + 3."),
        AssistantPromptMessage(content="".join(c.delta.message.content or "" for c in first),
                               tool_calls=parsed),
        ToolPromptMessage(content="5", tool_call_id=parsed[0].id),
    ]
    second = run(model, site, params, stream=stream, messages=history)
    assert "".join(c.delta.message.content or "" for c in second) == "5"
    assert len(sent) == 2
    for request in sent:
        assert all(request["json"][key] == value for key, value in expected.items())
    assert sent[0]["json"]["tools"][0]["function"]["name"] == "add"
    assert sent[1]["json"]["messages"][1]["tool_calls"] == [CALL]


@pytest.mark.parametrize("model,wrong_site", [
    ("deepseek-v4-flash", OVERSEAS),
    ("gpt-5.5", CHINA), ("gpt-5.6-luna", CHINA),
])
def test_unverified_site_hides_and_rejects_control(model, wrong_site):
    instance = adapter(model)
    rules = instance.get_model_schema(model, {"api_key": KEY,
                                               "endpoint_url": wrong_site}).parameter_rules
    assert not {"thinking_mode", "reasoning_effort"} & {rule.name for rule in rules}
    with pytest.raises(ValueError, match="unverified_site_thinking_control"):
        instance._invoke(model, {"api_key": KEY, "endpoint_url": wrong_site},
                         [UserPromptMessage(content="hello")],
                         {"reasoning_effort": "low"} if model.startswith("gpt-") else
                         {"thinking_mode": "开启"}, stream=False)


def test_defaults_invalid_values_and_pure_mapping():
    assert Adapter._thinking_parameters("deepseek-v4-pro", {}) == {
        "thinking": {"type": "enabled"}}
    assert Adapter._thinking_parameters("gpt-5.5", {}) == {}
    for model in ("gpt-5.5", "gpt-5.6-luna"):
        with pytest.raises(ValueError, match="unverified_reasoning_effort"):
            Adapter._thinking_parameters(model, {"reasoning_effort": "high"})
    with pytest.raises(ValueError, match="conflicting_thinking_controls"):
        Adapter._thinking_parameters("deepseek-v4-pro", {
            "thinking_mode": "开启", "thinking": {"type": "disabled"}})
