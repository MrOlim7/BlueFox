import ipaddress
import re
from urllib.parse import urlparse, quote

from Program import legacy_tools as core


DOMAIN_RE = re.compile(r"^(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$")
HASH_RE = re.compile(r"^[a-fA-F0-9]{32}$|^[a-fA-F0-9]{40}$|^[a-fA-F0-9]{64}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def ip_type(value):
    try:
        return f"ipv{ipaddress.ip_address(value).version}"
    except ValueError:
        return None


def analyze(value):
    result = {"input": value, "type": "unknown"}
    host = None
    address_type = ip_type(value)
    if value.lower().startswith(("http://", "https://")):
        try:
            parsed = urlparse(value)
            host = parsed.hostname
            # Accessing port also validates its numeric bounds.
            parsed.port
            if (not host or any(c.isspace() for c in value)
                    or not (ip_type(host) or DOMAIN_RE.fullmatch(host))):
                raise ValueError("Nom d'hôte invalide")
        except ValueError:
            return result
        result.update(type="url", hostname=host)
    elif address_type:
        result["type"] = address_type
    elif EMAIL_RE.fullmatch(value):
        result["type"] = "email"
    elif HASH_RE.fullmatch(value):
        result["type"] = {32: "hash_md5", 40: "hash_sha1", 64: "hash_sha256"}[len(value)]
    elif DOMAIN_RE.fullmatch(value):
        result["type"] = "domain"
        host = value.lower()

    links = {}
    target = host or value
    encoded = quote(target, safe="")
    if result["type"] in ("ipv4", "ipv6") or (host and ip_type(host)):
        links = {
            "abuseipdb": f"https://www.abuseipdb.com/check/{encoded}",
            "shodan": f"https://www.shodan.io/host/{encoded}",
            "virustotal": f"https://www.virustotal.com/gui/ip-address/{encoded}",
        }
    elif host:
        links = {
            "virustotal": f"https://www.virustotal.com/gui/domain/{encoded}",
            "urlscan": f"https://urlscan.io/search/#domain:{encoded}",
            "shodan": f"https://www.shodan.io/search?query={encoded}",
        }
    elif result["type"].startswith("hash_"):
        links = {
            "virustotal": f"https://www.virustotal.com/gui/file/{value.lower()}",
            "malwarebazaar": f"https://bazaar.abuse.ch/browse.php?search={value.lower()}",
        }
    elif result["type"] == "email":
        links = {
            "hibp": f"https://haveibeenpwned.com/account/{encoded}",
            "intelx": f"https://intelx.io/?s={encoded}",
        }
    if links:
        result["links"] = links
    return result


def run():
    indicator = core.get_input("IOC (ip/domain/url/hash/email)")
    if not indicator:
        return
    result = analyze(indicator.strip())
    core.print_header("IOC ANALYZER")
    core.print_result("Type", result["type"])
    for label, url in result.get("links", {}).items():
        core.print_result(label, url)
    if result["type"] == "unknown":
        core.print_warning("IOC non reconnu ou invalide")
    core.ask_save("ioc_analyzer", result)
