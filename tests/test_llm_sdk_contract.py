"""Real SDK 0.9.0 contracts: mock HTTP transport, never _invoke/_generate.

The model and tool below exist only in tests. No production capability is
inferred from these synthetic responses.
"""

from __future__ import annotations

from collections.abc import Generator
from copy import deepcopy
from importlib.metadata import version
import json
from pathlib import Path
import socket

import dify_plugin
from dify_plugin import OAICompatLargeLanguageModel
from dify_plugin.entities.model import AIModelEntity
from dify_plugin.entities.model.message import (
    AssistantPromptMessage, PromptMessageTool, ToolPromptMessage, UserPromptMessage,
)
import pytest
import requests

from models.llm.llm import MoyuLargeLanguageModel

MODEL = "offline-tool-model"
KEY = "offline-fake-credential"
CALL = {
    "id": "call_add_1", "type": "function",
    "function": {"name": "add", "arguments": '{"a":2,"b":3}'},
}
USAGE = {"prompt_tokens": 12, "completion_tokens": 8, "total_tokens": 20}


@pytest.fixture
def schema():
    return AIModelEntity.model_validate({
        "model": MODEL, "label": {"en_US": MODEL}, "model_type": "llm",
        "model_properties": {"mode": "chat", "context_size": 4096},
        "features": ["tool-call"],
        "parameter_rules": [
            {"name": name, "use_template": name}
            for name in ("temperature", "top_p", "max_tokens")
        ],
    })


@pytest.fixture
def adapter(schema):
    return MoyuLargeLanguageModel([schema])


@pytest.fixture
def tool():
    return PromptMessageTool(
        name="add", description="Add two integers without any external service.",
        parameters={"type": "object", "properties": {
            "a": {"type": "integer"}, "b": {"type": "integer"},
        }, "required": ["a", "b"]},
    )


def completion(*, tool_call=True, content=None, omit_content=False):
    message = {"role": "assistant"}
    if not omit_content:
        message["content"] = content
    if tool_call:
        message["tool_calls"] = [deepcopy(CALL)]
    return {"id": "offline-completion", "object": "chat.completion",
            "model": MODEL, "choices": [{"index": 0, "message": message,
            "finish_reason": "tool_calls" if tool_call else "stop"}],
            "usage": dict(USAGE)}


def response(payload):
    result = requests.Response()
    result.status_code = 200
    result.encoding = "utf-8"
    result._content = json.dumps(payload).encode("utf-8")
    result._content_consumed = True
    return result


def sse_response(*, tool_call=True):
    if tool_call:
        deltas = [
            {"role": "assistant", "content": None, "tool_calls": [{
                "index": 0, "id": CALL["id"], "type": "function",
                "function": {"name": "add", "arguments": ""},
            }]},
            {"tool_calls": [{"index": 0, "function": {"arguments": '{"a":'}}]},
            {"tool_calls": [{"index": 0, "function": {"arguments": '2,"b":3}'}}]},
        ]
    else:
        deltas = [{"role": "assistant", "content": "hel"}, {"content": "lo"}]
    chunks = [{"id": "offline-stream", "model": MODEL, "choices": [
        {"index": 0, "delta": delta, "finish_reason": None}
    ]} for delta in deltas]
    chunks.append({"id": "offline-stream", "model": MODEL, "choices": [
        {"index": 0, "delta": {}, "finish_reason": "tool_calls" if tool_call else "stop"}
    ], "usage": dict(USAGE)})
    result = response({})
    result.headers["Content-Type"] = "text/event-stream"
    result._content = ("".join("data: " + json.dumps(c) + "\n\n" for c in chunks)
                       + "data: [DONE]\n\n").encode("utf-8")
    return result


@pytest.fixture
def transport(monkeypatch):
    pending, captured = [], []

    def post(url, **kwargs):
        captured.append({"url": url, **deepcopy(kwargs)})
        assert pending, "Unexpected extra HTTP request"
        return pending.pop(0)

    monkeypatch.setattr(requests, "post", post)
    yield pending, captured
    assert not pending, "A queued HTTP response was never consumed"


def invoke(model, *, credentials=None, messages=None, tools=None, stream=False,
           parameters=None, stop=None, user=None):
    with model.timing_context():
        result = model._invoke(
            MODEL, {"api_key": KEY} if credentials is None else credentials,
            [UserPromptMessage(content="Use add for 2 + 3.")] if messages is None else messages,
            {} if parameters is None else parameters, tools, stop, stream, user,
        )
        # Exercise the parser, not merely construction of a lazy generator.
        return list(result) if isinstance(result, Generator) else result


