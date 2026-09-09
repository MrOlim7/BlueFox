import getpass
import json
import sys
import warnings
from pathlib import Path
from unittest.mock import Mock

import pytest

import BlueFox
from Program import ui
from Program.config import config
from Program.registry import registry

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("args, expected", [(["--help"], "--no-animation"), (["--version"], "3.0.0a1")])
def test_cli_flags_real_process(process, tmp_path, args, expected):
    result = process([sys.executable, str(ROOT / "BlueFox.py"), *args], cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert expected in result.stdout


def test_fast_navigation_all_categories_settings_and_quit(process, tmp_path):
    script = "".join(f"{index}\nb\n" for index in range(1, 7)) + "s\nb\nq\n"
    result = process([sys.executable, str(ROOT / "BlueFox.py"), "--no-animation", "--no-color"],
                     cwd=tmp_path, input=script)
    assert result.returncode == 0, result.stderr
    assert all(cat["name"] in result.stdout for cat in registry.categories.values())
    assert "BLUEFOX — RÉGLAGES" in result.stdout
    assert "Au revoir" in result.stdout
    assert "Choix invalide" not in result.stdout  # No hidden Enter gate consumed a choice.
    assert "\x1b" not in result.stdout
    assert "ACTIVE" not in result.stdout and "READY" not in result.stdout


@pytest.mark.parametrize("script", ["", "1\n", "s\n", "s\n2\n"])
def test_eof_exits_cleanly(process, tmp_path, script):
    result = process([sys.executable, str(ROOT / "BlueFox.py"), "--no-animation"], cwd=tmp_path, input=script)
    assert result.returncode == 0
    assert "Traceback" not in result.stderr


def test_no_animation_never_sleeps_or_waits_for_enter(monkeypatch):
    monkeypatch.setattr(ui, "interactive", lambda: True)
    sleep = Mock(side_effect=AssertionError("unexpected animation"))
    monkeypatch.setattr(ui.time, "sleep", sleep)
    prompts = Mock(return_value="q")
    monkeypatch.setattr(ui, "get_input", prompts)
    assert BlueFox.main(["--no-animation"]) == 0
    prompts.assert_called_once_with("Choix")
    sleep.assert_not_called()


def test_ctrl_c_at_boot_and_main(monkeypatch):
    monkeypatch.setattr(BlueFox, "boot_sequence", Mock(side_effect=KeyboardInterrupt))
    assert BlueFox.main(["--no-animation"]) == 130
    monkeypatch.setattr(BlueFox, "boot_sequence", Mock())
    monkeypatch.setattr(ui, "get_input", Mock(side_effect=KeyboardInterrupt))
    assert BlueFox.main(["--no-animation"]) == 130


def test_cancel_input_and_running_tool(monkeypatch, capsys):
    entry = registry.get("ip_lookup")
    run = Mock(side_effect=KeyboardInterrupt)
    monkeypatch.setattr(entry.implementation, "run", run)
    monkeypatch.setattr(ui, "get_input", lambda prompt: "")
    ui.run_tool(entry)
    run.assert_not_called()
    monkeypatch.setattr(ui, "get_input", lambda prompt: "192.0.2.1")
    ui.run_tool(entry)
    assert "Annulé" in capsys.readouterr().out


def test_settings_restore_theme_folder_workers(monkeypatch, tmp_path):
    answers = iter(["2", "purple", "3", str(tmp_path / "my results"), "4", "17", "b"])
    monkeypatch.setattr(ui, "get_input", lambda prompt: next(answers))
    BlueFox.hacker_settings()
    assert config["ui_theme"] == "purple"
    assert config["results_folder"] == str(tmp_path / "my results")
    assert config["max_workers"] == 17
    assert json.loads(config.path.read_text())["max_workers"] == 17


def test_settings_secret_keep_delete_and_masked_input(monkeypatch, capsys):
    config.set("ipgeo_api_key", "keep-me")
    config.set("abuseipdb_api_key", "delete-me")
    monkeypatch.setattr(ui, "get_input", Mock(side_effect=["1", "b"]))
    secret = Mock(side_effect=["", "-", "new-secret", "", "", ""])
    monkeypatch.setattr(getpass, "getpass", secret)
    BlueFox.hacker_settings()
    saved = json.loads(config.path.read_text())
    assert saved["ipgeo_api_key"] == "keep-me"
    assert saved["abuseipdb_api_key"] == ""
    assert saved["shodan_api_key"] == "new-secret"
    output = capsys.readouterr().out
    assert all(value not in output for value in ("keep-me", "delete-me", "new-secret"))
    assert secret.call_count == 6


def test_masked_input_refuses_visible_fallback(monkeypatch):
    def no_tty(prompt):
        warnings.warn("No TTY", getpass.GetPassWarning)
        raise AssertionError("visible fallback must not execute")
    monkeypatch.setattr(getpass, "getpass", no_tty)
    with pytest.raises(ValueError, match="Saisie masquée indisponible"):
        ui.get_secret("Clé")


def test_settings_cancel_does_not_apply_partial_key_edits(monkeypatch):
    monkeypatch.setattr(ui, "get_input", Mock(return_value="1"))
    monkeypatch.setattr(ui, "get_secret", Mock(side_effect=["unsaved-key", KeyboardInterrupt]))
    BlueFox.hacker_settings()
    assert config["ipgeo_api_key"] == ""
    assert not config.path.exists()


def test_settings_reports_save_failure(monkeypatch, capsys):
    monkeypatch.setattr(ui, "get_input", Mock(side_effect=["4", "18", "b"]))
    monkeypatch.setattr("os.replace", Mock(side_effect=PermissionError))
    BlueFox.hacker_settings()
    output = capsys.readouterr().out
    assert "droits insuffisants" in output
    assert "Réglages locaux sauvegardés" not in output
    assert "seulement pour cette session" in output


def test_invalid_workers_cli_returns_error(process, tmp_path):
    result = process([sys.executable, str(ROOT / "BlueFox.py"), "--max-workers", "0"], cwd=tmp_path)
    assert result.returncode == 2
    assert "entre 1 et 256" in result.stderr


def test_startup_without_requests_preserves_catalogue(process, tmp_path):
    script = '''import importlib.abc, sys
class Missing(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "requests":
            raise ModuleNotFoundError("requests unavailable", name="requests")
sys.meta_path.insert(0, Missing())
import BlueFox
from Program.registry import registry
assert len(registry.tools) == 51
assert not registry.get("ip_lookup").available
assert "requests" in registry.get("ip_lookup").unavailable_reason
assert registry.get("ping").implementation is not None
sys.exit(BlueFox.main(["--no-animation"]))
'''
    result = process([sys.executable, "-c", script], cwd=ROOT, input="q\n")
    assert result.returncode == 0, result.stderr
