"""Local checks only: no HTTP, DNS, socket connections or system commands."""
import shutil
import sys
import tempfile
from pathlib import Path

from .config import config
from .registry import DEPENDENCIES, dependency_error, registry
from .version import __version__
from . import ui


def writable_directory(path):
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=path):
            pass
        return None
    except OSError as exc:
        return "droits insuffisants" if isinstance(exc, PermissionError) else type(exc).__name__


def checks(manager=config, catalogue=registry):
    supported = (3, 10) <= sys.version_info[:2] <= (3, 14)
    yield "Python", supported, sys.version.split()[0] + " (cible : 3.10–3.14)"
    for module, distribution in DEPENDENCIES.items():
        error = dependency_error(module)
        yield distribution + " / " + module, error is None, error or "import réussi"
    commands = ["ping", "tracert" if sys.platform == "win32" else "traceroute", "nslookup"]
    commands += ["ipconfig"] if sys.platform == "win32" else ["ifconfig"]
    if sys.platform.startswith("linux"):
        commands.append("ip")
    for name in commands:
        path = shutil.which(name)
        yield name, path is not None, path or "commande absente (outils concernés uniquement)"
    for issue in manager.issues:
        yield "Configuration", "copiée" in issue, issue
    error = writable_directory(manager.path.parent)
    yield "Dossier de configuration", error is None, error or str(manager.path.parent)
    error = writable_directory(manager.results_path())
    yield "Dossier de résultats", error is None, error or str(manager.results_path())
    for entry in catalogue.tools.values():
        if not entry.available:
            yield entry.id, False, entry.unavailable_reason
        for warning in entry.warnings:
            yield entry.id, False, warning


def run_doctor():
    ui.print_header(f"BlueFox {__version__} — doctor local (aucun appel réseau)")
    failed = False
    for label, ok, detail in checks():
        ui.print_result(f"{'OK' if ok else 'ATTENTION'} {label}", detail)
        failed |= not ok
    ui.print_info("Présence/imports vérifiés ; fournisseurs, réseau et Discord non testés")
    return 1 if failed else 0