def calls_from(result):
    if isinstance(result, list):
        return [call for chunk in result for call in chunk.delta.message.tool_calls]
    return result.message.tool_calls


def assert_call(call):
    assert call.id == CALL["id"]
    assert call.type == "function"
    assert call.function.name == "add"
    assert call.function.arguments == CALL["function"]["arguments"]
    assert json.loads(call.function.arguments) == {"a": 2, "b": 3}


def test_real_sdk_is_used():
    assert version("dify_plugin") == "0.9.0"
    assert Path(dify_plugin.__file__).is_file()
    assert callable(OAICompatLargeLanguageModel._generate)


@pytest.mark.parametrize("existing", [None, "no_call", "tool_call"])
def test_protocol_in_credentials_copy(existing):
    original = {"api_key": "  " + KEY + "  "}
    if existing is not None:
        original["function_calling_type"] = existing
    before = deepcopy(original)
    patched = MoyuLargeLanguageModel._patched_credentials(original)
    assert original == before
    assert patched is not original
    assert patched["api_key"] == KEY
    assert patched["function_calling_type"] == "tool_call"


@pytest.mark.parametrize("endpoint, expected", [
    (None, "https://www.moyu.cn/v1/chat/completions"),
    (" https://www.konjac.ai/v1/ ", "https://www.konjac.ai/v1/chat/completions"),
])
def test_tools_and_original_parameters_reach_http(adapter, tool, transport, endpoint, expected):
    pending, sent = transport
    pending.append(response(completion()))
    credentials = {"api_key": " " + KEY + " "}
    if endpoint is not None:
        credentials["endpoint_url"] = endpoint
    before = deepcopy(credentials)
    invoke(adapter, credentials=credentials, tools=[tool],
           parameters={"temperature": 0.2, "top_p": 0.9, "max_tokens": 32,
                       "tool_choice": "required"}, stop=["END"], user="offline-user")
    request = sent[0]
    assert request["url"] == expected
    assert request["headers"]["Authorization"] == "Bearer " + KEY
    assert request["stream"] is False
    assert request["json"] == {
        "model": MODEL, "stream": False, "temperature": 0.2, "top_p": 0.9,
        "max_tokens": 32, "tool_choice": "auto", "stop": ["END"], "user": "offline-user",
        "messages": [{"role": "user", "content": "Use add for 2 + 3."}],
        "tools": [{"type": "function", "function": tool.model_dump()}],
    }
    assert credentials == before


def test_nonstream_tool_call_with_null_content(adapter, tool, transport):
    transport[0].append(response(completion(content=None)))
    result = invoke(adapter, tools=[tool])
    assert result.message.content is None
    assert len(calls_from(result)) == 1
    assert_call(calls_from(result)[0])
    assert result.usage.total_tokens == 20


def test_nonstream_tool_call_without_content(adapter, tool, transport):
    upstream = response(completion(omit_content=True))
    original_bytes = upstream.content
    transport[0].append(upstream)
    result = invoke(adapter, tools=[tool])
    assert result.message.content == ""
    assert len(calls_from(result)) == 1
    assert_call(calls_from(result)[0])
    assert upstream.content == original_bytes


def test_stream_tool_fragments_are_consumed_and_reassembled(adapter, tool, transport):
    transport[0].append(sse_response())
    chunks = invoke(adapter, tools=[tool], stream=True)
    assert len(calls_from(chunks)) == 1
    assert_call(calls_from(chunks)[0])
    assert chunks[-1].delta.finish_reason == "tool_calls"
    assert chunks[-1].delta.usage.total_tokens == 20
    assert transport[1][0]["stream"] is True
    assert transport[1][0]["json"]["stream"] is True
    assert transport[1][0]["json"]["tools"][0]["function"]["name"] == "add"


