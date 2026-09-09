import json
import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from Program import CONFIG, legacy_tools, settings
from Program.config import ConfigManager, config, mask_secret
from Program.tools.ip_lookup import IPLookupTool


def manager(tmp_path, data=None, env=None, overrides=None):
    path = tmp_path / "config.json"
    if data is not None:
        path.write_text(json.dumps(data))
    return ConfigManager(path, legacy_path=tmp_path / "absent.json", environ=env or {}, overrides=overrides)


def test_one_live_manager_and_both_families_use_updated_key(monkeypatch):
    assert CONFIG is legacy_tools.CONFIG is settings.CONFIG is config
    config.set("max_workers", 17)
    assert legacy_tools.CONFIG["max_workers"] == 17
    legacy_tools.CONFIG["ui_theme"] = "purple"
    assert config.get("ui_theme") == "purple"
    config.set("ipgeo_api_key", "fixture-key")
    responses = [Mock(json=lambda: {"status": "success", "country": "Fixture"}),
                 Mock(json=lambda: {"continent_name": "Fixture"})]
    http = Mock(side_effect=responses * 2)
    monkeypatch.setattr("requests.get", http)
    assert IPLookupTool().run(ip="192.0.2.1")["success"]
    monkeypatch.setattr(legacy_tools, "get_input", lambda prompt: "192.0.2.1")
    monkeypatch.setattr(legacy_tools, "ask_save", Mock())
    legacy_tools.ip_lookup()
    assert len(http.call_args_list) == 4
    assert all("fixture-key" in http.call_args_list[i].args[0] for i in (1, 3))


def test_layer_precedence_and_environment_not_saved(tmp_path):
    m = manager(tmp_path, {"max_workers": 3, "shodan_api_key": "local"},
                {"BLUEFOX_MAX_WORKERS": "4", "SHODAN_API_KEY": "environment"}, {"max_workers": 5})
    assert m["max_workers"] == 5
    assert m["shodan_api_key"] == "environment"
    m.set("ui_theme", "cyan")
    assert m.save()
    saved = json.loads(m.path.read_text())
    assert saved == {"max_workers": 3, "shodan_api_key": "local", "ui_theme": "cyan"}
    assert "environment" not in m.path.read_text()
    m.set_overrides({})
    assert m["max_workers"] == 4
    m.environment.clear()
    assert m["max_workers"] == 3
    del m["max_workers"]
    assert m["max_workers"] == 200


def test_delete_key_keeps_environment_override_until_removed(tmp_path):
    m = manager(tmp_path, {"shodan_api_key": "local"}, {"SHODAN_API_KEY": "env-secret"})
    m.set("shodan_api_key", "")
    assert m.save()
    assert m["shodan_api_key"] == "env-secret"
    assert manager(tmp_path)["shodan_api_key"] == ""
    assert json.loads(m.path.read_text())["shodan_api_key"] == ""


@pytest.mark.parametrize("key,value", [("max_workers", 0), ("max_workers", 257), ("max_workers", True),
    ("max_workers", "12"), ("max_workers", 3.5), ("ui_theme", "unknown"), ("ui_theme", None),
    ("results_folder", ""), ("results_folder", []), ("animations_enabled", "yes"), ("shodan_api_key", 42)])
def test_validation(tmp_path, key, value):
    m = manager(tmp_path)
    with pytest.raises(ValueError):
        m.set(key, value)
    with pytest.raises(ValueError):
        m.set_overrides({key: value})


def test_invalid_local_and_environment_fields_are_diagnosed(tmp_path):
    m = manager(tmp_path, {"max_workers": -1, "ui_theme": "broken"}, {"BLUEFOX_MAX_WORKERS": "bad", "BLUEFOX_ANIMATIONS": "maybe"})
    assert m["max_workers"] == 200
    assert m["ui_theme"] == "blue"
    assert len(m.issues) == 4


@pytest.mark.parametrize("content", ['{broken secret-text', '[1, 2]', 'null'])
def test_bad_json_preserved_and_no_secret_in_diagnostic(tmp_path, content):
    path = tmp_path / "config.json"
    path.write_text(content)
    m = manager(tmp_path)
    assert m["max_workers"] == 200
    assert m.issues
    assert not m.save()
    assert path.read_text() == content
    assert "secret-text" not in str(m.issues)


def test_atomic_save_failure_retains_previous_file(tmp_path, monkeypatch):
    m = manager(tmp_path, {"ui_theme": "green"})
    m.set("ui_theme", "purple")
    monkeypatch.setattr(os, "replace", Mock(side_effect=PermissionError("secret")))
    assert not m.save()
    assert "droits insuffisants" in m.last_error
    assert "secret" not in m.last_error
    assert json.loads(m.path.read_text()) == {"ui_theme": "green"}
    assert not list(tmp_path.glob(".bluefox-*.tmp"))


def test_read_permission_failure_and_missing_parent(tmp_path, monkeypatch):
    m = manager(tmp_path)
    monkeypatch.setattr(Path, "open", Mock(side_effect=PermissionError("private")))
    m.load()
    assert m.issues and not m.save()
    assert "private" not in str(m.issues)


def test_migration_copies_local_only_preserves_original_and_relative_results(tmp_path):
    legacy = tmp_path / "checkout/Program/bluefox_config.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(json.dumps({"shodan_api_key": "local-secret", "results_folder": "my results",
                                  "version": "2.5 beta", "custom": {"keep": True}}))
    before = legacy.read_bytes()
    target = tmp_path / "user/config.json"
    m = ConfigManager(target, legacy_path=legacy, environ={"SHODAN_API_KEY": "env-secret"})
    assert m["shodan_api_key"] == "env-secret"
    saved = json.loads(target.read_text())
    assert saved["shodan_api_key"] == "local-secret"
    assert saved["custom"] == {"keep": True}
    assert "version" not in saved
    assert m.results_path() == tmp_path / "checkout/my results"
    assert legacy.read_bytes() == before
    if os.name != "nt":
        assert target.stat().st_mode & 0o777 == 0o600
    target.write_text('{"max_workers": 18}')
    assert ConfigManager(target, legacy_path=legacy, environ={})["max_workers"] == 18


def test_explicit_environment_path_does_not_migrate(tmp_path):
    legacy = tmp_path / "old.json"
    legacy.write_text('{"max_workers": 7}')
    target = tmp_path / "new.json"
    m = ConfigManager(target, legacy_path=legacy, environ={"BLUEFOX_CONFIG_FILE": str(target)})
    assert m["max_workers"] == 200
    assert not target.exists()


def test_results_paths_agree_between_doctor_and_legacy(tmp_path, monkeypatch):
    config.set("results_folder", "saved files")
    monkeypatch.chdir(tmp_path.parent)
    legacy_tools.ensure_results_folder()
    assert config.results_path().is_dir()
    path = legacy_tools.save_result("fixture", {"example": 1}, "json")
    assert Path(path).parent == config.results_path()


def test_secret_masking_and_errors(capsys):
    config.set("shodan_api_key", "fixture-secret")
    legacy_tools.print_error("URL?key=fixture-secret")
    assert "fixture-secret" not in capsys.readouterr().out
    assert mask_secret("short") == mask_secret("much-longer-secret") == "********"
