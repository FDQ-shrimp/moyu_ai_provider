"""China-only thinking UI rules and wire guard with real SDK 0.9.0."""

from copy import deepcopy

from dify_plugin.entities.model.message import UserPromptMessage
import pytest

from models.llm.llm import MoyuLargeLanguageModel
from tests.test_llm_sdk_contract import KEY, completion, response, transport
from tests.test_thinking_control_contract import make_adapter


CHINA = "https://www.moyu.cn/v1"
OVERSEAS = "https://www.konjac.ai/v1"
MODELS = ("qwen-plus", "qwen3-max")


@pytest.mark.parametrize("model", MODELS)
def test_parameter_panel_is_filtered_by_site(model):
    adapter = make_adapter(model)
    domestic = adapter.get_parameter_rules(model, {"api_key": KEY, "endpoint_url": CHINA})
    foreign = adapter.get_parameter_rules(model, {"api_key": KEY, "endpoint_url": OVERSEAS})
    assert [rule.name for rule in domestic if rule.name == "thinking_mode"] == ["thinking_mode"]
    assert not [rule for rule in foreign if rule.name == "thinking_mode"]
    assert [rule.name for rule in domestic if rule.name != "thinking_mode"] == [
        rule.name for rule in foreign
    ]


@pytest.mark.parametrize("model", MODELS)
@pytest.mark.parametrize("setting", (None, "关闭", "开启"))
@pytest.mark.parametrize("stream", (False, True))
def test_domestic_public_switch_reaches_wire(transport, model, setting, stream):
    from tests.test_llm_sdk_contract import sse_response

    pending, sent = transport
    pending.append(sse_response(tool_call=False) if stream else
                   response(completion(tool_call=False, content="hello")))
    adapter = make_adapter(model)
    credentials = {"api_key": KEY, "endpoint_url": CHINA}
    parameters = {"temperature": 0.6, "top_p": 0.8, "max_tokens": 128}
    if setting is not None:
        parameters["thinking_mode"] = setting
    before = deepcopy((credentials, parameters))
    list(adapter.invoke(
        model=model, credentials=credentials,
        prompt_messages=[UserPromptMessage(content="hello")],
        model_parameters=parameters, stream=stream,
    ))
    assert (credentials, parameters) == before
    assert len(sent) == 1 and sent[0]["url"] == CHINA + "/chat/completions"
    body = sent[0]["json"]
    assert body["enable_thinking"] is (setting == "开启")
    assert "thinking_mode" not in body
    assert body["temperature"] == 0.6 and body["top_p"] == 0.8
    assert body["max_tokens"] == 128 and body["stream"] is stream


@pytest.mark.parametrize("model", MODELS)
def test_overseas_public_path_never_injects_domestic_switch(transport, model):
    pending, sent = transport
    pending.append(response(completion(tool_call=False, content="hello")))
    adapter = make_adapter(model)
    list(adapter.invoke(
        model=model, credentials={"api_key": KEY, "endpoint_url": OVERSEAS},
        prompt_messages=[UserPromptMessage(content="hello")],
        model_parameters={"max_tokens": 128, "thinking_mode": "开启"},
        stream=False,
    ))
    assert len(sent) == 1 and sent[0]["url"] == OVERSEAS + "/chat/completions"
    assert "thinking_mode" not in sent[0]["json"]
    assert "enable_thinking" not in sent[0]["json"]


@pytest.mark.parametrize("model", MODELS)
def test_direct_overseas_bypass_is_rejected(model):
    adapter = make_adapter(model)
    with pytest.raises(ValueError, match="domestic_only_thinking_control"):
        adapter._invoke(
            model, {"api_key": KEY, "endpoint_url": OVERSEAS},
            [UserPromptMessage(content="hello")],
            {"thinking_mode": "开启"}, stream=False,
        )
