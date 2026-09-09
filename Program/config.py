"""Shared configuration; only the local layer is persisted.

MutableMapping is a temporary compatibility interface for historical tools.
"""
import json
import os
import sys
import tempfile
from collections.abc import MutableMapping
from pathlib import Path

API_KEY_FIELDS = {
    "ipgeo_api_key": {"label": "IPGeolocation", "env": "IPGEO_API_KEY"},
    "abuseipdb_api_key": {"label": "AbuseIPDB", "env": "ABUSEIPDB_API_KEY"},
    "shodan_api_key": {"label": "Shodan", "env": "SHODAN_API_KEY"},
    "virustotal_api_key": {"label": "VirusTotal", "env": "VIRUSTOTAL_API_KEY"},
    "hunter_api_key": {"label": "Hunter.io", "env": "HUNTER_API_KEY"},
    "numverify_api_key": {"label": "NumVerify", "env": "NUMVERIFY_API_KEY"},
}
THEMES = ("blue", "cyan", "green", "red", "purple")
DEFAULT_CONFIG = {
    "client_id": "1305534641200959600", "ui_theme": "blue",
    "animations_enabled": True, "results_folder": "results", "max_workers": 200,
    **{key: "" for key in API_KEY_FIELDS},
}
ENV_FIELDS = {
    "ui_theme": "BLUEFOX_THEME", "results_folder": "BLUEFOX_RESULTS_FOLDER",
    "max_workers": "BLUEFOX_MAX_WORKERS", "animations_enabled": "BLUEFOX_ANIMATIONS",
    **{key: meta["env"] for key, meta in API_KEY_FIELDS.items()},
}
LEGACY_CONFIG_FILE = Path(__file__).parent / "bluefox_config.json"


def user_config_path():
    if os.getenv("BLUEFOX_CONFIG_FILE"):
        return Path(os.environ["BLUEFOX_CONFIG_FILE"]).expanduser().absolute()
    if sys.platform == "win32":
        root = Path(os.getenv("APPDATA", str(Path.home() / "AppData/Roaming")))
    elif sys.platform == "darwin":
        root = Path.home() / "Library/Application Support"
    else:
        root = Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return root / "bluefox" / "config.json"


def mask_secret(value):
    return "********" if value else "---"


def validate(key, value):
    if key not in DEFAULT_CONFIG:
        raise ValueError("Réglage inconnu")
    if key == "max_workers":
        if type(value) is not int or not 1 <= value <= 256:
            raise ValueError("max_workers doit être un entier entre 1 et 256")
    elif key == "animations_enabled":
        if type(value) is not bool:
            raise ValueError("animations_enabled doit être un booléen")
    elif not isinstance(value, str) or "\x00" in value:
        raise ValueError(f"{key} doit être une chaîne valide")
    elif key == "ui_theme" and value not in THEMES:
        raise ValueError("Thème inconnu")
    elif key == "results_folder" and not value.strip():
        raise ValueError("Le dossier de résultats ne peut pas être vide")
    return value


