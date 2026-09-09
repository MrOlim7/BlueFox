import importlib
import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from Program.catalogue import TOOL_SPECS
from Program.registry import ToolRegistry, registry
from Program.tools.base import BaseTool
from Program import ui

ROOT = Path(__file__).resolve().parents[1]


def test_complete_inventory_by_module_and_historical_category():
    modules = {path.stem for path in (ROOT / "Program/tools").glob("*.py")} - {"__init__", "base"}
    assert set(registry.tools) | {"ping_ip"} == modules
    history = json.loads((ROOT / "tests/fixtures/catalogue_5bedac2.json").read_text())
    for category, rows in history.items():
        expected = {"ping" if module == "ping_ip" else module for _, module in rows}
        if category == "NETWORK":
            expected.add("subnet_calculator")  # Previously orphaned, deliberately restored.
        assert {entry.id for _, entry in registry.categories[category]["tools"]} == expected
    assert registry.get("ping_ip") is registry.get("ping")
    assert registry.get("subnet_calculator").kind == "legacy"
    assert {t.id for t in registry.tools.values() if t.kind == "base"} == {"ping", "ip_lookup"}


def test_deterministic_order_and_duplicates():
    other = ToolRegistry(reversed(TOOL_SPECS))
    assert list(other.tools) == sorted(registry.tools)
    for category in other.categories:
        assert [t.id for _, t in other.categories[category]["tools"]] == sorted(
            t.id for _, t in registry.categories[category]["tools"])
    with pytest.raises(ValueError, match="dupliqué"):
        ToolRegistry([TOOL_SPECS[0], TOOL_SPECS[0]])


@pytest.mark.parametrize("missing, affected", [("whois", "whois_lookup"), ("dns.resolver", "dns_lookup_suite"), ("PIL.Image", "image_metadata")])
def test_absent_dependency_stays_in_catalogue(monkeypatch, missing, affected):
    actual = importlib.import_module
    def importing(name):
        if name == missing:
            raise ModuleNotFoundError(name, name=name)
        return actual(name)
    monkeypatch.setattr(importlib, "import_module", importing)
    catalogue = ToolRegistry()
    entry = catalogue.get(affected)
    assert not entry.available
    assert "import impossible" in entry.unavailable_reason
    assert set(catalogue.tools) == set(registry.tools)
    assert catalogue.get("file_hash_audit").available


def test_broken_tool_import_visible_without_hiding_category(monkeypatch):
    actual = importlib.import_module
    def importing(name):
        if name == "Program.tools.asn_info":
            raise RuntimeError("sensitive exception payload")
        return actual(name)
    monkeypatch.setattr(importlib, "import_module", importing)
    catalogue = ToolRegistry()
    assert not catalogue.get("asn_info").available
    assert "RuntimeError" in catalogue.get("asn_info").unavailable_reason
    assert "sensitive" not in catalogue.get("asn_info").unavailable_reason
    assert catalogue.get("ip_lookup").available


def test_dispatch_legacy_does_not_fabricate_success(capsys):
    entry = registry.get("subnet_calculator")
    original = entry.implementation
    try:
        entry.implementation = Mock(return_value=None)
        assert ui.run_tool(entry, pause_after=False) is None
        entry.implementation.assert_called_once_with()
        output = capsys.readouterr().out
        assert "historique" in output
        assert "[OK]" not in output
    finally:
        entry.implementation = original


def test_dispatch_migrated_collects_inputs_and_presents(monkeypatch, capsys):
    entry = registry.get("ip_lookup")
    assert isinstance(entry.implementation, BaseTool)
    monkeypatch.setattr(ui, "get_input", lambda prompt: "192.0.2.1")
    run = Mock(return_value={"success": True, "data": {"Pays": "Fixture"}})
    monkeypatch.setattr(entry.implementation, "run", run)
    ui.run_tool(entry, pause_after=False)
    run.assert_called_once_with(ip="192.0.2.1")
    assert "Pays: Fixture" in capsys.readouterr().out


def test_legacy_wrappers_use_same_dispatch(monkeypatch):
    call = Mock()
    monkeypatch.setattr(ui, "run_tool", call)
    from Program.tools import ip_lookup, ping_ip
    ip_lookup.run()
    ping_ip.run()
    assert [c.args[0].id for c in call.call_args_list] == ["ip_lookup", "ping"]
    for category in ("network", "osint", "web", "reports", "discovery", "intel"):
        module = importlib.import_module(f"Program.{category}")
        assert len(module.TOOLS) == len(registry.categories[category.upper()]["tools"])
        assert all(callable(run) for _, run in module.TOOLS)


def test_legacy_wrapper_still_calls_historical_implementation(monkeypatch):
    from Program import legacy_tools
    call = Mock()
    monkeypatch.setattr(legacy_tools, "subnet_calculator", call)
    registry.get("subnet_calculator").run_legacy()
    call.assert_called_once_with()
