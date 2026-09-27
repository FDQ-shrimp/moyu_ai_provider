"""Offline-only candidate parameter contract for the Phase 2 first gate.

Runs the production Moyu adapter and SDK 0.9.0 public invoke. Only
requests.post is mocked. Undeclared candidates are added in memory only.
"""
from copy import deepcopy
from pathlib import Path

from dify_plugin.entities.model import AIModelEntity
from dify_plugin.entities.model.message import UserPromptMessage
import pytest
import yaml

from models.llm.llm import MoyuLargeLanguageModel
from tests.test_llm_sdk_contract import KEY, completion, response, transport


ROOT = Path(__file__).resolve().parents[1]
SITES = ("https://www.moyu.cn/v1", "https://www.konjac.ai/v1")
CASES = (
    ("qwen3.6-plus", "enable_thinking", "boolean", True, False),
    ("gemini-2.5-flash", "reasoning_effort", "string", "low", "none"),
    ("gpt-5.5", "reasoning_effort", "string", "low", "none"),
)


class OfflineCandidateAdapter(MoyuLargeLanguageModel):
    """Use an in-memory candidate mapping, never the public production path."""

    @classmethod
    def _thinking_parameters(cls, model, model_parameters):
        if model in cls.THINKING_MODELS:
            return super()._thinking_parameters(model, model_parameters)
        return cls._candidate_thinking_parameters(model, model_parameters)


def candidate_adapter(model, field, kind, *, declare=True):
    path = ROOT / "models" / "llm" / f"{model}.yaml"
    schema = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert schema["model"] == model
    if not declare:
        # Explicit negative-control schema, including now-approved Qwen.
        schema["parameter_rules"] = [r for r in schema["parameter_rules"]
                                     if r["name"] != field]
    elif not any(r["name"] == field for r in schema["parameter_rules"]):
        rule = {"name": field, "type": kind, "required": False,
                "label": {"en_US": "Thinking control (test only)"}}
        if kind == "string":
            rule["options"] = ["low", "none"]
        schema["parameter_rules"].append(rule)
    return OfflineCandidateAdapter([AIModelEntity.model_validate(schema)])


@pytest.mark.parametrize("model,field,kind,on,off", CASES, ids=[c[0] for c in CASES])
@pytest.mark.parametrize("site", SITES, ids=["china", "overseas"])
@pytest.mark.parametrize("enabled", (True, False), ids=["on", "off"])
def test_candidate_reaches_http_json_without_changing_existing_fields(
    transport, model, field, kind, on, off, site, enabled,
):
    pending, sent = transport
    if model == "gpt-5.5" and site == SITES[0]:
        # Historical candidate contract predates site-scoped public exposure.
        # The present domestic boundary must hide this parameter.
        adapter = candidate_adapter(model, field, kind)
        schema = adapter.get_model_schema(model, {"api_key": KEY, "endpoint_url": site})
        assert all(rule.name != field for rule in schema.parameter_rules)
        return
    pending.append(response(completion(tool_call=False, content="offline-ok")))
    adapter = candidate_adapter(model, field, kind)
    credentials = {"api_key": KEY, "endpoint_url": site}
    parameters = {"temperature": 0.6, "top_p": 0.8, "max_tokens": 2048,
                  field: on if enabled else off}
    original = deepcopy((credentials, parameters))
    chunks = list(adapter.invoke(
        model=model, credentials=credentials,
        prompt_messages=[UserPromptMessage(content="Fixed short reasoning prompt.")],
        model_parameters=parameters, tools=None, stop=["END"], stream=False,
        user="offline-phase2-gate",
    ))
    assert (credentials, parameters) == original
    assert "".join(c.delta.message.content or "" for c in chunks) == "offline-ok"
    assert len(sent) == 1 and sent[0]["url"] == site + "/chat/completions"
    body = sent[0]["json"]
    assert body[field] == (on if enabled else off)
    assert body["model"] == model and body["stream"] is False
    assert body["messages"] == [{"role": "user", "content": "Fixed short reasoning prompt."}]
    assert body["temperature"] == 0.6 and body["top_p"] == 0.8
    assert body["max_tokens"] == 2048 and body["stop"] == ["END"]
    assert body["user"] == "offline-phase2-gate"
    assert not {"tools", "tool_choice", "extra_body", "thinking_budget", "thinking"} & body.keys()
    assert set(body) == {"model", "stream", "messages", "temperature", "top_p",
                         "max_tokens", "stop", "user", field}


@pytest.mark.parametrize("model,field,kind,on,off", CASES[1:], ids=[c[0] for c in CASES[1:]])
def test_undeclared_candidate_is_filtered_by_public_sdk(
    transport, model, field, kind, on, off,
):
    pending, sent = transport
    pending.append(response(completion(tool_call=False, content="offline-ok")))
    adapter = candidate_adapter(model, field, kind, declare=False)
    list(adapter.invoke(
        model=model, credentials={"api_key": KEY, "endpoint_url": SITES[0]},
        prompt_messages=[UserPromptMessage(content="Fixed short reasoning prompt.")],
        model_parameters={"max_tokens": 2048, field: off}, tools=None, stream=False,
    ))
    assert len(sent) == 1 and field not in sent[0]["json"]
