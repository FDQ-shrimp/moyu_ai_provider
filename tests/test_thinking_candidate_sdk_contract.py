"""Real SDK 0.9.0, fake HTTP only: hidden protocol candidates never go live."""

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
    KEY, USAGE, assert_call, calls_from, completion, response, sse_response,
    tool, transport,
)

ROOT = Path(__file__).resolve().parents[1]
SITES = ("https://www.moyu.cn/v1", "https://www.konjac.ai/v1")
CASES = (
    ("qwen3.6-flash", "thinking_mode", "string", "开启",
     {"enable_thinking": True}),
    ("glm-5.2", "thinking_mode", "string", "关闭",
     {"thinking": {"type": "disabled"}}),
    ("gpt-5.6-sol", "reasoning_effort", "string", "low",
     {"reasoning_effort": "low"}),
    ("claude-haiku-4-5-20251001", "thinking_budget", "int", 2048,
     {"thinking": {"type": "enabled", "budget_tokens": 2048}}),
    ("claude-sonnet-5", "reasoning_effort", "string", "medium",
     {"thinking": {"type": "adaptive"}, "output_config": {"effort": "medium"}}),
)


class OfflineCandidateAdapter(MoyuLargeLanguageModel):
    @classmethod
    def _thinking_parameters(cls, model, model_parameters):
        return cls._candidate_thinking_parameters(model, model_parameters)


def adapter_for(model, field, kind):
    schema = yaml.safe_load((ROOT / "models/llm" / f"{model}.yaml").read_text("utf-8"))
    schema["parameter_rules"] = [rule for rule in schema["parameter_rules"]
                                 if rule["name"] != field]
    schema["parameter_rules"].append({
        "name": field, "type": kind, "required": False,
        "label": {"en_US": "Offline candidate only"},
    })
    return OfflineCandidateAdapter([AIModelEntity.model_validate(schema)])


def final_sse(model):
    result = response({})
    result.headers["Content-Type"] = "text/event-stream"
    events = [
        {"id": "final", "model": model, "choices": [{
            "index": 0, "delta": {"content": "5"}, "finish_reason": None}]},
        {"id": "final", "model": model, "choices": [{
            "index": 0, "delta": {}, "finish_reason": "stop"}], "usage": dict(USAGE)},
    ]
    result._content = ("".join("data: " + json.dumps(event) + "\n\n"
                               for event in events) + "data: [DONE]\n\n").encode()
    return result


@pytest.mark.parametrize("model,field,kind,value,expected", CASES)
@pytest.mark.parametrize("site", SITES)
@pytest.mark.parametrize("stream", (False, True))
@pytest.mark.parametrize("with_tool", (False, True))
def test_candidate_chat_and_complete_tool_loop(
    transport, tool, model, field, kind, value, expected, site, stream, with_tool,
):
    pending, sent = transport
    adapter = adapter_for(model, field, kind)
    credentials = {"api_key": KEY, "endpoint_url": site}
    parameters = {"temperature": 0.6, "top_p": 0.8, "max_tokens": 128,
                  field: value}
    original = deepcopy((credentials, parameters))

    def invoke(messages, tools):
        return list(adapter.invoke(
            model=model, credentials=credentials, model_parameters=parameters,
            prompt_messages=messages, tools=tools, stream=stream,
            stop=["END"], user="offline-candidate",
        ))

    prompt = UserPromptMessage(content="Use add for 2 + 3.")
    pending.append(sse_response(tool_call=with_tool) if stream else
                   response(completion(tool_call=with_tool, content=None if with_tool else "hello")))
    first = invoke([prompt], [tool] if with_tool else None)
    if with_tool:
        calls = calls_from(first)
        assert len(calls) == 1
        assert_call(calls[0])
        args = json.loads(calls[0].function.arguments)
        local = args["a"] + args["b"]
        assert local == 5
        pending.append(final_sse(model) if stream else
                       response(completion(tool_call=False, content="5")))
        final = invoke([
            prompt,
            AssistantPromptMessage(
                content="".join(chunk.delta.message.content or "" for chunk in first),
                tool_calls=calls,
            ),
            ToolPromptMessage(content=str(local), tool_call_id=calls[0].id),
        ], None)
        assert "".join(chunk.delta.message.content or "" for chunk in final) == "5"
        assert sent[1]["json"]["messages"][-1] == {
            "role": "tool", "content": "5", "tool_call_id": calls[0].id,
        }
    else:
        assert not calls_from(first)
    assert (credentials, parameters) == original
    assert len(sent) == (2 if with_tool else 1)
    for request in sent:
        body = request["json"]
        assert request["url"] == site + "/chat/completions"
        assert body["stream"] is stream and body["model"] == model
        assert body["temperature"] == 0.6 and body["top_p"] == 0.8
        assert body["max_tokens"] == 128 and body["stop"] == ["END"]
        assert body["user"] == "offline-candidate"
        assert {key: body[key] for key in expected} == expected
        if field != "reasoning_effort":
            assert field not in body