@pytest.mark.parametrize("next_tools", [None, []], ids=["none", "empty"])
def test_tool_result_roundtrip_without_new_tools(adapter, tool, transport, next_tools):
    pending, sent = transport
    pending.append(response(completion()))
    first = invoke(adapter, tools=[tool])
    assert len(first.message.tool_calls) == 1
    tool_call_id = first.message.tool_calls[0].id
    pending.append(response(completion(tool_call=False, content="5")))
    messages = [UserPromptMessage(content="Add 2 and 3."), first.message,
                ToolPromptMessage(content="5", tool_call_id=tool_call_id)]
    final = invoke(adapter, messages=messages, tools=next_tools)
    assert final.message.content == "5"
    assert not final.message.tool_calls
    assert sent[1]["json"]["messages"][1]["tool_calls"] == [CALL]
    assert sent[1]["json"]["messages"][2] == {
        "role": "tool", "content": "5", "tool_call_id": tool_call_id,
    }
    assert "tools" not in sent[1]["json"]
    assert "tool_choice" not in sent[1]["json"]


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("tools", [None, []], ids=["none", "empty"])
def test_chat_regression_without_tools(adapter, transport, stream, tools):
    transport[0].append(sse_response(tool_call=False) if stream else
                        response(completion(tool_call=False, content="hello")))
    result = invoke(adapter, tools=tools, stream=stream)
    content = ("".join(c.delta.message.content or "" for c in result)
               if stream else result.message.content)
    assert content == "hello"
    assert not calls_from(result)
    body = transport[1][0]["json"]
    assert not {"tools", "functions", "tool_choice", "stop", "user"} & body.keys()
    assert body["stream"] is stream


@pytest.mark.parametrize("mode", [None, "no_call", "tool_call"], ids=["default", "no_call", "tool_call"])
@pytest.mark.parametrize("stream", [False, True])
def test_unmodified_sdk_protocol_control(schema, tool, transport, mode, stream):
    sdk = OAICompatLargeLanguageModel([schema])
    credentials = {"api_key": KEY, "mode": "chat", "endpoint_url": "https://offline.invalid/v1"}
    if mode is not None:
        credentials["function_calling_type"] = mode
    transport[0].append(sse_response() if stream else response(completion()))
    messages = [UserPromptMessage(content="Add."),
                AssistantPromptMessage(content=None, tool_calls=[CALL]),
                ToolPromptMessage(content="5", tool_call_id=CALL["id"])]
    result = invoke(sdk, credentials=credentials, messages=messages, tools=[tool], stream=stream)
    body = transport[1][0]["json"]
    if mode == "tool_call":
        assert body["tools"][0]["function"]["name"] == "add"
        assert body["tool_choice"] == "auto"
        assert body["messages"][1]["tool_calls"] == [CALL]
        assert body["messages"][2]["tool_call_id"] == CALL["id"]
        assert len(calls_from(result)) == 1
        assert_call(calls_from(result)[0])
    else:
        assert not {"tools", "functions", "tool_choice"} & body.keys()
        assert "tool_calls" not in body["messages"][1]
        assert body["messages"][2] == {}
        assert not calls_from(result)


def test_base_sdk_missing_content_limitation_is_reproducible(schema, tool, transport):
    transport[0].append(response(completion(omit_content=True)))
    with pytest.raises(KeyError, match="content"):
        invoke(OAICompatLargeLanguageModel([schema]), tools=[tool], credentials={
            "api_key": KEY, "endpoint_url": "https://offline.invalid/v1", "mode": "chat",
            "function_calling_type": "tool_call",
        })


def test_malformed_chat_is_not_silently_accepted(adapter, transport):
    transport[0].append(response(completion(tool_call=False, omit_content=True)))
    with pytest.raises(KeyError, match="content"):
        invoke(adapter)


def test_public_sdk_invoke_entrypoint(adapter, tool, transport):
    transport[0].append(response(completion()))
    chunks = list(adapter.invoke(
        model=MODEL, credentials={"api_key": KEY},
        prompt_messages=[UserPromptMessage(content="Add 2 and 3.")],
        model_parameters={"temperature": 0.2, "max_tokens": 32},
        tools=[tool], stream=False,
    ))
    assert len(calls_from(chunks)) == 1
    assert_call(calls_from(chunks)[0])


def test_real_http_is_blocked():
    with pytest.raises(RuntimeError, match="forbid"):
        requests.get("https://offline.invalid/")


def test_real_socket_is_blocked():
    with socket.socket() as client:
        with pytest.raises(RuntimeError, match="forbid"):
            client.connect(("127.0.0.1", 1))


def test_dotenv_open_is_blocked_before_filesystem_access(tmp_path):
    # The file does not exist: the guard must reject before any filesystem read.
    with pytest.raises(RuntimeError, match="dotenv"):
        (tmp_path / "never-created" / ".env").read_text()
