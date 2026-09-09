"""No real network in tests, including child CLI processes."""
import os
import socket
import subprocess
import tempfile
from pathlib import Path

import pytest

# This precedes application imports during collection.
_ISOLATION = tempfile.TemporaryDirectory(prefix="bluefox-tests-")
os.environ["BLUEFOX_CONFIG_FILE"] = str(Path(_ISOLATION.name) / "config.json")
for variable in ("IPGEO_API_KEY", "ABUSEIPDB_API_KEY", "SHODAN_API_KEY", "VIRUSTOTAL_API_KEY",
                 "HUNTER_API_KEY", "NUMVERIFY_API_KEY", "BLUEFOX_THEME", "BLUEFOX_MAX_WORKERS",
                 "BLUEFOX_RESULTS_FOLDER", "BLUEFOX_ANIMATIONS"):
    os.environ.pop(variable, None)


@pytest.fixture(autouse=True)
def isolation(monkeypatch, tmp_path, request):
    from Program.config import config
    config.path = tmp_path / "config.json"
    config.legacy_path = tmp_path / "absent.json"
    config.environ = {}
    config.set_overrides({})
    config.load()
    attempts = []

    def denied(*args, **kwargs):
        attempts.append("unexpected network/system call")
        raise AssertionError(attempts[-1])

    for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr", "create_connection"):
        monkeypatch.setattr(socket, name, denied)
    for name in ("connect", "connect_ex", "sendto"):
        monkeypatch.setattr(socket.socket, name, denied)
    import requests
    import dns.resolver
    monkeypatch.setattr(requests.sessions.Session, "request", denied)
    monkeypatch.setattr(dns.resolver.Resolver, "resolve", denied)
    monkeypatch.setattr(dns.resolver, "resolve", denied)
    if "process" not in request.fixturenames:
        monkeypatch.setattr(subprocess, "run", denied)
        monkeypatch.setattr(subprocess, "Popen", denied)
    yield
    assert not attempts, "A test attempted a real network/system operation"


@pytest.fixture
def process(tmp_path):
    guard = tmp_path / "guard"
    guard.mkdir()
    marker = guard / "network-attempt"
    (guard / "sitecustomize.py").write_text('''import os, socket, subprocess
from pathlib import Path

def denied(*args, **kwargs):
    Path(os.environ["BLUEFOX_TEST_NETWORK_MARKER"]).touch()
    raise RuntimeError("Network and system commands forbidden by test")
for name in ("getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr", "create_connection"):
    setattr(socket, name, denied)
for name in ("connect", "connect_ex", "sendto"):
    setattr(socket.socket, name, denied)
subprocess.run = denied
subprocess.Popen = denied
''')
    env = {**os.environ, "PYTHONPATH": str(guard), "PYTHONUTF8": "1", "NO_COLOR": "1",
           "BLUEFOX_CONFIG_FILE": str(tmp_path / "child-config.json"),
           "BLUEFOX_TEST_NETWORK_MARKER": str(marker)}

    def run(args, **kwargs):
        result = subprocess.run(args, env=kwargs.pop("env", env), capture_output=True,
                                text=True, encoding="utf-8", timeout=30, **kwargs)
        assert not marker.exists(), "Child attempted a network/system operation"
        return result
    run.env = env
    return run