class ConfigManager(MutableMapping):
    def __init__(self, path=None, *, legacy_path=None, environ=None, overrides=None):
        self.path = Path(path).absolute() if path is not None else user_config_path()
        self.legacy_path = Path(legacy_path) if legacy_path is not None else LEGACY_CONFIG_FILE
        self.environ = dict(os.environ if environ is None else environ)
        self.local = {}
        self.environment = {}
        self.overrides = {}
        self.issues = []
        self.last_error = None
        self._unsafe_to_save = False
        self.load()
        self.set_overrides(overrides or {})

    def load(self):
        self.local.clear()
        self.environment.clear()
        self.issues.clear()
        self.last_error = None
        self._unsafe_to_save = False
        # An explicit environment path opts out of automatic legacy migration.
        migrate = not self.path.exists() and "BLUEFOX_CONFIG_FILE" not in self.environ
        source = self.legacy_path if migrate and self.legacy_path.exists() else self.path
        try:
            with source.open(encoding="utf-8") as stream:
                saved = json.load(stream)
            if not isinstance(saved, dict):
                raise ValueError("object required")
            # Preserve unknown/invalid local data; version belongs to code.
            self.local = {key: value for key, value in saved.items() if key != "version"}
            for key in DEFAULT_CONFIG:
                if key in self.local:
                    try:
                        validate(key, self.local[key])
                    except ValueError:
                        self.issues.append(f"Fichier : réglage invalide ({key}), défaut utilisé")
            if source == self.legacy_path and "results_folder" in self.local:
                folder = self.local["results_folder"]
                if isinstance(folder, str) and folder and not Path(folder).is_absolute():
                    self.local["results_folder"] = str((source.parent.parent / folder).resolve())
        except FileNotFoundError:
            pass
        except (OSError, ValueError, UnicodeError) as exc:
            self._unsafe_to_save = True
            self.issues.append(f"Configuration illisible ({type(exc).__name__}) : fichier conservé ; réparez-le avant de sauvegarder")
        for key, name in ENV_FIELDS.items():
            if name not in self.environ:
                continue
            try:
                value = self.environ[name]
                if key == "max_workers":
                    value = int(value)
                elif key == "animations_enabled":
                    value = {"1": True, "true": True, "0": False, "false": False}[value.lower()]
                self.environment[key] = validate(key, value)
            except (ValueError, KeyError, TypeError):
                self.issues.append(f"Environnement : {name} invalide, valeur ignorée")
        if source == self.legacy_path and not self._unsafe_to_save:
            if not self.save():
                self.issues.append("Migration non enregistrée : " + self.last_error)
            else:
                self.issues.append("Ancienne configuration copiée ; fichier original conservé")

    def set_overrides(self, values):
        self.overrides = {key: validate(key, value) for key, value in values.items()}

    def __getitem__(self, key):
        if key not in DEFAULT_CONFIG:
            raise KeyError(key)
        for layer in (self.overrides, self.environment, self.local):
            if key in layer:
                try:
                    return validate(key, layer[key])
                except ValueError:
                    continue
        return DEFAULT_CONFIG[key]

    def __setitem__(self, key, value):
        self.local[key] = validate(key, value)

    def __delitem__(self, key):
        self[key] = DEFAULT_CONFIG[key]

    def __iter__(self):
        return iter(DEFAULT_CONFIG)

    def __len__(self):
        return len(DEFAULT_CONFIG)

    def set(self, key, value):
        self[key] = value

    def clear(self):
        """Reset the local layer without iterating over undeletable defaults."""
        self.local.clear()

    def source(self, key):
        if key in self.overrides:
            return "option explicite"
        if key in self.environment:
            return "environnement"
        if key in self.local:
            try:
                validate(key, self.local[key])
                return "fichier local"
            except ValueError:
                pass
        return "défaut"

    def results_path(self):
        path = Path(self["results_folder"]).expanduser()
        return path if path.is_absolute() else self.path.parent / path

    def redact(self, value):
        text = str(value)
        for layer in (self.local, self.environment, self.overrides):
            for key in API_KEY_FIELDS:
                secret = layer.get(key)
                if isinstance(secret, str) and secret:
                    text = text.replace(secret, "[secret masqué]")
        return text

    def save(self):
        self.last_error = None
        if self._unsafe_to_save:
            self.last_error = "Configuration illisible : sauvegarde refusée pour préserver le fichier"
            return False
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix=".bluefox-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(self.local, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            return True
        except (OSError, ValueError, TypeError) as exc:
            detail = "droits insuffisants" if isinstance(exc, PermissionError) else type(exc).__name__
            self.last_error = f"Impossible de sauvegarder la configuration ({detail})"
            return False
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass


config = ConfigManager()
CONFIG = config  # Temporary dictionary-compatible facade; never a copy.
CONFIG_FILE = config.path
