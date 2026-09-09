import requests
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
        if not ip:
            raise ValueError("IP address is required")

        try:
            # Primary lookup via ip-api.com
            response = requests.get(f"http://ip-api.com/json/{ip}?fields=66846719", timeout=10).json()

            if response.get("status") == "fail":
                return {"success": False, "error": response.get("message", "API lookup failed")}

            data = {
                "IP": ip,
                "Pays": f"{response.get('country', 'N/A')} ({response.get('countryCode', '')})",
                "Région": response.get("regionName", "N/A"),
                "Ville": response.get("city", "N/A"),
                "Code Postal": response.get("zip", "N/A"),
                "Latitude": response.get("lat", "N/A"),
                "Longitude": response.get("lon", "N/A"),
                "Timezone": response.get("timezone", "N/A"),
                "ISP": response.get("isp", "N/A"),
                "Organisation": response.get("org", "N/A"),
                "AS": response.get("as", "N/A"),
                "Mobile": response.get("mobile", "N/A"),
                "Proxy/VPN": response.get("proxy", "N/A"),
                "Hosting": response.get("hosting", "N/A"),
            }

            # Optional enrichment via ipgeolocation.io
            api_key = config.get("ipgeo_api_key")
            if api_key:
                try:
                    r2 = requests.get(
                        f"https://api.ipgeolocation.io/ipgeo?apiKey={api_key}&ip={ip}",
                        timeout=10
                    ).json()
                    if r2.get("continent_name"):
                        data["Continent"] = r2.get("continent_name")
                    if r2.get("district"):
                        data["District"] = r2.get("district")
                    if r2.get("currency") and isinstance(r2["currency"], dict):
                        data["Monnaie"] = r2["currency"].get("name")
                except:
                    pass

            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": str(e)}


def run():
    """Temporary interactive entrypoint for historical callers."""
    from Program.registry import registry
    from Program.ui import run_tool
    return run_tool(registry.get("ip_lookup"), pause_after=False)
