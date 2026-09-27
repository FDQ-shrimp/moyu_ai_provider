"""Document why GLM-5.2 cannot be live-probed through today's public path."""
from copy import deepcopy
from pathlib import Path

from dify_plugin.entities.model import AIModelEntity
from dify_plugin.entities.model.message import UserPromptMessage
from pydantic import ValidationError
import pytest
import yaml

from models.llm.llm import MoyuLargeLanguageModel
from tests.test_llm_sdk_contract import KEY, completion, response, transport


ROOT = Path(__file__).resolve().parents[1]
MODEL = "glm-5.2"


class RawSdkAdapter(MoyuLargeLanguageModel):
    @classmethod
    def _thinking_parameters(cls, model, model_parameters):
        # Isolate the original SDK behavior; production blocks hidden fields.
        return dict(model_parameters)


def schema():
    return yaml.safe_load((ROOT / "models/llm/glm-5.2.yaml").read_text("utf-8"))


def invoke(adapter, parameters):
    list(adapter.invoke(
        model=MODEL, credentials={"api_key": KEY, "endpoint_url": "https://www.moyu.cn/v1"},
        prompt_messages=[UserPromptMessage(content="Fixed short prompt")],
        model_parameters=parameters, tools=None, stream=False,
    ))


def test_sdk_schema_has_no_object_parameter_type():
    data = schema()
    data["parameter_rules"].append({"name": "thinking", "type": "object",
                                    "label": {"en_US": "Thinking"}})
    with pytest.raises(ValidationError):
        AIModelEntity.model_validate(data)


def test_public_sdk_filters_undeclared_thinking_object(transport):
    pending, sent = transport
    pending.append(response(completion(tool_call=False, content="offline-ok")))
    invoke(RawSdkAdapter([AIModelEntity.model_validate(schema())]),
           {"max_tokens": 128, "thinking": {"type": "disabled"}})
    assert len(sent) == 1
    assert "thinking" not in sent[0]["json"]


def test_string_ui_parameter_is_not_automatically_nested(transport):
    pending, sent = transport
    pending.append(response(completion(tool_call=False, content="offline-ok")))
    data = deepcopy(schema())
    data["parameter_rules"] = [rule for rule in data["parameter_rules"]
                               if rule["name"] != "thinking_mode"]
    data["parameter_rules"].append({"name": "thinking_mode", "type": "string",
                                    "options": ["enabled", "disabled"],
                                    "label": {"en_US": "Thinking mode"}})
    invoke(RawSdkAdapter([AIModelEntity.model_validate(data)]),
           {"max_tokens": 128, "thinking_mode": "disabled"})
    assert len(sent) == 1
    assert sent[0]["json"]["thinking_mode"] == "disabled"
    assert "thinking" not in sent[0]["json"]
