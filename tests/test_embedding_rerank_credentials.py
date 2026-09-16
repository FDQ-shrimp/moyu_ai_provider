"""Credential routing tests for embedding and rerank adapters."""

from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    ("import_path", "class_name"),
    [
        ("models.text_embedding.text_embedding", "MoyuTextEmbeddingModel"),
        ("models.rerank.rerank", "MoyuRerankModel"),
    ],
)
def test_missing_endpoint_uses_current_domestic_api(import_path: str, class_name: str):
    module = __import__(import_path, fromlist=[class_name])
    adapter = getattr(module, class_name)

    patched = adapter._patched_credentials({"api_key": " demo "})

    assert patched["api_key"] == "demo"
    assert patched["endpoint_url"] == "https://www.moyu.cn/v1"


@pytest.mark.parametrize(
    ("import_path", "class_name"),
    [
        ("models.text_embedding.text_embedding", "MoyuTextEmbeddingModel"),
        ("models.rerank.rerank", "MoyuRerankModel"),
    ],
)
def test_configured_endpoint_is_preserved_without_mutating_caller(
    import_path: str, class_name: str
):
    module = __import__(import_path, fromlist=[class_name])
    adapter = getattr(module, class_name)
    original = {
        "api_key": " demo ",
        "endpoint_url": "  https://www.konjac.ai/v1/  ",
    }

    patched = adapter._patched_credentials(original)

    assert patched["endpoint_url"] == "https://www.konjac.ai/v1"
    assert original["endpoint_url"] == "  https://www.konjac.ai/v1/  "


@pytest.mark.parametrize(
    ("import_path", "class_name"),
    [
        ("models.text_embedding.text_embedding", "MoyuTextEmbeddingModel"),
        ("models.rerank.rerank", "MoyuRerankModel"),
    ],
)
def test_blank_endpoint_falls_back_to_current_domestic_api(
    import_path: str, class_name: str
):
    module = __import__(import_path, fromlist=[class_name])
    adapter = getattr(module, class_name)

    patched = adapter._patched_credentials(
        {"api_key": "demo", "endpoint_url": "   "}
    )

    assert patched["endpoint_url"] == "https://www.moyu.cn/v1"


def test_embedding_invoke_forwards_configured_endpoint_to_sdk(monkeypatch):
    from dify_plugin import OAICompatEmbeddingModel
    from models.text_embedding.text_embedding import MoyuTextEmbeddingModel

    captured = {}

    def fake_invoke(self, model, credentials, *args):
        captured.update(credentials)
        return "ok"

    monkeypatch.setattr(OAICompatEmbeddingModel, "_invoke", fake_invoke)
    adapter = object.__new__(MoyuTextEmbeddingModel)

    result = adapter._invoke(
        "demo-embedding",
        {"api_key": "demo", "endpoint_url": "https://www.konjac.ai/v1/"},
        ["hello"],
    )

    assert result == "ok"
    assert captured["endpoint_url"] == "https://www.konjac.ai/v1"


def test_rerank_invoke_forwards_endpoint_and_repairs_top_n(monkeypatch):
    from dify_plugin import OAICompatRerankModel
    from models.rerank.rerank import MoyuRerankModel

    captured = {}

    def fake_invoke(
        self, model, credentials, query, docs, score_threshold, top_n, user
    ):
        captured["credentials"] = credentials
        captured["top_n"] = top_n
        return "ok"

    monkeypatch.setattr(OAICompatRerankModel, "_invoke", fake_invoke)
    adapter = object.__new__(MoyuRerankModel)

    result = adapter._invoke(
        "demo-rerank",
        {"api_key": "demo", "endpoint_url": "https://www.konjac.ai/v1/"},
        "query",
        ["one", "two"],
        top_n=None,
    )

    assert result == "ok"
    assert captured["credentials"]["endpoint_url"] == "https://www.konjac.ai/v1"
    assert captured["top_n"] == 2
