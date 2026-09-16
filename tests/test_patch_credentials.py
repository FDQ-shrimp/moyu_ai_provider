"""Tests for `MoyuLargeLanguageModel._patch_credentials`.

These are the most value-dense tests: the historical `KeyError: 'endpoint_url'`
incident happened right here, so we pin the expected behaviour.
"""

from __future__ import annotations


def test_patch_credentials_injects_endpoint_and_mode():
    from models.llm.llm import MoyuLargeLanguageModel

    creds = {"api_key": "  sk-demo  "}
    MoyuLargeLanguageModel._patch_credentials(creds)

    assert creds["api_key"] == "sk-demo", "api_key must be stripped in place"
    assert creds["endpoint_url"] == MoyuLargeLanguageModel.BASE_URL
    assert creds["mode"] == "chat"


def test_patch_credentials_handles_missing_key():
    from models.llm.llm import MoyuLargeLanguageModel

    creds: dict = {}
    MoyuLargeLanguageModel._patch_credentials(creds)

    assert creds["api_key"] == ""
    assert creds["endpoint_url"] == MoyuLargeLanguageModel.BASE_URL
    assert creds["mode"] == "chat"


def test_patched_credentials_does_not_mutate_caller():
    from models.llm.llm import MoyuLargeLanguageModel

    original = {"api_key": " abc "}
    patched = MoyuLargeLanguageModel._patched_credentials(original)

    assert patched is not original
    assert "endpoint_url" not in original, "caller dict must stay unchanged"
    assert patched["endpoint_url"] == MoyuLargeLanguageModel.BASE_URL
    assert patched["api_key"] == "abc"


def test_base_url_points_at_v1():
    from models.llm.llm import MoyuLargeLanguageModel

    assert MoyuLargeLanguageModel.BASE_URL.endswith("/v1")
    assert MoyuLargeLanguageModel.BASE_URL.startswith("https://")


def test_missing_endpoint_uses_current_domestic_api():
    from models.llm.llm import MoyuLargeLanguageModel

    patched = MoyuLargeLanguageModel._patched_credentials({"api_key": "demo"})

    assert patched["endpoint_url"] == "https://www.moyu.cn/v1"


def test_configured_endpoint_is_preserved_and_normalized():
    from models.llm.llm import MoyuLargeLanguageModel

    original = {
        "api_key": " demo ",
        "endpoint_url": "  https://www.konjac.ai/v1/  ",
    }
    patched = MoyuLargeLanguageModel._patched_credentials(original)

    assert patched["endpoint_url"] == "https://www.konjac.ai/v1"
    assert original["endpoint_url"] == "  https://www.konjac.ai/v1/  "


def test_blank_endpoint_falls_back_to_current_domestic_api():
    from models.llm.llm import MoyuLargeLanguageModel

    patched = MoyuLargeLanguageModel._patched_credentials(
        {"api_key": "demo", "endpoint_url": "   "}
    )

    assert patched["endpoint_url"] == "https://www.moyu.cn/v1"


def test_invoke_forwards_configured_endpoint_to_sdk(monkeypatch):
    from dify_plugin import OAICompatLargeLanguageModel
    from models.llm.llm import MoyuLargeLanguageModel

    captured = {}

    def fake_invoke(self, model, credentials, *args):
        captured.update(credentials)
        return "ok"

    monkeypatch.setattr(OAICompatLargeLanguageModel, "_invoke", fake_invoke)
    adapter = object.__new__(MoyuLargeLanguageModel)

    result = adapter._invoke(
        "demo-model",
        {"api_key": "demo", "endpoint_url": "https://www.konjac.ai/v1/"},
        [],
        {},
        stream=False,
    )

    assert result == "ok"
    assert captured["endpoint_url"] == "https://www.konjac.ai/v1"
    assert captured["mode"] == "chat"
