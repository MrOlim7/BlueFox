import sys
from pathlib import Path
from unittest.mock import Mock

from Program import doctor
from Program.config import config

ROOT = Path(__file__).resolve().parents[1]


def test_doctor_is_local_and_reports_missing_commands(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    rows = list(doctor.checks())
    assert any(label == "ping" and not ok for label, ok, _ in rows)
    assert any(label == "Dossier de résultats" and ok for label, ok, _ in rows)


def test_doctor_permission_failure(monkeypatch):
    monkeypatch.setattr(doctor.tempfile, "TemporaryFile", Mock(side_effect=PermissionError("private")))
    rows = list(doctor.checks())
    assert any(label == "Dossier de résultats" and not ok and "droits" in detail for label, ok, detail in rows)
    assert "private" not in str(rows)


def test_doctor_real_process_without_network(process, tmp_path):
    result = process([sys.executable, str(ROOT / "BlueFox.py"), "doctor"], cwd=tmp_path)
    assert result.returncode in (0, 1), result.stderr
    assert "aucun appel réseau" in result.stdout
    assert "Dossier de résultats" in result.stdout
    assert "Traceback" not in result.stderr
