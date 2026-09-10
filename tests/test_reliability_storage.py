import csv
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from Program import legacy_tools as core, result_storage as storage
from Program.config import config


def test_concurrent_same_second_exports_are_complete_and_unique(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "datetime", Mock(now=lambda: Mock(strftime=lambda _: "same_second")))
    with ThreadPoolExecutor(max_workers=16) as executor:
        paths = list(executor.map(lambda i: storage.write_result(tmp_path, "same", {"i": i}), range(64)))
    assert len(set(paths)) == 64
    assert [json.loads(Path(path).read_text())["i"] for path in paths] == list(range(64))
    assert len(list(tmp_path.iterdir())) == 64


def test_forced_collision_cannot_overwrite_and_retries(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, "uuid4", lambda: SimpleNamespace(hex="collision"))
    monkeypatch.setattr(storage, "datetime", Mock(now=lambda: Mock(strftime=lambda _: "same_second")))
    original = storage.write_result(tmp_path, "same", {"original": True})
    with pytest.raises(FileExistsError):
        storage.write_result(tmp_path, "same", {"replacement": True})
    assert json.loads(Path(original).read_text()) == {"original": True}
    assert len(list(tmp_path.iterdir())) == 1
    ids = iter(["collision", "unique"])
    monkeypatch.setattr(storage, "uuid4", lambda: SimpleNamespace(hex=next(ids)))
    assert storage.write_result(tmp_path, "same", {}) != original


@pytest.mark.parametrize("stage", ["directory", "temporary", "flush", "publish"])
def test_disk_failure_has_no_final_export_or_success(monkeypatch, tmp_path, capsys, stage):
    config.set("results_folder", str(tmp_path / "results"))
    failing = Mock(side_effect=PermissionError("simulated disk failure"))
    if stage == "directory":
        monkeypatch.setattr(Path, "mkdir", failing)
    elif stage == "temporary":
        monkeypatch.setattr(storage.tempfile, "NamedTemporaryFile", failing)
    elif stage == "flush":
        monkeypatch.setattr(storage.os, "fsync", failing)
    else:
        monkeypatch.setattr(storage.os, "link", failing)
    assert core.save_result("fixture", {"field": "value"}) is None
    output = capsys.readouterr().out
    assert "Erreur sauvegarde" in output and "[OK]" not in output
    assert not list((tmp_path / "results").glob("*"))


def test_partial_temp_write_is_never_published(monkeypatch, tmp_path):
    original = storage.tempfile.NamedTemporaryFile
    def broken(**kwargs):
        stream = original(**kwargs)
        def write(content):
            stream.file.write(content[:3])
            raise OSError("disk full")
        stream.write = write
        return stream
    monkeypatch.setattr(storage.tempfile, "NamedTemporaryFile", broken)
    with pytest.raises(OSError):
        storage.write_result(tmp_path, "fixture", {"long": "value"})
    assert not list(tmp_path.iterdir())


def test_destination_is_only_visible_when_complete(monkeypatch, tmp_path):
    original = storage.os.link
    def publish(source, destination):
        assert not Path(destination).exists()
        assert json.loads(Path(source).read_text()) == {"complete": True}
        original(source, destination)
    monkeypatch.setattr(storage.os, "link", publish)
    storage.write_result(tmp_path, "fixture", {"complete": True})


def test_unknown_format_rejected_without_success_or_files(monkeypatch, tmp_path, capsys):
    config.set("results_folder", str(tmp_path))
    assert core.save_result("fixture", {}, "html") is None
    assert "Format d'export inconnu" in capsys.readouterr().out
    assert not list(tmp_path.iterdir())


def test_unknown_format_is_diagnosed_in_interactive_prompts(monkeypatch, capsys):
    monkeypatch.setattr(core, "get_input", lambda _: "html")
    core.ask_save("fixture", {})
    assert core.ask_export_format() is None
    assert capsys.readouterr().out.count("Format d'export inconnu") == 2


@pytest.mark.parametrize("value", ["=1+1", "+cmd", "-1+1", "@SUM(A1)", "  =1", "\t=1", "\r=1", "\n=1"])
def test_csv_formula_cells_are_escaped_but_json_preserves_values(tmp_path, value):
    path = storage.write_result(tmp_path, "csv", {value: value}, "csv")
    with open(path, newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    assert rows[1] == ["'" + value, "'" + value]
    path = storage.write_result(tmp_path, "json", {value: value}, "json")
    assert json.loads(Path(path).read_text()) == {value: value}


def test_report_excludes_previous_reports_and_handles_list_sources(monkeypatch, tmp_path):
    config.set("results_folder", str(tmp_path))
    storage.write_result(tmp_path, "source", ["fixture", 42])
    storage.write_result(tmp_path, "REPORT", {"sections": []})
    storage.write_result(tmp_path, "renamed", {"title": "BlueFox OSINT Investigation Report", "sections": []})
    monkeypatch.setattr(core, "get_input", lambda _: "0")
    core.report_generator()
    core.report_generator()
    reports = [json.loads(path.read_text()) for path in tmp_path.glob("REPORT_*.json")]
    generated = [r for r in reports if r.get("report_kind")]
    assert len(generated) == 2
    assert all(len(r["sections"]) == 1 for r in generated)
    assert generated[0]["sections"][0]["data"] == ["fixture", 42]
    assert len(list(tmp_path.glob("REPORT_*.txt"))) == 2


def test_report_invalid_source_aborts_explicitly(monkeypatch, tmp_path, capsys):
    config.set("results_folder", str(tmp_path))
    (tmp_path / "broken.json").write_text("{")
    monkeypatch.setattr(core, "get_input", lambda _: "0")
    core.report_generator()
    assert not list(tmp_path.glob("REPORT_*"))
    assert "Rapport annulé" in capsys.readouterr().out


def test_report_write_error_never_announces_success(monkeypatch, tmp_path, capsys):
    config.set("results_folder", str(tmp_path))
    storage.write_result(tmp_path, "source", {})
    monkeypatch.setattr(core, "get_input", lambda _: "0")
    monkeypatch.setattr(storage.os, "link", Mock(side_effect=OSError("disk full")))
    core.report_generator()
    assert "[OK]" not in capsys.readouterr().out
    assert not list(tmp_path.glob("REPORT_*"))
