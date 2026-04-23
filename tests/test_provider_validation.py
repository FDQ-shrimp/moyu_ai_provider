"""Tests for MoyuProvider.validate_provider_credentials.

`dify_plugin.ModelProvider.__init__` requires arguments we don't have in a
unit-test context (provider_schemas / model_factory). We therefore build
the instance through `object.__new__`, which bypasses __init__ entirely.
That is sound because `validate_provider_credentials` is a plain method
that uses `self` only as a namespace and does not touch any attribute the
base constructor would populate.
"""

from __future__ import annotations

import os

import pytest


def _new_provider():
    from provider.moyu import MoyuProvider

    return object.__new__(MoyuProvider)


def test_empty_api_key_rejected():
    from dify_plugin.errors.model import CredentialsValidateFailedError

    provider = _new_provider()
    with pytest.raises(CredentialsValidateFailedError):
        provider.validate_provider_credentials({})


def test_whitespace_api_key_rejected():
    from dify_plugin.errors.model import CredentialsValidateFailedError

    provider = _new_provider()
    with pytest.raises(CredentialsValidateFailedError):
        provider.validate_provider_credentials({"api_key": "   "})


def test_non_empty_api_key_accepted_without_network():
    provider = _new_provider()
    # Must not raise; there is no network call on the shape-level check.
    provider.validate_provider_credentials({"api_key": "sk-fake-but-nonempty"})


def test_validation_independent_of_env(monkeypatch):
    """Provider shape-check must be a pure function of its argument dict."""
    from dify_plugin.errors.model import CredentialsValidateFailedError

    monkeypatch.setenv("REMOTE_INSTALL_KEY", "uuid-irrelevant")
    monkeypatch.delenv("MOYU_API_KEY", raising=False)
    assert os.environ.get("REMOTE_INSTALL_KEY") == "uuid-irrelevant"

    provider = _new_provider()

    with pytest.raises(CredentialsValidateFailedError):
        provider.validate_provider_credentials({"api_key": ""})

    provider.validate_provider_credentials({"api_key": "something"})
