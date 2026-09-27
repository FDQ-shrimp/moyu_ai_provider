"""No live calls: twelve exact candidates through real SDK 0.9.0 and fake HTTP."""

from copy import deepcopy
import json
from dify_plugin.entities.model.message import AssistantPromptMessage, ToolPromptMessage, UserPromptMessage
import pytest
from scripts.thinking_twelve_offline import (
    ADAPTIVE, GEMINI, GPT, MANUAL, MAX_TOKENS, MODELS,
    candidate_adapter, contrast, field_for, map_candidate, observe_response, values_for,
)
from tests.test_llm_sdk_contract import (
    KEY, USAGE, assert_call, calls_from, completion, response, sse_response,
    tool, transport,
)

SITES = {"GLM-5": ("https://www.moyu.cn/v1",)}
DEFAULT_SITES = ("https://www.konjac.ai/v1",)


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


@pytest.mark.parametrize("model", sorted(MODELS))
@pytest.mark.parametrize("choice_index", (0, 1))
@pytest.mark.parametrize("stream", (False, True))
@pytest.mark.parametrize("with_tool", (False, True))
def test_http_json_and_two_turn_tool_contract(
    transport, tool, model, choice_index, stream, with_tool,
):
    pending, sent = transport
    value = values_for(model)[choice_index]
    field = field_for(model)
    adapter = candidate_adapter(model)
    parameters = {"max_tokens": MAX_TOKENS, field: value}
    if model not in MANUAL | ADAPTIVE:
        parameters.update(temperature=0.6, top_p=0.8)
    elif value == "关闭" and model not in {"claude-opus-4-7", "claude-opus-4-8"}:
        parameters.update(temperature=0.6, top_p=0.8)
    elif value == "开启":
        parameters["top_p"] = 1.0
    credentials = {"api_key": KEY, "endpoint_url": SITES.get(model, DEFAULT_SITES)[0]}
    original = deepcopy((parameters, credentials))

    def invoke(messages, tools):
        return list(adapter.invoke(
            model=model, credentials=credentials, model_parameters=parameters,
            prompt_messages=messages, tools=tools, stream=stream,
            stop=["END"], user="offline-twelve",
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
        assert sent[1]["json"]["messages"][-1]["role"] == "tool"
    else:
        assert not calls_from(first)
    assert (parameters, credentials) == original
    assert len(sent) == (2 if with_tool else 1)
    expected = map_candidate(model, parameters)
    for request in sent:
        body = request["json"]
        assert request["url"] == credentials["endpoint_url"] + "/chat/completions"
        assert body["model"] == model and body["stream"] is stream
        if "temperature" in parameters:
            assert body["temperature"] == parameters["temperature"]
        else:
            assert "temperature" not in body
        if "top_p" in parameters:
            assert body["top_p"] == parameters["top_p"]
        else:
            assert "top_p" not in body
        assert body["max_tokens"] == MAX_TOKENS and body["stop"] == ["END"]
        assert body["user"] == "offline-twelve"
        assert {key: body[key] for key in expected} == expected
        assert field not in body or field == "reasoning_effort"


@pytest.mark.parametrize("model", sorted(MODELS))
def test_pure_unset_conflict_and_invalid(model):
    source = {"temperature": 0.5, "top_p": 0.8, "max_tokens": MAX_TOKENS}
    original = deepcopy(source)
    assert map_candidate(model, source) == source
    assert source == original
    field = field_for(model)
    for invalid in (None, True, "bogus"):
        with pytest.raises(ValueError, match="invalid_candidate_control"):
            map_candidate(model, {**source, field: invalid})
    with pytest.raises(ValueError, match="conflicting_thinking_controls"):
        map_candidate(model, {**source, field: values_for(model)[0],
                              "thinking": {"type": "disabled"}})
    assert source == original
    with pytest.raises(ValueError, match="unknown_exact_candidate"):
        map_candidate("claude-sonnet-5", {field: values_for(model)[0]})


@pytest.mark.parametrize("model", sorted(MANUAL))
def test_manual_budget_is_strictly_below_max(model):
    with pytest.raises(ValueError, match="thinking_budget_must_be_below_max_tokens"):
        map_candidate(model, {"thinking_mode": "开启", "max_tokens": 1024})
    assert map_candidate(model, {"thinking_mode": "开启", "max_tokens": MAX_TOKENS})[
        "thinking"] == {"type": "enabled", "budget_tokens": 1024}


@pytest.mark.parametrize("model", sorted(MANUAL | ADAPTIVE))
def test_claude_sampling_restrictions_are_not_silently_dropped(model):
    with pytest.raises(ValueError, match="claude_.*sampling_forbidden|claude_thinking_temperature_forbidden"):
        map_candidate(model, {"thinking_mode": "开启", "max_tokens": MAX_TOKENS,
                              "temperature": 0.6})
    with pytest.raises(ValueError, match="claude_.*sampling_forbidden|claude_thinking_top_p_out_of_range"):
        map_candidate(model, {"thinking_mode": "开启", "max_tokens": MAX_TOKENS,
                              "top_p": 0.8})


@pytest.mark.parametrize("model", sorted(ADAPTIVE))
def test_adaptive_display_only_when_enabled(model):
    assert map_candidate(model, {"thinking_mode": "开启"}) == {
        "thinking": {"type": "adaptive", "display": "summarized"}}
    assert map_candidate(model, {"thinking_mode": "关闭"}) == {
        "thinking": {"type": "disabled"}}


def payload(message, *, thoughts=None, reasoning=None):
    result = {"choices": [{"message": message}], "usage": {}}
    if thoughts is not None:
        result["usageMetadata"] = {"thoughtsTokenCount": thoughts}
    if reasoning is not None:
        result["usage"]["completion_tokens_details"] = {"reasoning_tokens": reasoning}
    return result


@pytest.mark.parametrize("model", sorted(MODELS))
def test_response_observer_and_contrast(model):
    plain = observe_response(payload({"content": "final"}, thoughts=0, reasoning=0))
    if model in MANUAL | ADAPTIVE:
        on = observe_response(payload({"content": [
            {"type": "thinking", "thinking": "hidden", "signature": "signed"},
            {"type": "text", "text": "final"}]}))
    elif model == "GLM-5":
        on = observe_response(payload({"content": "final", "reasoning_content": "hidden"}))
    elif model in GEMINI:
        on = observe_response(payload({"content": "final"}, thoughts=3))
    else:
        on = observe_response(payload({"content": "final"}, reasoning=3))
    assert contrast(model, on, plain, sdk_parsed=True) == "verified"
    assert contrast(model, on, plain, sdk_parsed=False) == "unconfirmed"
    missing = observe_response(payload({"content": "final"}))
    assert contrast(model, missing, plain, sdk_parsed=True) == "unconfirmed"
    assert contrast(model, on, missing, sdk_parsed=True) == (
        "unconfirmed" if model in GEMINI | GPT else "verified")


@pytest.mark.parametrize("bad", [None, [], {}, {"choices": [{"message": []}]},
                                      payload({"content": "ok"}, reasoning=-1),
                                      payload({"content": "ok", "reasoning_content": []})])
def test_malformed_response_remains_unconfirmed(bad):
    observed = observe_response(bad)
    assert not observed.valid
    assert contrast("GLM-5", observed, observed, sdk_parsed=True) == "unconfirmed"


def test_gemini_compatible_reasoning_fallback_and_claude_signature_required():
    on = observe_response(payload({"content": "final"}, reasoning=4))
    off = observe_response(payload({"content": "final"}, reasoning=0))
    assert contrast("gemini-2.5-flash", on, off, sdk_parsed=True) == "verified"
    mixed = observe_response(payload({"content": "final"}, thoughts=4))
    assert contrast("gemini-2.5-flash", mixed, off, sdk_parsed=True) == "unconfirmed"
    unsigned = observe_response(payload({"content": [
        {"type": "thinking", "thinking": "hidden"}, {"type": "text", "text": "final"}]}))
    assert contrast("claude-opus-4-8", unsigned, off, sdk_parsed=True) == "unconfirmed"


def test_native_claude_content_blocks_are_observed_without_recording_text():
    raw = {"type": "message", "content": [
        {"type": "thinking", "thinking": "private", "signature": "signed"},
        {"type": "text", "text": "final"}]}
    observed = observe_response(raw)
    assert observed.valid and observed.final_answer
    assert observed.thinking_block and observed.signature
    assert "private" not in repr(observed) and "signed" not in repr(observed)


def test_native_gemini_parts_and_thought_usage_are_observed():
    raw = {"candidates": [{"content": {"parts": [
        {"thought": True, "text": "private"}, {"text": "final"}]}}],
        "usageMetadata": {"thoughtsTokenCount": 7}}
    observed = observe_response(raw)
    assert observed.valid and observed.final_answer
    assert observed.thinking_block and observed.thoughts_tokens == 7
    assert "private" not in repr(observed)
