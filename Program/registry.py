"""Deterministic catalogue, including tools whose imports are unavailable."""
import importlib
import shutil
import sys
from dataclasses import dataclass, field
from typing import Any

from .catalogue import ALIASES, TOOL_SPECS
from .tools.base import BaseTool

CATEGORY_METADATA = {
    "NETWORK": {"name": "Network Tools", "description": "Réseau et analyse IP"},
    "OSINT": {"name": "OSINT Tools", "description": "Sources ouvertes"},
    "WEB": {"name": "Web Recon", "description": "HTTP et TLS"},
    "REPORTS": {"name": "Rapports & Export", "description": "Résultats locaux"},
    "DISCOVERY": {"name": "Discovery Lab", "description": "DNS et services"},
    "INTEL": {"name": "Intel & Forensics", "description": "IOC et fichiers"},
}
DEPENDENCIES = {
    "requests": "requests", "whois": "python-whois", "dns.resolver": "dnspython",
    "dns.query": "dnspython", "dns.zone": "dnspython", "PIL.Image": "Pillow",
    "bs4": "beautifulsoup4", "pystyle": "pystyle", "pypresence": "pypresence",
}
REQUIRED = {
    "whois_lookup": ("whois",), "image_metadata": ("PIL.Image",),
    "dns_lookup_suite": ("dns.resolver",),
    "dns_resolver_compare": ("dns.resolver",),
    "dns_zone_transfer_test": ("dns.resolver", "dns.query", "dns.zone"),
}
ENRICHMENTS = {
    "domain_osint": ("whois", "dns.resolver", "bs4"),
    "email_osint": ("dns.resolver",),
    "http_title_probe": ("bs4",),
    "url_recon": ("bs4",),
}


def dependency_error(module):
    try:
        importlib.import_module(module)
        return None
    except Exception as exc:
        # Never display arbitrary exception payloads containing URLs/credentials.
        return f"{DEPENDENCIES.get(module, module)} : import impossible ({type(exc).__name__})"


@dataclass
class ToolEntry:
    id: str
    name: str
    categories: tuple
    module: str
    entrypoint: str
    kind: str
    implementation: Any = field(default=None, repr=False)
    unavailable_reason: str | None = None
    warnings: list = field(default_factory=list)

    @property
    def available(self):
        return self.unavailable_reason is None

    def load(self):
        for module in REQUIRED.get(self.id, ()):
            error = dependency_error(module)
            if error:
                self.unavailable_reason = error
                return
        try:
            module = importlib.import_module(f"Program.tools.{self.module}")
            implementation = getattr(module, self.entrypoint)
            if self.kind == "base":
                implementation = implementation()
                if not isinstance(implementation, BaseTool):
                    raise TypeError("BaseTool required")
            elif self.kind != "legacy" or not callable(implementation):
                raise TypeError("interactive callable required")
            self.implementation = implementation
        except ModuleNotFoundError as exc:
            name = exc.name or self.module
            self.unavailable_reason = f"Module absent : {DEPENDENCIES.get(name, name)} ({name})"
            return
        except Exception as exc:
            self.unavailable_reason = f"{self.module}.{self.entrypoint} : chargement impossible ({type(exc).__name__})"
            return
        command = {"ping": "ping", "ping_sweep_cidr": "ping",
                   "traceroute": "tracert" if sys.platform == "win32" else "traceroute"}.get(self.id)
        if command and not shutil.which(command):
            self.unavailable_reason = f"Commande système absente : {command}"
        if self.id == "dns_records" and dependency_error("dns.resolver"):
            if not shutil.which("nslookup"):
                self.unavailable_reason = "dnspython et commande de repli nslookup absents"
            else:
                self.warnings.append("dnspython absent : repli historique nslookup")
        for module in ENRICHMENTS.get(self.id, ()):
            error = dependency_error(module)
            if error:
                self.warnings.append("Enrichissement indisponible : " + error)

    def run_legacy(self):
        """TEMPORARY: direct interactive call, no invented structured result."""
        if self.kind != "legacy" or not self.available:
            raise RuntimeError("Outil historique indisponible")
        self.implementation()


class ToolRegistry:
    def __init__(self, specs=TOOL_SPECS):
        self.tools = {}
        self.categories = {key: {**value, "tools": []} for key, value in CATEGORY_METADATA.items()}
        # Validate everything before importing anything; duplicates are errors.
        for spec in sorted(specs, key=lambda item: item["id"]):
            entry = ToolEntry(**{**spec, "categories": tuple(spec["categories"])})
            if entry.id in self.tools or entry.id in ALIASES:
                raise ValueError(f"Identifiant dupliqué ou réservé : {entry.id}")
            if not entry.categories or len(set(entry.categories)) != len(entry.categories):
                raise ValueError(f"Catégories invalides : {entry.id}")
            if any(cat not in self.categories for cat in entry.categories):
                raise ValueError(f"Catégorie inconnue : {entry.id}")
            self.tools[entry.id] = entry
        for entry in self.tools.values():
            entry.load()
            for category in entry.categories:
                self.categories[category]["tools"].append((entry.name, entry))

    def get(self, tool_id):
        return self.tools[ALIASES.get(tool_id, tool_id)]

    def get_categories(self):
        return self.categories


def legacy_category_tools(category):
    """Old category imports remain usable through the same dispatch as the CLI."""
    def callback(entry):
        def run():
            from .ui import run_tool
            return run_tool(entry, pause_after=False)
        return run
    return [(name, callback(entry)) for name, entry in CATEGORIES[category]["tools"]]


registry = ToolRegistry()
CATEGORIES = registry.get_categories()
