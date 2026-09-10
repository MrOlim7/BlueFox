import ipaddress
import requests
from Program.reliability import response_object
from typing import Any, Dict
from Program.tools.base import BaseTool
from Program.config import config

class IPLookupTool(BaseTool):
    @property
    def category(self) -> str:
        return "NETWORK"

    @property
    def name(self) -> str:
        return "IP Lookup"

    @property
    def description(self) -> str:
        return "Get detailed geographical and ISP information for an IP address."

    @property
    def required_inputs(self) -> Dict[str, str]:
        return {"ip": "Adresse IP"}

    def run(self, ip: str) -> Dict[str, Any]:
        try:
            ip = str(ipaddress.ip_address(ip))
            response = response_object(requests.get(
                f"http://ip-api.com/json/{ip}?fields=66846719", timeout=10
            ), "IP Lookup")
            if response.get("status") != "success":
                raise ValueError("IP Lookup: recherche indisponible ou statut invalide")
            if response.get("query") != ip:
                # Compare normalized IPv6 representations as well.
                if ipaddress.ip_address(response.get("query", "")) != ipaddress.ip_address(ip):
                    raise ValueError("IP Lookup: adresse de réponse incohérente")
            for key in ("country", "countryCode", "isp"):
                if not isinstance(response.get(key), str) or not response[key]:
                    raise ValueError(f"IP Lookup: champ {key} absent ou invalide")
            for key, limit in (("lat", 90), ("lon", 180)):
                value = response.get(key)
                if type(value) not in (int, float) or not -limit <= value <= limit:
                    raise ValueError(f"IP Lookup: champ {key} absent ou invalide")
            data = {"IP": ip, "Pays": f"{response['country']} ({response['countryCode']})"}
            fields = {
                "regionName": "Région", "city": "Ville", "zip": "Code Postal",
                "lat": "Latitude", "lon": "Longitude", "timezone": "Timezone",
                "isp": "ISP", "org": "Organisation", "as": "AS",
                "mobile": "Mobile", "proxy": "Proxy/VPN", "hosting": "Hosting",
            }
            missing = []
            for key, label in fields.items():
                expected = bool if key in ("mobile", "proxy", "hosting") else str
                if key in ("lat", "lon") or isinstance(response.get(key), expected):
                    data[label] = response[key]
                else:
                    missing.append(key)
            warnings = []
            if missing:
                warnings.append("Données primaires partielles : " + ", ".join(missing))
            api_key = config.get("ipgeo_api_key")
            if api_key:
                try:
                    enrichment = response_object(requests.get(
                        "https://api.ipgeolocation.io/ipgeo",
                        params={"apiKey": api_key, "ip": ip}, timeout=10
                    ), "IP Geolocation")
                    extra = {}
                    for key, label in (("continent_name", "Continent"), ("district", "District")):
                        if isinstance(enrichment.get(key), str) and enrichment[key]:
                            extra[label] = enrichment[key]
                    currency = enrichment.get("currency")
                    if isinstance(currency, dict) and isinstance(currency.get("name"), str) and currency["name"]:
                        extra["Monnaie"] = currency["name"]
                    if not extra or enrichment.get("error") or enrichment.get("message"):
                        raise ValueError("Enrichissement invalide")
                    data.update(extra)
                except (requests.RequestException, ValueError):
                    warnings.append("Enrichissement IP Geolocation indisponible")
            if warnings:
                data["Avertissements"] = warnings
            return {"success": True, "partial": bool(warnings), "data": data}
        except requests.RequestException:
            return {"success": False, "error": "IP Lookup: erreur réseau, résultat indisponible"}
        except ValueError as exc:
            return {"success": False, "error": str(exc)}


def run():
    """Temporary interactive entrypoint for historical callers."""
    from Program.registry import registry
    from Program.ui import run_tool
    return run_tool(registry.get("ip_lookup"), pause_after=False)
