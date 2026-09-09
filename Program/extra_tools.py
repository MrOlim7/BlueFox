import concurrent.futures
import hashlib
import ipaddress
import os
import socket
import subprocess
import time
from urllib.parse import urlparse, quote

import requests

from . import legacy_tools as core
from .version import __version__

try:
    import dns.query
    import dns.zone
    HAS_DNS_EXT = True
except Exception:
    HAS_DNS_EXT = False


def _http_headers():
    return {"User-Agent": f"BlueFox/{__version__}"}


def http_title_probe():
    url = core.normalize_url(core.get_input("URL cible"))
    if not url:
        return

    core.print_header(f"HTTP TITLE PROBE - {url}")
    data = {"url": url}

    try:
        start = time.time()
        r = requests.get(url, timeout=15, allow_redirects=True, headers=_http_headers())
        elapsed = round(time.time() - start, 3)
        parsed = urlparse(r.url)

        title = "N/A"
        if core.HAS_BS4:
            soup = core.BeautifulSoup(r.text, "html.parser")
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
        else:
            lower = r.text.lower()
            if "<title>" in lower and "</title>" in lower:
                title = r.text.split("<title>", 1)[1].split("</title>", 1)[0].strip()

        data.update({
            "status_code": r.status_code,
            "final_url": r.url,
            "response_time_s": elapsed,
            "title": title,
            "server": r.headers.get("Server", "N/A"),
            "content_type": r.headers.get("Content-Type", "N/A"),
        })

        core.print_result("Status", str(r.status_code))
        core.print_result("URL finale", r.url)
        core.print_result("Temps réponse", f"{elapsed}s")
        core.print_result("Titre", title)
        core.print_result("Server", r.headers.get("Server", "N/A"))
        core.print_result("Content-Type", r.headers.get("Content-Type", "N/A"))
        core.print_result("Hostname", parsed.netloc)

        core.ask_save(f"http_title_{parsed.netloc}", data)
    except Exception as e:
        core.print_error(f"Erreur: {e}")


def favicon_hash():
    url = core.normalize_url(core.get_input("URL cible"))
    if not url:
        return

    parsed = urlparse(url)
    icon_url = f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
    core.print_header(f"FAVICON HASH - {parsed.netloc}")

    try:
        r = requests.get(icon_url, timeout=15, headers=_http_headers())
        if r.status_code != 200 or not r.content:
            core.print_warning("favicon.ico introuvable")
            return

        hashes = {
            "MD5": hashlib.md5(r.content).hexdigest(),
            "SHA1": hashlib.sha1(r.content).hexdigest(),
            "SHA256": hashlib.sha256(r.content).hexdigest(),
        }
        data = {"favicon_url": icon_url, "hashes": hashes, "size": len(r.content)}

        core.print_result("URL", icon_url)
        for name, value in hashes.items():
            core.print_result(name, value)

        core.ask_save(f"favicon_{parsed.netloc}", data)
    except Exception as e:
        core.print_error(f"Erreur: {e}")


def dns_lookup_suite():
    domain = core.get_input("Domaine")
    if not domain:
        return
    if not core.HAS_DNS:
        core.print_error("dnspython est requis")
        return

    core.print_header(f"DNS LOOKUP SUITE - {domain}")
    record_types = ["A", "AAAA", "MX", "NS", "TXT", "CAA", "SOA", "CNAME"]
    data = {"domain": domain, "records": {}}

    for record_type in record_types:
        try:
            answers = core.dns.resolver.resolve(domain, record_type)
            values = [str(r) for r in answers]
            data["records"][record_type] = values
            for value in values:
                core.print_result(record_type, value)
        except Exception:
            continue

    core.ask_save(f"dns_suite_{domain}", data)


