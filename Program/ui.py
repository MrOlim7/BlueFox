"""Small terminal layer with no network or legacy imports."""
import getpass
import os
import sys
import time
import warnings

from .config import config

NO_COLOR = False
COLORS = {"blue": 94, "cyan": 96, "green": 92, "red": 91, "purple": 95}


def interactive():
    return sys.stdin.isatty() and sys.stdout.isatty()


def color(text):
    text = config.redact(text)
    if NO_COLOR or "NO_COLOR" in os.environ or not sys.stdout.isatty():
        return text
    return f"\033[{COLORS[config['ui_theme']]}m{text}\033[0m"


def clear():
    if interactive() and not NO_COLOR and "NO_COLOR" not in os.environ:
        print("\033[2J\033[H", end="")


def center(text, width=76):
    return str(text).center(width)


def get_input(prompt):
    return input(color(f"  {prompt} : ")).strip()


def get_secret(prompt):
    # Refuse getpass's visible-input fallback (redirected stdin / broken TTY).
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            return getpass.getpass(f"  {prompt} : ")
        except getpass.GetPassWarning as exc:
            raise ValueError("Saisie masquée indisponible : utilisez un terminal ou une variable d'environnement") from exc


def pause():
    if interactive():
        get_input("Entrée pour continuer")


def delay(seconds):
    if config["animations_enabled"] and interactive():
        time.sleep(seconds)


def print_header(title):
    print(color(f"\n  {'═' * 60}\n  {title}\n  {'═' * 60}"))


def print_result(key, value):
    print(color(f"  {key}: {value}"))


def print_success(message):
    print(color(f"  [OK] {message}"))


def print_error(message):
    print(color(f"  [ERREUR] {message}"))


def print_warning(message):
    print(color(f"  [!] {message}"))


def print_info(message):
    print(color(f"  [i] {message}"))


def run_tool(entry, *, pause_after=True):
    print_header(entry.name)
    try:
        if not entry.available:
            print_error(f"Indisponible : {entry.unavailable_reason}")
            return
        for warning in entry.warnings:
            print_warning(warning)
        if entry.kind == "legacy":
            print_info("Compatibilité temporaire : outil historique interactif")
            entry.run_legacy()
        else:
            inputs = {}
            for param, prompt in entry.implementation.required_inputs.items():
                value = get_input(prompt + " (vide = annuler)")
                if not value:
                    print_info("Annulé")
                    return
                inputs[param] = value
            result = entry.implementation.run(**inputs)
            if result.get("success") is False or result.get("error"):
                print_error(result.get("error") or "Échec de l'outil")
            else:
                for key, value in result.get("data", result).items():
                    print_result(key, value)
        if pause_after:
            pause()
    except KeyboardInterrupt:
        print_info("Annulé")
    except EOFError:
        raise
    except Exception as exc:
        print_error(f"{type(exc).__name__}: {exc}")
