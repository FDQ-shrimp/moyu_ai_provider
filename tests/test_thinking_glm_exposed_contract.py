"""Approved GLM object switch through public SDK and production adapter."""

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
MODELS = ("glm-5.1", "glm-5.2", "kimi-k2.6")
SITES = ("https://www.moyu.cn/v1", "https://www.konjac.ai/v1")


def adapter_for(model):
    schema = yaml.safe_load((ROOT / "models/llm" / f"{model}.yaml").read_text("utf-8"))
    return MoyuLargeLanguageModel([AIModelEntity.model_validate(schema)])


def final_sse(model):
    result = response({})
    result.headers["Content-Type"] = "text/event-stream"
    events = [
        {"id": "final", "model": model, "choices": [{"index": 0,
            "delta": {"content": "5"}, "finish_reason": None}]},
        {"id": "final", "model": model, "choices": [{"index": 0,
            "delta": {}, "finish_reason": "stop"}], "usage": dict(USAGE)},
    ]
    result._content = ("".join("data: " + json.dumps(event) + "\n\n"
                               for event in events) + "data: [DONE]\n\n").encode()
    return result


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("site", SITES)
@pytest.mark.parametrize("setting", (None, "关闭", "开启"))
@pytest.mark.parametrize("stream", (False, True))
@pytest.mark.parametrize("with_tool", (False, True))
def test_public_glm_chat_and_tool_roundtrip(
    transport, tool, model, site, setting, stream, with_tool,
):
    pending, sent = transport
    adapter = adapter_for(model)
    credentials = {"api_key": KEY, "endpoint_url": site}
    parameters = {"temperature": 0.6, "top_p": 0.8, "max_tokens": 128}
    if setting is not None:
        parameters["thinking_mode"] = setting
    before = deepcopy((credentials, parameters))

    def invoke(messages, tools):
        return list(adapter.invoke(
            model=model, credentials=credentials, prompt_messages=messages,
            model_parameters=parameters, tools=tools, stop=["END"],
            stream=stream, user="offline-glm-public",
        ))

    prompt = UserPromptMessage(content="Use add for 2 + 3.")
    pending.append(sse_response(tool_call=with_tool) if stream else
                   response(completion(tool_call=with_tool,
                                       content=None if with_tool else "hello")))
    first = invoke([prompt], [tool] if with_tool else None)
    if with_tool:
        calls = calls_from(first)
        assert len(calls) == 1
        assert_call(calls[0])
        args = json.loads(calls[0].function.arguments)
        assert args["a"] + args["b"] == 5
        pending.append(final_sse(model) if stream else
                       response(completion(tool_call=False, content="5")))
        final = invoke([
            prompt,
            AssistantPromptMessage(
                content="".join(chunk.delta.message.content or "" for chunk in first),
                tool_calls=calls,
            ),
            ToolPromptMessage(content="5", tool_call_id=calls[0].id),
        ], None)
        assert "".join(chunk.delta.message.content or "" for chunk in final) == "5"
        assert sent[1]["json"]["messages"][-1] == {
            "role": "tool", "content": "5", "tool_call_id": calls[0].id,
        }
    else:
        assert not calls_from(first)
    assert (credentials, parameters) == before
    assert len(sent) == (2 if with_tool else 1)
    for request in sent:
        body = request["json"]
        assert request["url"] == site + "/chat/completions"
        assert body["model"] == model and body["stream"] is stream
        assert body["thinking"] == {"type": "enabled" if setting == "开启" else "disabled"}
        assert "thinking_mode" not in body
        assert body["temperature"] == 0.6 and body["top_p"] == 0.8
        assert body["max_tokens"] == 128 and body["stop"] == ["END"]


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("invalid", ("enabled", "disabled", "auto", True, 0, {}))
def test_public_glm_rejects_invalid_dropdown(transport, model, invalid):
    with pytest.raises(ValueError):
        list(adapter_for(model).invoke(
            model=model, credentials={"api_key": KEY, "endpoint_url": SITES[0]},
            prompt_messages=[UserPromptMessage(content="hello")],
            model_parameters={"thinking_mode": invalid}, stream=False,
        ))
    assert transport[1] == []
