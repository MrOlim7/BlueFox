"""Exercise real shell/batch launchers from foreign directories with spaces."""
import os
import shutil
import subprocess
import sys
import sysconfig
import venv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def checkout(tmp_path, process):
    target = tmp_path / "checkout with spaces"
    target.mkdir()
    for name in ("start.sh", "start.bat", "setup.bat", "BlueFox.py"):
        shutil.copy2(ROOT / name, target / name)
    shutil.copytree(ROOT / "Program", target / "Program", ignore=shutil.ignore_patterns("__pycache__", "bluefox_config.json"))
    # A real isolated interpreter; reuse already installed test dependencies
    # through a .pth file, without pip or a network connection in the tests.
    venv.EnvBuilder(with_pip=False).create(target / ".venv")
    if os.name == "nt":
        site = target / ".venv/Lib/site-packages"
    else:
        site = target / f".venv/lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
    site.mkdir(parents=True, exist_ok=True)
    (site / "test-dependencies.pth").write_text(sysconfig.get_paths()["purelib"] + "\n")
    return target


def invocation(checkout, *args):
    if os.name == "nt":
        # cmd /s /c needs an outer quote pair around the full command.
        command = subprocess.list2cmdline([str(checkout / "start.bat"), *args])
        return f'cmd.exe /d /s /c "{command}"'
    return ["bash", str(checkout / "start.sh"), *args]


def test_real_launcher_other_directory_spaces_and_arguments(checkout, process, tmp_path):
    result = process(invocation(checkout, "--version"), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert "BlueFox 3.0.0a1" in result.stdout
    result = process(invocation(checkout, "--no-animation", "--no-color"), cwd=tmp_path, input="q\n")
    assert result.returncode == 0, result.stderr
    assert "Au revoir" in result.stdout


def test_launcher_uses_venv_exact_arguments_and_exit_code(checkout, process, tmp_path):
    (checkout / "BlueFox.py").write_text('import json,sys; print(json.dumps([sys.executable, sys.argv[1:]])); sys.exit(37)')
    result = process(invocation(checkout, "--results-folder", "folder with spaces"), cwd=tmp_path)
    assert result.returncode == 37
    import json
    executable, args = json.loads(result.stdout)
    assert Path(executable).is_relative_to(checkout / ".venv")
    assert args == ["--results-folder", "folder with spaces"]


def test_launcher_no_venv_explains_installation(tmp_path, process):
    target = tmp_path / "without venv"
    target.mkdir()
    for name in ("start.sh", "start.bat"):
        shutil.copy2(ROOT / name, target / name)
    result = process(invocation(target), cwd=tmp_path)
    assert result.returncode == 1
    assert "environnement absent" in result.stderr


@pytest.mark.skipif(os.name != "nt", reason="setup.bat requires Windows cmd.exe")
def test_windows_setup_propagates_install_failure(checkout, process, tmp_path):
    # Simulate pip failure without installing anything or contacting an index.
    (Path(process.env["PYTHONPATH"]) / "pip.py").write_text("import sys; sys.exit(23)")
    command = subprocess.list2cmdline([str(checkout / "setup.bat")])
    result = process(f'cmd.exe /d /s /c "{command}"', cwd=tmp_path)
    assert result.returncode == 1
    assert "Echec" in result.stderr
    assert "BlueFox installe" not in result.stdout