def dns_zone_transfer_test():
    domain = core.get_input("Domaine")
    if not domain:
        return
    if not (core.HAS_DNS and HAS_DNS_EXT):
        core.print_error("dnspython complet est requis pour ce test")
        return

    core.print_header(f"ZONE TRANSFER TEST - {domain}")
    data = {"domain": domain, "attempts": []}
    found = False

    try:
        ns_answers = core.dns.resolver.resolve(domain, "NS")
    except Exception as e:
        core.print_error(f"Impossible de récupérer les NS: {e}")
        return

    for ns in ns_answers:
        ns_host = str(ns.target).rstrip(".")
        try:
            ns_ip = socket.gethostbyname(ns_host)
            xfr = dns.query.xfr(ns_ip, domain, timeout=5)
            zone = dns.zone.from_xfr(xfr)
            records = []
            if zone:
                for name, node in zone.nodes.items():
                    records.append(str(name))
            data["attempts"].append({"ns": ns_host, "ip": ns_ip, "success": True, "records": records[:50]})
            core.print_success(f"AXFR possible via {ns_host} ({ns_ip})")
            found = True
        except Exception as e:
            data["attempts"].append({"ns": ns_host, "success": False, "error": str(e)})
            core.print_info(f"{ns_host}: refusé")

    if not found:
        core.print_success("Aucun transfert de zone ouvert détecté")
    core.ask_save(f"zone_transfer_{domain}", data)


def subdomain_resolver():
    domain = core.get_input("Domaine racine")
    if not domain:
        return

    raw = core.get_input("Sous-domaines à tester (séparés par virgules)")
    if not raw:
        return

    prefixes = [s.strip() for s in raw.split(",") if s.strip()]
    core.print_header(f"SUBDOMAIN RESOLVER - {domain}")

    results = {}

    def resolve(sub):
        target = f"{sub}.{domain}"
        try:
            ip = socket.gethostbyname(target)
            return target, ip
        except Exception:
            return target, "N/A"

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(32, max(4, len(prefixes)))) as executor:
        for target, ip in executor.map(resolve, prefixes):
            results[target] = ip
            core.print_result(target, ip)

    core.ask_save(f"subdomain_resolver_{domain}", results)


def ping_sweep_cidr():
    cidr = core.get_input("Réseau CIDR (ex: 192.168.1.0/24)")
    if not cidr:
        return

    core.print_header(f"PING SWEEP - {cidr}")
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except Exception as e:
        core.print_error(f"CIDR invalide: {e}")
        return

    hosts = list(network.hosts())
    if len(hosts) > 256:
        hosts = hosts[:256]
        core.print_warning("Limite appliquée à 256 hôtes pour garder l'outil réactif")

    data = {"cidr": cidr, "alive": []}

    def ping_host(ip):
        ip_str = str(ip)
        if os.name == "nt":
            cmd = ["ping", "-n", "1", "-w", "1000", ip_str]
        else:
            cmd = ["ping", "-c", "1", "-W", "1", ip_str]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                return ip_str
        except Exception:
            pass
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=32) as executor:
        for alive in executor.map(ping_host, hosts):
            if alive:
                data["alive"].append(alive)
                core.print_success(f"Hôte actif: {alive}")

    core.print_info(f"{len(data['alive'])} hôte(s) actif(s)")
    core.ask_save(f"ping_sweep_{cidr.replace('/', '_')}", data)


def banner_grabber():
    host = core.get_input("Hôte ou IP")
    if not host:
        return
    port = core.get_input("Port [80]")
    port = int(port) if port.strip() else 80

    core.print_header(f"BANNER GRABBER - {host}:{port}")
    try:
        with socket.create_connection((host, port), timeout=5) as sock:
            sock.settimeout(5)
            try:
                sock.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
            except Exception:
                pass
            try:
                banner = sock.recv(2048).decode(errors="ignore").strip()
            except Exception:
                banner = ""
        core.print_result("Banner", banner[:500] if banner else "N/A")
        core.ask_save(f"banner_{host}_{port}", {"host": host, "port": port, "banner": banner})
    except Exception as e:
        core.print_error(f"Erreur: {e}")


TOOLS = [
    ("HTTP Title Probe", http_title_probe),
    ("Favicon Hash", favicon_hash),
    ("DNS Lookup Suite", dns_lookup_suite),
    ("Zone Transfer Test", dns_zone_transfer_test),
    ("Subdomain Resolver", subdomain_resolver),
    ("Ping Sweep CIDR", ping_sweep_cidr),
    ("Banner Grabber", banner_grabber),
]
