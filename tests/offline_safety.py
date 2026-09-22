"""Process-local test safeguards, installed BEFORE importing the real SDK."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_enabled = False


def _audit(event, args):
    if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
        name = Path(os.fsdecode(args[0])).name.lower()
        if name == ".env" or name.startswith(".env."):
            raise RuntimeError("Offline checks forbid opening dotenv files")
    if event in {"socket.connect", "socket.getaddrinfo", "socket.sendto",
                 "subprocess.Popen", "os.system"}:
        raise RuntimeError("Offline checks forbid network access and child processes")


def enable():
    global _enabled
    if _enabled:
        return
    sys.addaudithook(_audit)
    # The SDK instantiates DifyPluginEnv during import. Disable settings sources
    # before that happens; do not merely change cwd and hope .env is absent.
    from pydantic_settings.sources import DotEnvSettingsSource, EnvSettingsSource

    DotEnvSettingsSource._read_env_files = lambda self: {}
    EnvSettingsSource._load_env_vars = lambda self: {}
    _enabled = True


def block_transports():
    """Install after SDK/gevent startup; tests replace only requests.post."""
    import socket
    import requests

    def denied(*args, **kwargs):
        raise RuntimeError("Offline checks forbid real network transport")

    socket.socket.connect = denied
    socket.socket.connect_ex = denied
    socket.socket.sendto = denied
    socket.getaddrinfo = denied
    requests.sessions.Session.send = denied
