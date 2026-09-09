"""Simulated transport checks for the interfaces retained during migration."""
import subprocess
from unittest.mock import Mock

import pytest

from Program import legacy_tools
from Program.tools.ping import PingTool
from Program.tools import reverse_dns, dns_lookup_suite


@pytest.mark.parametrize("platform, flag", [("Windows", "-n"), ("Linux", "-c"), ("Darwin", "-c")])
def test_ping_preserves_four_probe_behavior(monkeypatch, platform, flag):
    monkeypatch.setattr("platform.system", lambda: platform)
    run = Mock(return_value=subprocess.CompletedProcess([], 0, stdout="fixture ping", stderr=""))
    monkeypatch.setattr(subprocess, "run", run)
    result = PingTool().run(ip="192.0.2.1")
    assert result["success"] and result["output"] == "fixture ping"
    run.assert_called_once_with(["ping", flag, "4", "192.0.2.1"], capture_output=True, text=True, timeout=15)


def test_legacy_reverse_dns_uses_simulated_socket(monkeypatch, capsys):
    monkeypatch.setattr(legacy_tools, "get_input", lambda prompt: "192.0.2.1")
    reverse = Mock(return_value=("fixture.example", [], ["192.0.2.1"]))
    monkeypatch.setattr(legacy_tools.socket, "gethostbyaddr", reverse)
    monkeypatch.setattr(legacy_tools, "ask_save", Mock())
    reverse_dns.run()
    reverse.assert_called_once_with("192.0.2.1")
    assert "fixture.example" in capsys.readouterr().out


def test_legacy_dns_uses_simulated_resolver_and_retains_export(monkeypatch):
    monkeypatch.setattr(legacy_tools, "get_input", lambda prompt: "fixture.example")
    resolve = Mock(return_value=["192.0.2.1"])
    save = Mock()
    monkeypatch.setattr(legacy_tools.dns.resolver, "resolve", resolve)
    monkeypatch.setattr(legacy_tools, "ask_save", save)
    dns_lookup_suite.run()
    assert resolve.call_count == 8
    assert save.call_args.args[1]["records"]["A"] == ["192.0.2.1"]
