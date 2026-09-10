# ============================================================
#  BlueFox historical tools — temporary v3 compatibility
#  À but éducatif uniquement
# ============================================================

import subprocess
import requests
import socket
import platform
import concurrent.futures
import atexit
import re
import os
import sys
import time
import json
import hashlib
import ssl
import csv
import base64
from datetime import datetime
from urllib.parse import urlparse, quote_plus, quote

# ============================================================
#  IMPORTS OPTIONNELS
# ============================================================
try:
    from pystyle import Colors, Colorate, Center
    HAS_PYSTYLE = True
except ImportError:
    HAS_PYSTYLE = False

try:
    from pypresence import Presence
    HAS_RPC = True
except ImportError:
    HAS_RPC = False

try:
    import whois as python_whois
    HAS_WHOIS = True
except ImportError:
    HAS_WHOIS = False

try:
    import dns.resolver
    HAS_DNS = True
except ImportError:
    HAS_DNS = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ============================================================
#  CONFIG
# ============================================================
from .config import API_KEY_FIELDS, CONFIG, CONFIG_FILE, config, mask_secret
from .version import __version__
from . import ui
from .reliability import response_object, host_bounds, port_range, parse_ports
from .result_storage import write_result, is_report, report_text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

THEME_PRESETS = {
    "blue": {"primary": "blue_to_cyan", "secondary": "blue_to_red"},
    "cyan": {"primary": "cyan_to_blue", "secondary": "cyan_to_red"},
    "green": {"primary": "green_to_cyan", "secondary": "green_to_yellow"},
    "red": {"primary": "red_to_yellow", "secondary": "red_to_blue"},
    "purple": {"primary": "purple_to_blue", "secondary": "purple_to_red"},
}


def load_local_config():
    return config.load()


def save_local_config():
    return config.save()


def set_ui_theme(theme_name):
    theme_name = (theme_name or "").strip().lower()
    if theme_name in THEME_PRESETS:
        CONFIG["ui_theme"] = theme_name
        return True
    return False


def _theme_color_slot(slot, fallback_attr):
    if not HAS_PYSTYLE:
        return None

    theme_name = CONFIG.get("ui_theme", "blue")
    preset = THEME_PRESETS.get(theme_name, THEME_PRESETS["blue"])
    attr_name = preset.get(slot, fallback_attr)
    color_value = getattr(Colors, attr_name, None)
    if color_value is None:
        color_value = getattr(Colors, fallback_attr, None)
    return color_value

# ============================================================
#  COULEURS & AFFICHAGE
# ============================================================
# Temporary UI aliases ensure both tool families use redaction and settings.
color = ui.color
color2 = ui.color
center = ui.center
clear = ui.clear
pause = ui.pause
print_header = ui.print_header
print_result = ui.print_result
print_success = ui.print_success
print_error = ui.print_error
print_info = ui.print_info
print_warning = ui.print_warning
get_input = ui.get_input
get_secret = ui.get_secret


def prompt_with_default(prompt, default=""):
    suffix = f" [{default}]" if default not in [None, ""] else ""
    value = input(color(f"  └─$ {prompt}{suffix}: ")).strip()
    return value if value else default


def normalize_url(value):
    if not value:
        return value
    if not value.startswith(("http://", "https://")):
        return "https://" + value
    return value


def intro_animation():
    frames = [
        "  [*] Booting BlueFox...",
        "  [/] Loading network modules...",
        "  [-] Loading OSINT modules...",
        "  [\\] Preparing interface...",
        "  [|] Initializing API config...",
        "  [>] Launching toolkit...",
    ]

    clear()
    for frame in frames:
        clear()
        print(color("\n" + " " * 10 + "__________"))
        print(color(" " * 10 + "/\\_\\_\\_\\_\\"))
        print(color(" " * 10 + "\\_/ BlueFox"))
        print(color(" " * 10 + "  " + frame))
        time.sleep(0.08)

    clear()
    if HAS_PYSTYLE:
        print(Colorate.Horizontal(Colors.blue_to_cyan, Center.XCenter(BANNER)))
    else:
        print(BANNER)
    print(color("  " + "=" * 60))
    print(color("  BlueFox is starting with a fresher interface and saved settings."))
    time.sleep(0.2)



# ============================================================
#  DISCORD RPC
# ============================================================
RPC = None
start_time = int(time.time())

def init_rpc():
    global RPC
    if HAS_RPC:
        try:
            RPC = Presence(CONFIG["client_id"])
            RPC.connect()
        except:
            RPC = None

def update_rpc(state, details):
    if RPC:
        try:
            RPC.update(
                state=state,
                details=details,
                large_image="large_image_name",
                small_image="logo_bluefox2",
                start=start_time
            )
        except:
            pass


def close_rpc():
    global RPC
    if RPC:
        try:
            if hasattr(RPC, "close"):
                RPC.close()
        except:
            pass
        finally:
            RPC = None


atexit.register(close_rpc)

# ============================================================
#  SAUVEGARDE DES RÉSULTATS
# ============================================================
def ensure_results_folder():
    os.makedirs(str(config.results_path()), exist_ok=True)

def save_result(filename, data, fmt="json"):
    try:
        filepath = write_result(config.results_path(), filename, data, fmt)
    except (OSError, ValueError, TypeError) as exc:
        print_error(f"Erreur sauvegarde: {exc}")
        return None
    print_success(f"Résultat sauvegardé: {filepath}")
    return filepath


def ask_save(filename, data):
    choice = get_input("Sauvegarder les résultats? (json/csv/txt/non)")
    if choice in ["json", "csv", "txt"]:
        save_result(filename, data, choice)
    elif choice not in ("", "non", "no", "n"):
        print_error(f"Format d'export inconnu : {choice}")

def ask_export_format():
    choice = get_input("Format d'export (json/csv/txt/non)")
    if choice in ["json", "csv", "txt"]:
        return choice
    if choice not in ("", "non", "no", "n"):
        print_error(f"Format d'export inconnu : {choice}")
    return None

# ============================================================
#  CATÉGORIE 1 : NETWORK TOOLS
# ============================================================

def ping_ip():
    ip = get_input("Adresse IP à ping")
    if not ip:
        return
    update_rpc("Ping IP", f"Ping de {ip}")
    print_header(f"PING - {ip}")
    try:
        if platform.system().lower() == "windows":
            result = subprocess.run(['ping', '-n', '4', ip], capture_output=True, text=True, timeout=15)
        else:
            result = subprocess.run(['ping', '-c', '4', ip], capture_output=True, text=True, timeout=15)
        print(color(result.stdout))
        if result.returncode != 0:
            print_error("Hôte injoignable ou timeout.")
    except subprocess.TimeoutExpired:
        print_error("Timeout expiré.")
    except Exception as e:
        print_error(f"Erreur: {e}")

def ip_lookup():
    ip = get_input("Adresse IP")
    if not ip:
        return
    update_rpc("IP Lookup", f"Recherche {ip}")
    print_header(f"IP INFORMATION - {ip}")
    
    from .tools.ip_lookup import IPLookupTool
    result = IPLookupTool().run(ip=ip)
    if not result["success"]:
        print_error(result["error"])
        return
    for key, value in result["data"].items():
        print_result(key, str(value))
    ask_save(f"ip_lookup_{ip}", result["data"])


def traceroute():
    ip = get_input("Adresse IP/Domaine")
    if not ip:
        return
    update_rpc("Traceroute", f"Trace {ip}")
    print_header(f"TRACEROUTE - {ip}")
    try:
        if platform.system().lower() == "windows":
            cmd = ['tracert', '-h', '30', '-w', '3000', ip]
        else:
            cmd = ['traceroute', '-m', '30', '-w', '3', ip]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        print(color(result.stdout))
    except subprocess.TimeoutExpired:
        print_error("Timeout expiré.")
    except FileNotFoundError:
        print_error("Commande traceroute non trouvée.")
    except Exception as e:
        print_error(f"Erreur: {e}")

def reverse_dns():
    ip = get_input("Adresse IP")
    if not ip:
        return
    print_header(f"REVERSE DNS - {ip}")
    try:
        hostname = socket.gethostbyaddr(ip)
        data = {
            "IP": ip,
            "Hostname": hostname[0],
            "Aliases": ", ".join(hostname[1]) if hostname[1] else "Aucun",
            "Addresses": ", ".join(hostname[2])
        }
        for k, v in data.items():
            print_result(k, v)
        ask_save(f"reverse_dns_{ip}", data)
    except socket.herror:
        print_error("Aucun enregistrement DNS inverse trouvé.")
    except Exception as e:
        print_error(f"Erreur: {e}")

def port_scanner():
    ip = get_input("Adresse IP")
    if not ip:
        return
    
    print_info("Modes: 1) Rapide (top 100) | 2) Standard (1-1024) | 3) Complet (1-65535) | 4) Custom")
    mode = get_input("Mode")
    
    COMMON_PORTS = {
        21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
        80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
        993: "IMAPS", 995: "POP3S", 3306: "MySQL", 3389: "RDP",
        5432: "PostgreSQL", 5900: "VNC", 6379: "Redis", 8080: "HTTP-Alt",
        8443: "HTTPS-Alt", 27017: "MongoDB"
    }
    
    TOP_100 = [20,21,22,23,25,53,80,110,111,135,139,143,443,445,465,587,
               993,995,1433,1434,1521,1723,2049,2082,2083,2086,2087,3306,
               3389,5432,5900,5985,5986,6379,8080,8443,8888,9090,9200,27017]
    
    if mode == "1":
        ports = TOP_100
    elif mode == "2":
        ports = list(range(1, 1025))
    elif mode == "3":
        ports = list(range(1, 65536))
    elif mode == "4":
        try:
            ports = port_range(get_input("Port début"), get_input("Port fin"))
        except ValueError as exc:
            print_error(str(exc))
            return
    else:
        ports = TOP_100
    
    update_rpc("Port Scan", f"Scan de {ip}")
    print_header(f"PORT SCAN - {ip} ({len(ports)} ports)")
    
    open_ports = []
    
    def scan_single(port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((ip, port))
            sock.close()
            if result == 0:
                service = COMMON_PORTS.get(port, "Unknown")
                return (port, service)
        except:
            pass
        return None
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=CONFIG["max_workers"]) as executor:
            futures = {executor.submit(scan_single, p): p for p in ports}
            done = 0
            total = len(ports)
            for future in concurrent.futures.as_completed(futures):
                done += 1
                if done % 500 == 0 or done == total:
                    pct = int(done / total * 100)
                    sys.stdout.write(color(f"\r  [i] Progression: {pct}% ({done}/{total})"))
                    sys.stdout.flush()
                result = future.result()
                if result:
                    open_ports.append(result)
                    print(color(f"\n  ║ Port {result[0]:<6} OPEN  ({result[1]})"))
        
        print(color(f"\n\n  {'─' * 40}"))
        print_success(f"{len(open_ports)} port(s) ouvert(s) trouvé(s)")
        
        if open_ports:
            data = {str(p[0]): p[1] for p in sorted(open_ports)}
            ask_save(f"portscan_{ip}", data)
    
    except Exception as e:
        print_error(f"Erreur: {e}")

def whois_lookup():
    target = get_input("Domaine ou IP")
    if not target:
        return
    print_header(f"WHOIS - {target}")
    
    if HAS_WHOIS:
        try:
            result = python_whois.whois(target)
            data = {}
            for key, value in result.items():
                if value:
                    if isinstance(value, list):
                        data[key] = ", ".join(str(v) for v in value)
                    else:
                        data[key] = str(value)
                    print_result(key, data[key])
            ask_save(f"whois_{target}", data)
        except Exception as e:
            print_error(f"Erreur WHOIS: {e}")
    else:
        print_error("Module python-whois non installé (pip install python-whois)")

def blacklist_check():
    ip = get_input("Adresse IP")
    if not ip:
        return
    print_header(f"BLACKLIST CHECK - {ip}")
    
    if CONFIG["abuseipdb_api_key"]:
        try:
            r = requests.get(
                f"https://api.abuseipdb.com/api/v2/check",
                params={"ipAddress": ip, "maxAgeInDays": 90},
                headers={"Key": CONFIG["abuseipdb_api_key"], "Accept": "application/json"},
                timeout=10
            ).json()
            
            d = r.get("data", {})
            data = {
                "IP": d.get("ipAddress"),
                "Public": d.get("isPublic"),
                "Abuse Score": f"{d.get('abuseConfidenceScore', 0)}%",
                "Pays": d.get("countryCode"),
                "ISP": d.get("isp"),
                "Domain": d.get("domain"),
                "Total Reports": d.get("totalReports"),
                "Whitelisted": d.get("isWhitelisted"),
            }
            for k, v in data.items():
                print_result(k, str(v))
            ask_save(f"blacklist_{ip}", data)
        except Exception as e:
            print_error(f"Erreur: {e}")
    else:
        # Fallback sans API
        try:
            r = requests.get(f"https://ip-api.com/json/{ip}?fields=proxy,hosting", timeout=10).json()
            print_result("Proxy/VPN", str(r.get("proxy", "N/A")))
            print_result("Hosting", str(r.get("hosting", "N/A")))
            print_warning("Pour un check complet, ajoutez ABUSEIPDB_API_KEY")
        except Exception as e:
            print_error(f"Erreur: {e}")

def dns_records():
    domain = get_input("Domaine")
    if not domain:
        return
    print_header(f"DNS RECORDS - {domain}")
    
    if HAS_DNS:
        record_types = ['A', 'AAAA', 'MX', 'NS', 'TXT', 'SOA', 'CNAME', 'SRV']
        data = {}
        for rtype in record_types:
            try:
                answers = dns.resolver.resolve(domain, rtype)
                records = [str(r) for r in answers]
                data[rtype] = records
                for r in records:
                    print_result(rtype, r)
            except dns.resolver.NoAnswer:
                pass
            except dns.resolver.NXDOMAIN:
                print_error(f"Domaine {domain} introuvable")
                return
            except Exception:
                pass
        ask_save(f"dns_{domain}", data)
    else:
        # Fallback avec nslookup
        try:
            result = subprocess.run(['nslookup', '-type=any', domain], capture_output=True, text=True, timeout=15)
            print(color(result.stdout))
        except Exception as e:
            print_error(f"Erreur: {e}")

def asn_info():
    ip = get_input("Adresse IP")
    if not ip:
        return
    print_header(f"ASN INFORMATION - {ip}")
    try:
        r = requests.get(f"https://api.iptoasn.com/v1/as/ip/{ip}", timeout=10).json()
        data = {
            "IP Range": r.get("announced", "N/A"),
            "ASN": r.get("as_number", "N/A"),
            "Organisation": r.get("as_description", "N/A"),
            "Pays": r.get("as_country_code", "N/A"),
        }
        for k, v in data.items():
            print_result(k, str(v))
        ask_save(f"asn_{ip}", data)
    except Exception as e:
        print_error(f"Erreur: {e}")

def my_ip_info():
    print_header("MON IP / CONFIGURATION RÉSEAU")
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print_result("Hostname", hostname)
    print_result("IP Locale", local_ip)
    
    try:
        public_ip = requests.get("https://api.ipify.org", timeout=5).text
        print_result("IP Publique", public_ip)
    except:
        print_result("IP Publique", "Impossible de récupérer")
    
    print(color(f"\n  {'─' * 40}"))
    _plat = platform.system()
    if _plat == "Windows":
        result = os.popen("ipconfig").read()
    elif _plat == "Darwin":
        # macOS — use native ifconfig
        result = os.popen("ifconfig 2>/dev/null").read()
    else:
        # Linux
        result = os.popen("ifconfig 2>/dev/null || ip addr 2>/dev/null").read()
    print(color(result))

def ssl_cert_info():
    domain = get_input("Domaine (sans https://)")
    if not domain:
        return
    print_header(f"CERTIFICAT SSL - {domain}")
    try:
        import ssl as ssl_lib
        context = ssl_lib.create_default_context()
        conn = context.wrap_socket(socket.socket(), server_hostname=domain)
        conn.settimeout(10)
        conn.connect((domain, 443))
        cert = conn.getpeercert()
        conn.close()
        
        data = {
            "Sujet": str(dict(x[0] for x in cert.get("subject", []))),
            "Émetteur": str(dict(x[0] for x in cert.get("issuer", []))),
            "Version": cert.get("version"),
            "Numéro de série": cert.get("serialNumber"),
            "Valide depuis": cert.get("notBefore"),
            "Valide jusqu'à": cert.get("notAfter"),
            "Alt Names": str(cert.get("subjectAltName", [])),
        }
        for k, v in data.items():
            print_result(k, str(v))
        ask_save(f"ssl_{domain}", data)
    except Exception as e:
        print_error(f"Erreur: {e}")

def http_headers():
    url = get_input("URL complète (https://...)")
    if not url:
        return
    if not url.startswith("http"):
        url = "https://" + url
    print_header(f"HTTP HEADERS - {url}")
    try:
        r = requests.head(url, timeout=10, allow_redirects=True)
        data = dict(r.headers)
        for k, v in data.items():
            print_result(k, v)
        
        # Analyse sécurité basique
        print(color(f"\n  {'─' * 40}"))
        print_info("Analyse de sécurité:")
        security_headers = {
            "Strict-Transport-Security": "HSTS",
            "Content-Security-Policy": "CSP",
            "X-Frame-Options": "Clickjacking Protection",
            "X-Content-Type-Options": "MIME Sniffing Protection",
            "X-XSS-Protection": "XSS Protection",
            "Referrer-Policy": "Referrer Policy",
        }
        for header, name in security_headers.items():
            if header.lower() in [h.lower() for h in data.keys()]:
                print_success(f"{name}: Présent ✓")
            else:
                print_warning(f"{name}: Absent ✗")
        
        ask_save(f"headers_{urlparse(url).netloc}", data)
    except Exception as e:
        print_error(f"Erreur: {e}")

def subnet_calculator():
    cidr = get_input("Réseau CIDR (ex: 192.168.1.0/24)")
    if not cidr:
        return
    print_header(f"SUBNET CALCULATOR - {cidr}")
    try:
        import ipaddress
        network = ipaddress.ip_network(cidr, strict=False)
        usable, first, last = host_bounds(network)
        data = {
            "Adresse réseau": str(network.network_address),
            "Broadcast": str(network.broadcast_address),
            "Masque": str(network.netmask),
            "Wildcard": str(network.hostmask),
            "Préfixe": f"/{network.prefixlen}",
            "Nombre d'hôtes": usable,
            "Première IP": first,
            "Dernière IP": last,
            "Privé": str(network.is_private),
        }
        for k, v in data.items():
            print_result(k, str(v))
        ask_save(f"subnet_{cidr.replace('/', '_')}", data)
    except Exception as e:
        print_error(f"Erreur: {e}")


def tcp_connect_test():
    host = get_input("Hôte ou IP")
    if not host:
        return

    raw_ports = get_input("Ports (ex: 22,80,443 ou 20-30)")
    if not raw_ports:
        return

    try:
        ports = parse_ports(raw_ports)
    except ValueError as exc:
        print_error(f"Ports invalides : {exc}")
        return

    print_header(f"TCP CONNECT TEST - {host}")
    print_info(f"{len(ports)} port(s) à tester")

    results = {"host": host, "ports": {}}

    def check_port(port):
        try:
            with socket.create_connection((host, port), timeout=2):
                return port, "open"
        except Exception:
            return port, "closed"

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(64, max(4, len(ports)))) as executor:
            for port, status in executor.map(check_port, ports):
                results["ports"][port] = status
                if status == "open":
                    print_success(f"Port {port} ouvert")
                else:
                    print_info(f"Port {port} fermé")

        ask_save(f"tcp_test_{host}", results)
    except Exception as e:
        print_error(f"Erreur: {e}")


def url_recon():
    url = normalize_url(get_input("URL cible"))
    if not url:
        return

    print_header(f"URL RECON - {url}")
    headers_req = {
        "User-Agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) BlueFox/{__version__}"
    }
    data = {"url": url}

    try:
        start = time.time()
        r = requests.get(url, timeout=15, headers=headers_req, allow_redirects=True)
        elapsed = round(time.time() - start, 3)
        final_url = r.url
        parsed = urlparse(final_url)

        data.update({
            "status_code": r.status_code,
            "final_url": final_url,
            "response_time_s": elapsed,
            "content_type": r.headers.get("Content-Type", "N/A"),
            "server": r.headers.get("Server", "N/A"),
            "content_length": len(r.text),
            "redirects": len(r.history),
        })

        print_result("Status", str(r.status_code))
        print_result("URL finale", final_url)
        print_result("Temps réponse", f"{elapsed}s")
        print_result("Server", r.headers.get("Server", "N/A"))
        print_result("Content-Type", r.headers.get("Content-Type", "N/A"))
        print_result("Taille contenu", str(len(r.text)))
        print_result("Redirections", str(len(r.history)))

        if HAS_BS4:
            soup = BeautifulSoup(r.text, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else "N/A"
            forms = soup.find_all("form")
            links = soup.find_all("a", href=True)
            metas = soup.find_all("meta")

            data["title"] = title
            data["forms_count"] = len(forms)
            data["links_count"] = len(links)
            data["meta_count"] = len(metas)

            print_result("Titre", title)
            print_result("Formulaires", str(len(forms)))
            print_result("Liens", str(len(links)))
            print_result("Meta tags", str(len(metas)))

        print(color(f"\n  {'─' * 40}"))
        print_info("Raccourcis d'analyse:")
        print_result("Domain", parsed.netloc)
        print_result("Wayback", f"https://web.archive.org/web/*/{parsed.netloc}")
        print_result("BuiltWith", f"https://builtwith.com/{parsed.netloc}")
        print_result("SecurityHeaders", f"https://securityheaders.com/?q={parsed.netloc}")

        ask_save(f"url_recon_{parsed.netloc}", data)
    except Exception as e:
        print_error(f"Erreur: {e}")


def robots_sitemap_audit():
    target = normalize_url(get_input("Domaine ou URL"))
    if not target:
        return

    parsed = urlparse(target)
    base = f"{parsed.scheme}://{parsed.netloc}"
    print_header(f"WEB SURFACE - {parsed.netloc}")

    paths = {
        "robots.txt": f"{base}/robots.txt",
        "sitemap.xml": f"{base}/sitemap.xml",
        "security.txt": f"{base}/.well-known/security.txt",
    }
    data = {"base": base, "files": {}}

    for label, file_url in paths.items():
        try:
            r = requests.get(file_url, timeout=10, headers={"User-Agent": f"BlueFox/{__version__}"})
            exists = r.status_code < 400 and len(r.text.strip()) > 0
            data["files"][label] = {
                "status_code": r.status_code,
                "exists": exists,
                "size": len(r.text),
            }
            if exists:
                print_success(f"{label}: disponible ({len(r.text)} chars)")
                if label == "robots.txt":
                    lines = [line.strip() for line in r.text.splitlines() if line.strip() and not line.startswith("#")]
                    for line in lines[:12]:
                        print_result("robots", line)
            else:
                print_warning(f"{label}: absent ou vide ({r.status_code})")
        except Exception as e:
            data["files"][label] = {"error": str(e)}
            print_warning(f"{label}: erreur")

    print(color(f"\n  {'─' * 40}"))
    print_info("Liens rapides:")
    print_result("robots.txt", paths["robots.txt"])
    print_result("sitemap.xml", paths["sitemap.xml"])
    print_result("security.txt", paths["security.txt"])

    ask_save(f"websurface_{parsed.netloc}", data)

# ============================================================
#  CATÉGORIE 2 : OSINT TOOLS
# ============================================================

def username_lookup():
    username = get_input("Nom d'utilisateur à rechercher")
    if not username:
        return
    raw_username = username.strip()
    safe_username = quote(raw_username, safe="")
    update_rpc("Username Lookup", f"Recherche de {username}")
    print_header(f"USERNAME LOOKUP - {username}")
    
    platforms = {
        "GitHub": f"https://github.com/{safe_username}",
        "Twitter/X": f"https://x.com/{safe_username}",
        "Instagram": f"https://instagram.com/{safe_username}",
        "Reddit": f"https://reddit.com/user/{safe_username}",
        "TikTok": f"https://tiktok.com/@{safe_username}",
        "YouTube": f"https://youtube.com/@{safe_username}",
        "Twitch": f"https://twitch.tv/{safe_username}",
        "Pinterest": f"https://pinterest.com/{safe_username}",
        "Spotify": f"https://open.spotify.com/user/{safe_username}",
        "SoundCloud": f"https://soundcloud.com/{safe_username}",
        "Medium": f"https://medium.com/@{safe_username}",
        "DeviantArt": f"https://deviantart.com/{safe_username}",
        "Flickr": f"https://flickr.com/people/{safe_username}",
        "Vimeo": f"https://vimeo.com/{safe_username}",
        "GitLab": f"https://gitlab.com/{safe_username}",
        "Bitbucket": f"https://bitbucket.org/{safe_username}",
        "Steam": f"https://steamcommunity.com/id/{safe_username}",
        "Xbox Gamertag": f"https://xboxgamertag.com/search/{safe_username}",
        "Keybase": f"https://keybase.io/{safe_username}",
        "About.me": f"https://about.me/{safe_username}",
        "Patreon": f"https://patreon.com/{safe_username}",
        "Dribbble": f"https://dribbble.com/{safe_username}",
        "Behance": f"https://behance.net/{safe_username}",
        "HackerOne": f"https://hackerone.com/{safe_username}",
        "BugCrowd": f"https://bugcrowd.com/{safe_username}",
        "Replit": f"https://replit.com/@{safe_username}",
        "Roblox (approx)": f"https://www.roblox.com/search/users?keyword={quote(raw_username)}",
        "Minecraft (NameMC)": f"https://namemc.com/profile/{safe_username}",
        "Chess.com": f"https://chess.com/member/{safe_username}",
        "Lichess": f"https://lichess.org/@/{safe_username}",
        "Telegram (approx)": f"https://t.me/{safe_username}",
        "Snapchat": f"https://snapchat.com/add/{safe_username}",
        "Cash App": f"https://cash.app/${safe_username}",
        "MyAnimeList": f"https://myanimelist.net/profile/{safe_username}",
        "AniList": f"https://anilist.co/user/{safe_username}",
        "NPM": f"https://npmjs.com/~{safe_username}",
        "PyPI": f"https://pypi.org/user/{safe_username}",
        "Docker Hub": f"https://hub.docker.com/u/{safe_username}",
        "Gravatar": f"https://gravatar.com/{safe_username}",
        "Linktree": f"https://linktr.ee/{safe_username}",
    }
    
    found = {}
    not_found = []
    errors = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    def check_platform(name, url):
        try:
            r = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
            if r.status_code in [403, 429, 451]:
                return (name, url, f"BLOCKED_{r.status_code}")
            if r.status_code == 200:
                if r.url.endswith("/"):
                    lower_text = r.text.lower()
                    if "not found" in lower_text or "doesn't exist" in lower_text or \
                       "page not found" in lower_text or "user not found" in lower_text or \
                       "no results" in lower_text:
                        return (name, url, "NOT_FOUND")
                return (name, url, "FOUND")
            elif r.status_code == 404:
                return (name, url, "NOT_FOUND")
            else:
                return (name, url, f"STATUS_{r.status_code}")
        except requests.Timeout:
            return (name, url, "TIMEOUT")
        except Exception:
            return (name, url, "ERROR")
    
    total = len(platforms)
    done = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_platform, n, u): n for n, u in platforms.items()}
        for future in concurrent.futures.as_completed(futures):
            done += 1
            sys.stdout.write(color(f"\r  [i] Progression: {done}/{total}"))
            sys.stdout.flush()
            
            name, url, status = future.result()
            if status == "FOUND":
                found[name] = url
            elif status == "NOT_FOUND":
                not_found.append(name)
            else:
                errors.append((name, status))
    
    print(color(f"\n\n  {'─' * 50}"))
    print_success(f"TROUVÉS ({len(found)}):")
    for name, url in sorted(found.items()):
        print(color(f"  ║ ✓ {name:<25} → {url}"))
    
    if errors:
        print(color(f"\n  {'─' * 50}"))
        print_warning(f"INCERTAINS ({len(errors)}):")
        for name, status in sorted(errors):
            print(color(f"  ║ ? {name:<25} → {status}"))
    
    print(color(f"\n  {'─' * 50}"))
    print_info(f"Non trouvés: {len(not_found)} plateformes")
    
    ask_save(f"username_{raw_username}", {"found": found, "not_found": not_found, "errors": dict(errors)})

def email_osint():
    email = get_input("Adresse email")
    if not email:
        return
    print_header(f"EMAIL OSINT - {email}")
    
    data = {"email": email}
    
    # 1. Validation format
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(email_regex, email):
        print_success("Format valide")
    else:
        print_error("Format invalide")
        return
    
    # 2. Vérification MX du domaine
    domain = email.split("@")[1]
    data["domain"] = domain
    
    if HAS_DNS:
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_list = [str(r.exchange) for r in mx_records]
            data["mx_records"] = mx_list
            print_result("MX Records", ", ".join(mx_list))
            print_success("Le domaine accepte les emails")
        except:
            print_warning("Pas de MX record trouvé")
    
    # 3. HaveIBeenPwned (info seulement)
    print_info("Vérification HaveIBeenPwned...")
    try:
        # API v3 nécessite une clé payante, on utilise le hash
        sha1 = hashlib.sha1(email.encode()).hexdigest().upper()
        data["sha1_hash"] = sha1
        print_result("SHA1 Hash", sha1)
    except:
        pass
    
    # 4. Gravatar check
    try:
        email_hash = hashlib.md5(email.lower().strip().encode()).hexdigest()
        gravatar_url = f"https://gravatar.com/avatar/{email_hash}?d=404"
        r = requests.get(gravatar_url, timeout=5)
        if r.status_code == 200:
            data["gravatar"] = f"https://gravatar.com/{email_hash}"
            print_success(f"Gravatar trouvé: https://gravatar.com/{email_hash}")
        else:
            print_info("Pas de Gravatar")
    except:
        pass
    
    # 5. GitHub email search
    try:
        r = requests.get(f"https://api.github.com/search/users?q={email}+in:email", timeout=10).json()
        if r.get("total_count", 0) > 0:
            for user in r["items"][:5]:
                print_success(f"GitHub: {user['login']} → {user['html_url']}")
                data[f"github_{user['login']}"] = user['html_url']
        else:
            print_info("Aucun profil GitHub trouvé")
    except:
        pass
    
    # 6. Hunter.io si clé dispo
    if CONFIG["hunter_api_key"]:
        try:
            r = requests.get(
                f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={CONFIG['hunter_api_key']}",
                timeout=10
            ).json()
            d = r.get("data", {})
            print_result("Statut", d.get("status"))
            print_result("Score", str(d.get("score")))
            print_result("Jetable", str(d.get("disposable")))
            print_result("Webmail", str(d.get("webmail")))
            data.update(d)
        except:
            pass
    
    # 7. Services connus par domaine
    known_providers = {
        "gmail.com": "Google", "yahoo.com": "Yahoo", "outlook.com": "Microsoft",
        "hotmail.com": "Microsoft", "protonmail.com": "ProtonMail", "icloud.com": "Apple",
        "aol.com": "AOL", "mail.ru": "Mail.ru", "yandex.com": "Yandex",
    }
    provider = known_providers.get(domain)
    if provider:
        data["provider"] = provider
        print_result("Fournisseur", provider)
    
    ask_save(f"email_{email.replace('@','_at_')}", data)

def phone_osint():
    phone = get_input("Numéro de téléphone (format international: +33...)")
    if not phone:
        return
    print_header(f"PHONE OSINT - {phone}")
    
    data = {"phone": phone}
    
    # Analyse du format
    phone_clean = re.sub(r'[^0-9+]', '', phone)
    data["cleaned"] = phone_clean
    
    # Détection pays par indicatif
    country_codes = {
        "+1": "États-Unis/Canada", "+33": "France", "+44": "Royaume-Uni",
        "+49": "Allemagne", "+34": "Espagne", "+39": "Italie",
        "+81": "Japon", "+86": "Chine", "+91": "Inde",
        "+7": "Russie", "+55": "Brésil", "+61": "Australie",
        "+32": "Belgique", "+41": "Suisse", "+212": "Maroc",
        "+213": "Algérie", "+216": "Tunisie", "+90": "Turquie",
        "+351": "Portugal", "+31": "Pays-Bas", "+48": "Pologne",
        "+46": "Suède", "+47": "Norvège", "+45": "Danemark",
        "+358": "Finlande", "+352": "Luxembourg",
    }
    
    detected_country = None
    for code, country in sorted(country_codes.items(), key=lambda x: -len(x[0])):
        if phone_clean.startswith(code):
            detected_country = country
            data["country"] = country
            data["country_code"] = code
            print_result("Pays", f"{country} ({code})")
            break
    
    if not detected_country:
        print_warning("Indicatif pays non reconnu")
    
    # Détection opérateur (France)
    if phone_clean.startswith("+33"):
        fr_number = phone_clean[3:]
        fr_operators = {
            "06": {"01": "Orange", "07": "Orange", "08": "SFR", "09": "SFR",
                   "10": "Bouygues", "11": "Bouygues", "20": "Bouygues",
                   "50": "Free", "51": "Free", "60": "Orange"},
            "07": {"01": "Orange", "30": "Free", "50": "Free", "80": "Bouygues"}
        }
        prefix2 = fr_number[:2]
        prefix4 = fr_number[:4]
        print_result("Numéro national", f"0{fr_number}")
        print_result("Type", "Mobile" if prefix2 in ["06", "07"] else "Fixe" if prefix2 in ["01","02","03","04","05"] else "Autre")
    
    # NumVerify (gratuit, limité)
    if CONFIG.get("numverify_api_key"):
        try:
            r = requests.get(
                f"http://apilayer.net/api/validate?access_key={CONFIG['numverify_api_key']}&number={phone_clean}",
                timeout=10
            ).json()
            if r.get("valid") is not None:
                print_result("Valide", str(r.get("valid")))
                print_result("Type de ligne", r.get("line_type", "N/A"))
                print_result("Opérateur", r.get("carrier", "N/A"))
                print_result("Localisation", r.get("location", "N/A"))
        except:
            pass
    else:
        print_warning("Ajoutez NUMVERIFY_API_KEY pour enrichir cette analyse")
    
    print(color(f"\n  {'─' * 40}"))
    print_info("Recherche sur les annuaires publics:")
    print_result("Pages Blanches", f"https://www.pagesjaunes.fr/annuaire/cherchertous?quoiqui={phone_clean}")
    print_result("TrueCaller", f"https://www.truecaller.com/search/fr/{phone_clean}")
    print_result("Sync.me", f"https://sync.me/search/?q={phone_clean}")
    print_result("NumeroInverse", f"https://www.numeroinverse.fr/numero/{phone_clean}")
    
    data["links"] = {
        "pages_blanches": f"https://www.pagesjaunes.fr/annuaire/cherchertous?quoiqui={phone_clean}",
        "truecaller": f"https://www.truecaller.com/search/fr/{phone_clean}",
    }
    
    ask_save(f"phone_{phone_clean}", data)

def domain_osint():
    domain = get_input("Nom de domaine (ex: example.com)")
    if not domain:
        return
    update_rpc("Domain OSINT", f"Analyse de {domain}")
    print_header(f"DOMAIN OSINT - {domain}")
    
    data = {"domain": domain}
    
    # 1. WHOIS
    if HAS_WHOIS:
        try:
            w = python_whois.whois(domain)
            whois_data = {}
            important_fields = ["registrar", "creation_date", "expiration_date", "updated_date",
                              "name_servers", "status", "emails", "name", "org", "address",
                              "city", "state", "country"]
            for field in important_fields:
                val = w.get(field)
                if val:
                    if isinstance(val, list):
                        val = ", ".join(str(v) for v in val)
                    whois_data[field] = str(val)
                    print_result(f"WHOIS {field}", str(val))
            data["whois"] = whois_data
        except Exception as e:
            print_warning(f"WHOIS échoué: {e}")
    
    # 2. DNS Records
    print(color(f"\n  {'─' * 40}"))
    print_info("DNS Records:")
    if HAS_DNS:
        dns_data = {}
        for rtype in ['A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME']:
            try:
                answers = dns.resolver.resolve(domain, rtype)
                records = [str(r) for r in answers]
                dns_data[rtype] = records
                for r in records:
                    print_result(rtype, r)
            except:
                pass
        data["dns"] = dns_data
    
    # 3. IP du domaine
    try:
        ip = socket.gethostbyname(domain)
        data["ip"] = ip
        print_result("IP", ip)
    except:
        pass
    
    # 4. HTTP Info
    print(color(f"\n  {'─' * 40}"))
    print_info("HTTP Info:")
    for scheme in ["https", "http"]:
        try:
            r = requests.get(f"{scheme}://{domain}", timeout=10, allow_redirects=True, 
                           headers={"User-Agent": "Mozilla/5.0"})
            data["http_status"] = r.status_code
            data["final_url"] = r.url
            data["server"] = r.headers.get("Server", "N/A")
            data["powered_by"] = r.headers.get("X-Powered-By", "N/A")
            print_result("Status", str(r.status_code))
            print_result("URL finale", r.url)
            print_result("Server", r.headers.get("Server", "N/A"))
            print_result("X-Powered-By", r.headers.get("X-Powered-By", "N/A"))
            print_result("Content-Type", r.headers.get("Content-Type", "N/A"))
            
            # Détecter les technologies
            if HAS_BS4:
                soup = BeautifulSoup(r.text, 'html.parser')
                title = soup.title.string if soup.title else "N/A"
                data["title"] = title
                print_result("Titre", title)
                
                # Détection CMS basique
                body = r.text.lower()
                if "wp-content" in body or "wordpress" in body:
                    print_success("CMS détecté: WordPress")
                    data["cms"] = "WordPress"
                elif "joomla" in body:
                    print_success("CMS détecté: Joomla")
                    data["cms"] = "Joomla"
                elif "drupal" in body:
                    print_success("CMS détecté: Drupal")
                    data["cms"] = "Drupal"
                elif "shopify" in body:
                    print_success("CMS détecté: Shopify")
                    data["cms"] = "Shopify"
                
                # Meta tags
                for meta in soup.find_all('meta'):
                    name = meta.get('name', meta.get('property', '')).lower()
                    content = meta.get('content', '')
                    if name in ['description', 'author', 'generator', 'keywords']:
                        print_result(f"Meta {name}", content[:100])
                        data[f"meta_{name}"] = content
            break
        except:
            continue
    
    # 5. SSL
    print(color(f"\n  {'─' * 40}"))
    print_info("SSL Certificate:")
    try:
        context = ssl.create_default_context()
        conn = context.wrap_socket(socket.socket(), server_hostname=domain)
        conn.settimeout(10)
        conn.connect((domain, 443))
        cert = conn.getpeercert()
        conn.close()
        
        issuer = dict(x[0] for x in cert.get("issuer", []))
        data["ssl_issuer"] = issuer.get("organizationName", "N/A")
        data["ssl_expires"] = cert.get("notAfter", "N/A")
        print_result("Émetteur SSL", issuer.get("organizationName", "N/A"))
        print_result("Expire", cert.get("notAfter", "N/A"))
    except:
        print_warning("Pas de certificat SSL ou erreur")
    
    # 6. Wayback Machine
    print(color(f"\n  {'─' * 40}"))
    print_info("Wayback Machine:")
    try:
        r = requests.get(f"https://archive.org/wayback/available?url={domain}", timeout=10).json()
        snapshots = r.get("archived_snapshots", {})
        if snapshots.get("closest"):
            snap = snapshots["closest"]
            data["wayback_url"] = snap.get("url")
            data["wayback_timestamp"] = snap.get("timestamp")
            print_result("Dernier snapshot", snap.get("url"))
            print_result("Date", snap.get("timestamp"))
        else:
            print_info("Aucune archive trouvée")
    except:
        pass
    
    # 7. Subdomains basique
    print(color(f"\n  {'─' * 40}"))
    print_info("Recherche de sous-domaines:")
    try:
        r = requests.get(f"https://crt.sh/?q=%.{domain}&output=json", timeout=15)
        if r.status_code == 200:
            certs = r.json()
            subdomains = set()
            for cert in certs:
                name = cert.get("name_value", "")
                for sub in name.split("\n"):
                    sub = sub.strip().lower()
                    if sub.endswith(domain) and "*" not in sub:
                        subdomains.add(sub)
            
            data["subdomains"] = list(subdomains)
            print_success(f"{len(subdomains)} sous-domaine(s) trouvé(s):")
            for sub in sorted(subdomains)[:30]:
                print(color(f"  ║   → {sub}"))
            if len(subdomains) > 30:
                print_info(f"... et {len(subdomains) - 30} de plus")
    except:
        print_warning("Recherche de sous-domaines échouée")
    
    # 8. VirusTotal si clé dispo
    if CONFIG["virustotal_api_key"]:
        print(color(f"\n  {'─' * 40}"))
        print_info("VirusTotal:")
        try:
            r = requests.get(
                f"https://www.virustotal.com/api/v3/domains/{domain}",
                headers={"x-apikey": CONFIG["virustotal_api_key"]},
                timeout=10
            ).json()
            attrs = r.get("data", {}).get("attributes", {})
            stats = attrs.get("last_analysis_stats", {})
            print_result("Malicious", str(stats.get("malicious", 0)))
            print_result("Suspicious", str(stats.get("suspicious", 0)))
            print_result("Clean", str(stats.get("harmless", 0)))
            print_result("Reputation", str(attrs.get("reputation", "N/A")))
        except:
            pass
    
    # Liens utiles
    print(color(f"\n  {'─' * 40}"))
    print_info("Liens utiles:")
    print_result("Shodan", f"https://www.shodan.io/search?query={domain}")
    print_result("SecurityTrails", f"https://securitytrails.com/domain/{domain}")
    print_result("DNSDumpster", f"https://dnsdumpster.com/")
    print_result("BuiltWith", f"https://builtwith.com/{domain}")
    print_result("Wayback", f"https://web.archive.org/web/*/{domain}")
    
    ask_save(f"domain_{domain}", data)

def google_dork_generator():
    print_header("GOOGLE DORK GENERATOR")
    
    print_info("Modes:")
    print(color("  1) Dorks par domaine/site"))
    print(color("  2) Dorks par personne"))
    print(color("  3) Dorks par email"))
    print(color("  4) Dorks personnalisés"))
    
    mode = get_input("Mode")
    
    dorks = []
    
    if mode == "1":
        site = get_input("Domaine cible")
        if not site:
            return
        dorks = [
            (f'site:{site}', "Toutes les pages indexées"),
            (f'site:{site} filetype:pdf', "Fichiers PDF"),
            (f'site:{site} filetype:doc OR filetype:docx', "Documents Word"),
            (f'site:{site} filetype:xls OR filetype:xlsx', "Fichiers Excel"),
            (f'site:{site} filetype:sql', "Fichiers SQL"),
            (f'site:{site} filetype:log', "Fichiers log"),
            (f'site:{site} filetype:env', "Fichiers .env"),
            (f'site:{site} filetype:xml', "Fichiers XML"),
            (f'site:{site} filetype:conf OR filetype:cfg', "Fichiers de config"),
            (f'site:{site} filetype:bak OR filetype:old', "Fichiers backup"),
            (f'site:{site} inurl:admin', "Pages admin"),
            (f'site:{site} inurl:login', "Pages login"),
            (f'site:{site} inurl:dashboard', "Dashboards"),
            (f'site:{site} inurl:api', "Endpoints API"),
            (f'site:{site} intitle:"index of"', "Directory listing"),
            (f'site:{site} intext:"password"', "Mentions de mot de passe"),
            (f'site:{site} intext:"username" filetype:log', "Logs avec usernames"),
            (f'site:{site} ext:php inurl:?', "PHP avec paramètres"),
            (f'site:{site} inurl:wp-content', "WordPress content"),
            (f'site:{site} inurl:wp-admin', "WordPress admin"),
            (f'site:{site} "error" OR "warning" OR "fatal"', "Messages d'erreur"),
            (f'site:{site} inurl:config', "Pages config"),
            (f'site:{site} inurl:backup', "Backups"),
            (f'site:{site} inurl:.git', "Repos Git exposés"),
            (f'site:{site} "Not for distribution"', "Documents confidentiels"),
            (f'"{site}" -site:{site}', "Mentions externes du domaine"),
            (f'link:{site}', "Sites qui linkent vers le domaine"),
            (f'related:{site}', "Sites similaires"),
            (f'cache:{site}', "Version en cache Google"),
        ]
    
    elif mode == "2":
        name = get_input("Nom de la personne")
        if not name:
            return
        dorks = [
            (f'"{name}"', "Mention exacte"),
            (f'"{name}" site:linkedin.com', "LinkedIn"),
            (f'"{name}" site:facebook.com', "Facebook"),
            (f'"{name}" site:twitter.com OR site:x.com', "Twitter/X"),
            (f'"{name}" site:instagram.com', "Instagram"),
            (f'"{name}" site:github.com', "GitHub"),
            (f'"{name}" filetype:pdf', "Documents PDF"),
            (f'"{name}" resume OR CV', "CV / Resume"),
            (f'"{name}" email OR contact OR @', "Infos de contact"),
            (f'"{name}" phone OR tel OR mobile', "Numéro de téléphone"),
            (f'"{name}" address OR location', "Adresse"),
            (f'"{name}" site:youtube.com', "YouTube"),
            (f'"{name}" inurl:blog', "Blogs"),
            (f'"{name}" site:reddit.com', "Reddit"),
            (f'"{name}" site:medium.com', "Medium"),
        ]
    
    elif mode == "3":
        email = get_input("Adresse email")
        if not email:
            return
        dorks = [
            (f'"{email}"', "Mention exacte de l'email"),
            (f'"{email}" site:pastebin.com', "Pastebin"),
            (f'"{email}" site:github.com', "GitHub"),
            (f'"{email}" filetype:pdf', "Documents PDF"),
            (f'"{email}" filetype:xls OR filetype:csv', "Fichiers de données"),
            (f'"{email}" intext:password', "Leaks potentiels"),
            (f'"{email}" site:linkedin.com', "LinkedIn"),
            (f'intext:"{email}"', "Toutes mentions"),
        ]
    
    elif mode == "4":
        keyword = get_input("Mot-clé")
        site_filter = get_input("Site spécifique (laisser vide pour tous)")
        filetype = get_input("Type de fichier (laisser vide pour tous)")
        
        base = f'"{keyword}"'
        if site_filter:
            base += f' site:{site_filter}'
        if filetype:
            base += f' filetype:{filetype}'
        dorks = [(base, "Recherche personnalisée")]
    
    print(color(f"\n  {'─' * 60}"))
    print_success(f"{len(dorks)} dork(s) généré(s):\n")
    
    data = {}
    for i, (dork, desc) in enumerate(dorks, 1):
        google_url = f"https://www.google.com/search?q={quote_plus(dork)}"
        print(color(f"  {i:02d}. [{desc}]"))
        print(color(f"      Dork  : {dork}"))
        print(color(f"      URL   : {google_url}\n"))
        data[f"{i:02d}_{desc}"] = {"dork": dork, "url": google_url}
    
    ask_save("google_dorks", data)

def image_metadata():
    filepath = get_input("Chemin de l'image")
    if not filepath or not os.path.exists(filepath):
        print_error("Fichier introuvable")
        return
    
    print_header(f"METADATA - {os.path.basename(filepath)}")
    
    data = {"file": filepath}
    
    # Infos basiques
    stat = os.stat(filepath)
    data["size"] = f"{stat.st_size / 1024:.1f} KB"
    data["created"] = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
    data["modified"] = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    print_result("Taille", data["size"])
    print_result("Créé", data["created"])
    print_result("Modifié", data["modified"])
    
    if HAS_PIL:
        try:
            img = Image.open(filepath)
            data["format"] = img.format
            data["dimensions"] = f"{img.size[0]}x{img.size[1]}"
            data["mode"] = img.mode
            print_result("Format", img.format)
            print_result("Dimensions", data["dimensions"])
            print_result("Mode couleur", img.mode)
            
            # EXIF
            exif_data = img._getexif()
            if exif_data:
                print(color(f"\n  {'─' * 40}"))
                print_info("Données EXIF:")
                
                gps_info = {}
                for tag_id, value in exif_data.items():
                    tag = TAGS.get(tag_id, tag_id)
                    
                    if tag == "GPSInfo":
                        for gps_tag_id, gps_value in value.items():
                            gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                            gps_info[gps_tag] = gps_value
                            print_result(f"GPS {gps_tag}", str(gps_value))
                    elif isinstance(value, bytes):
                        continue
                    else:
                        value_str = str(value)[:100]
                        data[f"exif_{tag}"] = value_str
                        print_result(str(tag), value_str)
                
                # Conversion GPS en coordonnées
                if gps_info:
                    try:
                        def gps_to_decimal(coords, ref):
                            d, m, s = coords
                            decimal = float(d) + float(m) / 60 + float(s) / 3600
                            if ref in ['S', 'W']:
                                decimal = -decimal
                            return decimal
                        
                        lat = gps_to_decimal(gps_info.get("GPSLatitude", (0,0,0)), 
                                           gps_info.get("GPSLatitudeRef", "N"))
                        lon = gps_to_decimal(gps_info.get("GPSLongitude", (0,0,0)),
                                           gps_info.get("GPSLongitudeRef", "E"))
                        
                        data["gps_latitude"] = lat
                        data["gps_longitude"] = lon
                        
                        print(color(f"\n  {'─' * 40}"))
                        print_success(f"COORDONNÉES GPS TROUVÉES!")
                        print_result("Latitude", str(lat))
                        print_result("Longitude", str(lon))
                        print_result("Google Maps", f"https://maps.google.com/?q={lat},{lon}")
                        print_result("OpenStreetMap", f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=15")
                    except:
                        pass
            else:
                print_warning("Aucune donnée EXIF trouvée")
        except Exception as e:
            print_error(f"Erreur PIL: {e}")
    else:
        print_warning("Pillow non installé. pip install Pillow")
    
    ask_save(f"metadata_{os.path.basename(filepath)}", data)

def wayback_machine():
    url = get_input("URL ou domaine")
    if not url:
        return
    print_header(f"WAYBACK MACHINE - {url}")
    
    try:
        # Dernier snapshot
        r = requests.get(f"https://archive.org/wayback/available?url={url}", timeout=10).json()
        snapshots = r.get("archived_snapshots", {})
        if snapshots.get("closest"):
            snap = snapshots["closest"]
            print_result("Dernier snapshot", snap.get("url"))
            print_result("Date", snap.get("timestamp"))
            print_result("Status", str(snap.get("status")))
        
        # Liste des captures
        print(color(f"\n  {'─' * 40}"))
        print_info("Historique des captures:")
        
        r2 = requests.get(
            f"http://web.archive.org/cdx/search/cdx?url={url}&output=json&limit=50&fl=timestamp,statuscode,mimetype",
            timeout=15
        ).json()
        
        if len(r2) > 1:
            data = {"url": url, "snapshots": []}
            print(color(f"  {'Timestamp':<20} {'Status':<10} {'Type':<30}"))
            print(color(f"  {'─'*20} {'─'*10} {'─'*30}"))
            for entry in r2[1:]:  # Skip header
                ts, status, mime = entry
                date_str = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}"
                print(color(f"  {date_str:<20} {status:<10} {mime:<30}"))
                data["snapshots"].append({"date": date_str, "status": status, "mime": mime})
            
            print_success(f"\n  Total: {len(r2)-1} captures trouvées (limité à 50)")
            print_result("Voir tout", f"https://web.archive.org/web/*/{url}")
            ask_save(f"wayback_{url.replace('/', '_')}", data)
        else:
            print_warning("Aucune capture trouvée")
    
    except Exception as e:
        print_error(f"Erreur: {e}")

def haveibeenpwned():
    email = get_input("Adresse email")
    if not email:
        return
    print_header(f"BREACH CHECK - {email}")
    
    # API v3 nécessite une clé payante, on utilise des alternatives gratuites
    data = {"email": email, "breaches": []}
    
    # 1. BreachDirectory (gratuit)
    print_info("Vérification des breaches connues...")
    try:
        r = requests.get(
            f"https://breachdirectory.org/api/email/{email}",
            timeout=10,
            headers={"User-Agent": "BlueFox-OSINT/3.0"}
        )
        if r.status_code == 200:
            result = r.json()
            if result.get("found"):
                print_warning("⚠ Cette adresse a été trouvée dans des fuites de données!")
                for breach in result.get("result", []):
                    print_result("Source", breach.get("source", "N/A"))
                    # Provider payloads can contain passwords/hashes: retain source only.
                    data["breaches"].append({"source": breach.get("source", "N/A")})
    except:
        pass
    
    # 2. Hash de l'email pour vérification anonyme
    email_hash = hashlib.sha256(email.encode()).hexdigest()
    data["sha256"] = email_hash
    print_result("SHA256 de l'email", email_hash)
    
    # 3. Password hash check (k-anonymity)
    print(color(f"\n  {'─' * 40}"))
    check_pass = get_input("Vérifier aussi un mot de passe? (oui/non)")
    if check_pass.lower() in ["oui", "o", "yes", "y"]:
        password = get_secret("Mot de passe à vérifier")
        if password:
            from .passwords import pwned_count
            try:
                count = pwned_count(password)
                data["password_pwned"] = count > 0
                data["password_count"] = count
                if count:
                    print_warning(f"Ce mot de passe apparaît {count} fois dans les fuites connues")
                else:
                    print_info("Mot de passe absent de cette réponse ; aucune garantie de sécurité")
            except (requests.RequestException, ValueError):
                # Do not echo transport payloads or secret-derived values.
                data["password_status"] = "unavailable"
                print_error("Pwned Passwords: résultat indisponible")
    
    # 4. Liens utiles
    print(color(f"\n  {'─' * 40}"))
    print_info("Vérifications supplémentaires:")
    print_result("HaveIBeenPwned", f"https://haveibeenpwned.com/account/{email}")
    print_result("DeHashed", f"https://dehashed.com/search?query={email}")
    print_result("LeakCheck", f"https://leakcheck.io/check/{email}")
    print_result("IntelX", f"https://intelx.io/?s={email}")
    print_result("Snusbase", f"https://snusbase.com/")
    
    ask_save(f"breach_{email.replace('@','_')}", data)

def social_media_lookup():
    username = get_input("Nom d'utilisateur à rechercher")
    if not username:
        return
    raw_username = username.strip()
    safe_username = quote(raw_username, safe="")
    update_rpc("Social Media", f"Recherche {username}")
    print_header(f"SOCIAL MEDIA LOOKUP - {username}")
    
    platforms = {
        # Format: (url, nom)
        "GitHub": f"https://github.com/{safe_username}",
        "Twitter/X": f"https://x.com/{safe_username}",
        "Instagram": f"https://instagram.com/{safe_username}",
        "Facebook": f"https://facebook.com/{safe_username}",
        "LinkedIn": f"https://linkedin.com/in/{safe_username}",
        "Reddit": f"https://reddit.com/user/{safe_username}",
        "YouTube": f"https://youtube.com/@{safe_username}",
        "TikTok": f"https://tiktok.com/@{safe_username}",
        "Pinterest": f"https://pinterest.com/{safe_username}",
        "Twitch": f"https://twitch.tv/{safe_username}",
        "Snapchat": f"https://snapchat.com/add/{safe_username}",
        "Telegram": f"https://t.me/{safe_username}",
        "Medium": f"https://medium.com/@{safe_username}",
        "DeviantArt": f"https://deviantart.com/{safe_username}",
        "Flickr": f"https://flickr.com/people/{safe_username}",
        "SoundCloud": f"https://soundcloud.com/{safe_username}",
        "Spotify": f"https://open.spotify.com/user/{safe_username}",
        "Steam": f"https://steamcommunity.com/id/{safe_username}",
        "Xbox": f"https://xboxgamertag.com/search/{safe_username}",
        "Roblox": f"https://www.roblox.com/search/users?keyword={quote(raw_username)}",
        "Minecraft": f"https://namemc.com/profile/{safe_username}",
        "HackTheBox": f"https://app.hackthebox.com/users/{safe_username}",
        "TryHackMe": f"https://tryhackme.com/p/{safe_username}",
        "Keybase": f"https://keybase.io/{safe_username}",
        "Gravatar": f"https://gravatar.com/{safe_username}",
        "About.me": f"https://about.me/{safe_username}",
        "GitLab": f"https://gitlab.com/{safe_username}",
        "Bitbucket": f"https://bitbucket.org/{safe_username}",
        "Docker Hub": f"https://hub.docker.com/u/{safe_username}",
        "npm": f"https://www.npmjs.com/~{safe_username}",
        "PyPI": f"https://pypi.org/user/{safe_username}",
        "Stack Overflow": f"https://stackoverflow.com/users/?q={quote_plus(raw_username)}",
        "Pastebin": f"https://pastebin.com/u/{safe_username}",
        "Replit": f"https://replit.com/@{safe_username}",
        "CodePen": f"https://codepen.io/{safe_username}",
        "Dribbble": f"https://dribbble.com/{safe_username}",
        "Behance": f"https://behance.net/{safe_username}",
        "Vimeo": f"https://vimeo.com/{safe_username}",
        "Dailymotion": f"https://dailymotion.com/{safe_username}",
        "VK": f"https://vk.com/{safe_username}",
        "OK.ru": f"https://ok.ru/{safe_username}",
        "Quora": f"https://quora.com/profile/{safe_username}",
        "Clubhouse": f"https://joinclubhouse.com/@{safe_username}",
        "Cash App": f"https://cash.app/${safe_username}",
        "Venmo": f"https://venmo.com/{safe_username}",
        "Fiverr": f"https://fiverr.com/{safe_username}",
        "Upwork": f"https://upwork.com/freelancers/~{safe_username}",
        "9GAG": f"https://9gag.com/u/{safe_username}",
        "MyAnimeList": f"https://myanimelist.net/profile/{safe_username}",
        "Wattpad": f"https://wattpad.com/user/{safe_username}",
        "Goodreads": f"https://goodreads.com/{safe_username}",
        "Last.fm": f"https://last.fm/user/{safe_username}",
        "Letterboxd": f"https://letterboxd.com/{safe_username}",
        "Chess.com": f"https://chess.com/member/{safe_username}",
        "Lichess": f"https://lichess.org/@/{safe_username}",
    }
    
    found = []
    not_found = []
    errors = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    def check_platform(name, url):
        try:
            r = requests.get(url, headers=headers, timeout=8, allow_redirects=True)
            if r.status_code in [403, 429, 451]:
                return ("error", name, f"BLOCKED_{r.status_code}")
            if r.status_code == 200:
                # Vérifications supplémentaires pour éviter les faux positifs
                lower_text = r.text.lower()
                if "not found" in lower_text or "doesn't exist" in lower_text or \
                   "page not found" in lower_text or "user not found" in lower_text or \
                   "no results" in lower_text or "404" in r.url:
                    return ("not_found", name, url)
                return ("possible", name, url)
            elif r.status_code == 404:
                return ("not_found", name, url)
            else:
                return ("error", name, f"STATUS_{r.status_code}")
        except requests.exceptions.ConnectionError:
            return ("error", name, url)
        except requests.exceptions.Timeout:
            return ("error", name, url)
        except:
            return ("error", name, url)
    
    total = len(platforms)
    done = 0
    
    print_info(f"Vérification de {total} plateformes...\n")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(check_platform, name, url): name for name, url in platforms.items()}
        
        for future in concurrent.futures.as_completed(futures):
            done += 1
            sys.stdout.write(color(f"\r  [i] Progression: {done}/{total} ({int(done/total*100)}%)"))
            sys.stdout.flush()
            
            try:
                status, name, url = future.result()
                if status == "possible":
                    found.append((name, url))
                elif status == "not_found":
                    not_found.append(name)
                else:
                    errors.append(name)
            except Exception:
                errors.append(futures[future])
    
    # Résultats
    print(color(f"\n\n  {'═' * 60}"))
    print_info(f"RÉSULTATS POUR: {username}")
    print(color(f"  {'═' * 60}\n"))
    
    if found:
        print_info(f"Profils possibles ({len(found)}):\n")
        for name, url in sorted(found):
            print(color(f"  ✓ {name:<20} → {url}"))
    
    print(color(f"\n  {'─' * 40}"))
    print_info(f"Absence apparente: {len(not_found)} | Erreurs: {len(errors)}")

    print_warning("HTTP 200 ne prouve ni l'existence d'un profil ni une identité")
    data = {
        "username": username,
        "found_count": len(found),
        "profiles": {name: url for name, url in sorted(found)},
        "profile_status": "possible",
        "not_found_count": len(not_found),
        "not_found": sorted(not_found),
        "error_count": len(errors),
        "errors": sorted(errors),
        "status": "partial" if errors else "completed",
        "interpretation": "Profils possibles et absences apparentes ; aucune identité confirmée",
    }
    ask_save(f"social_{raw_username}", data)

def email_osint():
    email = get_input("Adresse email")
    if not email:
        return
    print_header(f"EMAIL OSINT - {email}")
    
    data = {"email": email}
    
    # Validation format
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        print_error("Format d'email invalide")
        return
    
    parts = email.split("@")
    local_part = parts[0]
    domain = parts[1]
    data["local_part"] = local_part
    data["domain"] = domain
    
    print_result("Partie locale", local_part)
    print_result("Domaine", domain)
    
    # 1. Vérification MX du domaine
    print(color(f"\n  {'─' * 40}"))
    print_info("Vérification du domaine email:")
    
    if HAS_DNS:
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            for mx in mx_records:
                print_result("MX Record", str(mx))
                data.setdefault("mx_records", []).append(str(mx))
        except:
            print_warning("Pas de record MX trouvé - domaine peut-être invalide")
    
    # 2. Check SMTP (existence basique)
    print(color(f"\n  {'─' * 40}"))
    print_info("Vérification SMTP:")
    try:
        import smtplib
        if HAS_DNS:
            mx_records = dns.resolver.resolve(domain, 'MX')
            mx_host = str(mx_records[0].exchange).rstrip('.')
            
            smtp = smtplib.SMTP(timeout=10)
            smtp.connect(mx_host)
            smtp.helo("bluefox.local")
            smtp.mail("test@bluefox.local")
            code, msg = smtp.rcpt(email)
            smtp.quit()
            
            if code == 250:
                print_success("L'adresse email semble valide (acceptée par le serveur)")
                data["smtp_valid"] = True
            else:
                print_warning(f"Le serveur a répondu: {code} {msg.decode()}")
                data["smtp_valid"] = False
        else:
            print_warning("Module dnspython requis pour la vérification SMTP")
    except Exception as e:
        print_info(f"Vérification SMTP impossible: {e}")
    
    # 3. Gravatar
    print(color(f"\n  {'─' * 40}"))
    print_info("Gravatar:")
    email_hash_md5 = hashlib.md5(email.lower().encode()).hexdigest()
    gravatar_url = f"https://gravatar.com/avatar/{email_hash_md5}?d=404"
    try:
        r = requests.get(gravatar_url, timeout=10)
        if r.status_code == 200:
            print_success(f"Avatar Gravatar trouvé!")
            print_result("URL Avatar", f"https://gravatar.com/avatar/{email_hash_md5}")
            print_result("Profil", f"https://gravatar.com/{email_hash_md5}")
            data["gravatar"] = True
        else:
            print_info("Pas de Gravatar")
            data["gravatar"] = False
    except:
        pass
    
    # 4. Services connus par domaine
    print(color(f"\n  {'─' * 40}"))
    print_info("Analyse du provider:")
    
    known_providers = {
        "gmail.com": "Google (Gmail)",
        "googlemail.com": "Google (Gmail)",
        "yahoo.com": "Yahoo",
        "yahoo.fr": "Yahoo France",
        "outlook.com": "Microsoft (Outlook)",
        "hotmail.com": "Microsoft (Hotmail)",
        "hotmail.fr": "Microsoft (Hotmail France)",
        "live.com": "Microsoft (Live)",
        "msn.com": "Microsoft (MSN)",
        "protonmail.com": "ProtonMail (Chiffré)",
        "proton.me": "ProtonMail (Chiffré)",
        "icloud.com": "Apple (iCloud)",
        "me.com": "Apple",
        "aol.com": "AOL",
        "zoho.com": "Zoho",
        "tutanota.com": "Tutanota (Chiffré)",
        "mail.ru": "Mail.ru (Russie)",
        "yandex.ru": "Yandex (Russie)",
        "gmx.com": "GMX",
        "orange.fr": "Orange France",
        "free.fr": "Free France",
        "sfr.fr": "SFR France",
        "laposte.net": "La Poste France",
        "wanadoo.fr": "Wanadoo/Orange France",
    }
    
    provider = known_providers.get(domain.lower(), "Inconnu / Domaine personnalisé")
    data["provider"] = provider
    print_result("Provider", provider)
    
    if domain.lower() not in known_providers:
        print_info("Domaine personnalisé - probablement professionnel ou auto-hébergé")
        # Vérifier le site
        try:
            r = requests.get(f"https://{domain}", timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            print_result("Site web", f"https://{domain} (Status: {r.status_code})")
        except:
            pass
    
    # 5. Variations d'email possibles
    print(color(f"\n  {'─' * 40}"))
    print_info("Variations possibles:")
    
    if "." in local_part:
        no_dots = local_part.replace(".", "")
        print_result("Sans points", f"{no_dots}@{domain}")
    
    if "+" in local_part:
        base = local_part.split("+")[0]
        print_result("Sans tag", f"{base}@{domain}")
    
    common_domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "protonmail.com"]
    print_info("Même username sur d'autres providers:")
    for d in common_domains:
        if d != domain.lower():
            print(color(f"  ║   → {local_part}@{d}"))
    
    # 6. Recherches externes
    print(color(f"\n  {'─' * 40}"))
    print_info("Liens de recherche:")
    print_result("Google", f"https://www.google.com/search?q=%22{email}%22")
    print_result("HaveIBeenPwned", f"https://haveibeenpwned.com/account/{email}")
    print_result("Hunter.io", f"https://hunter.io/email-verifier/{email}")
    print_result("EmailRep", f"https://emailrep.io/{email}")
    print_result("Epieos", f"https://epieos.com/?q={email}")
    
    # 7. Hunter.io API si disponible
    if CONFIG["hunter_api_key"]:
        try:
            r = requests.get(
                f"https://api.hunter.io/v2/email-verifier?email={email}&api_key={CONFIG['hunter_api_key']}",
                timeout=10
            ).json()
            d = r.get("data", {})
            print(color(f"\n  {'─' * 40}"))
            print_info("Hunter.io:")
            print_result("Score", str(d.get("score")))
            print_result("Result", d.get("result"))
            print_result("Disposable", str(d.get("disposable")))
            print_result("Webmail", str(d.get("webmail")))
        except:
            pass
    
    ask_save(f"email_{email.replace('@','_')}", data)

def shodan_search():
    if not CONFIG["shodan_api_key"]:
        print_error("Clé API Shodan requise. Définissez SHODAN_API_KEY")
        print_info("Obtenir une clé gratuite: https://account.shodan.io/register")
        return
    
    print_header("SHODAN SEARCH")
    print_info("1) Recherche par IP | 2) Recherche par query")
    mode = get_input("Mode")
    
    headers = {"Key": CONFIG["shodan_api_key"]}
    
    if mode == "1":
        ip = get_input("Adresse IP")
        if not ip:
            return
        try:
            r = requests.get(f"https://api.shodan.io/shodan/host/{ip}?key={CONFIG['shodan_api_key']}", timeout=15).json()
            
            data = {
                "IP": r.get("ip_str"),
                "Organisation": r.get("org"),
                "OS": r.get("os"),
                "Pays": r.get("country_name"),
                "Ville": r.get("city"),
                "ISP": r.get("isp"),
                "Ports": r.get("ports"),
                "Hostnames": r.get("hostnames"),
                "Vulns": r.get("vulns", []),
            }
            
            for k, v in data.items():
                print_result(k, str(v))
            
            if r.get("vulns"):
                print(color(f"\n  {'─' * 40}"))
                print_warning("Vulnérabilités connues:")
                for vuln in r.get("vulns", []):
                    print(color(f"  ⚠ {vuln}"))
            
            if r.get("data"):
                print(color(f"\n  {'─' * 40}"))
                print_info("Services:")
                for service in r.get("data", [])[:10]:
                    print_result(f"Port {service.get('port')}", service.get("product", "N/A"))
            
            ask_save(f"shodan_{ip}", data)
        except Exception as e:
            print_error(f"Erreur: {e}")
    
    elif mode == "2":
        query = get_input("Query Shodan")
        if not query:
            return
        try:
            r = requests.get(
                f"https://api.shodan.io/shodan/host/search?key={CONFIG['shodan_api_key']}&query={query}",
                timeout=15
            ).json()
            
            print_success(f"Résultats: {r.get('total', 0)}")
            for match in r.get("matches", [])[:20]:
                print(color(f"\n  {'─' * 30}"))
                print_result("IP", match.get("ip_str"))
                print_result("Port", str(match.get("port")))
                print_result("Org", match.get("org"))
                print_result("Pays", match.get("location", {}).get("country_name"))
        except Exception as e:
            print_error(f"Erreur: {e}")

def virustotal_check():
    if not CONFIG["virustotal_api_key"]:
        print_error("Clé API VirusTotal requise. Définissez VIRUSTOTAL_API_KEY")
        print_info("Clé gratuite: https://www.virustotal.com/gui/join-us")
        return
    
    print_header("VIRUSTOTAL CHECK")
    print_info("1) URL | 2) Domaine | 3) IP | 4) Hash de fichier")
    mode = get_input("Mode")
    
    headers = {"x-apikey": CONFIG["virustotal_api_key"]}
    
    try:
        if mode == "1":
            url = get_input("URL à vérifier")
            url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
            r = requests.get(f"https://www.virustotal.com/api/v3/urls/{url_id}", headers=headers, timeout=15)
            
        elif mode == "2":
            domain = get_input("Domaine")
            r = requests.get(f"https://www.virustotal.com/api/v3/domains/{domain}", headers=headers, timeout=15)
            
        elif mode == "3":
            ip = get_input("Adresse IP")
            r = requests.get(f"https://www.virustotal.com/api/v3/ip_addresses/{ip}", headers=headers, timeout=15)
            
        elif mode == "4":
            file_hash = get_input("Hash (MD5/SHA1/SHA256)")
            r = requests.get(f"https://www.virustotal.com/api/v3/files/{file_hash}", headers=headers, timeout=15)
        else:
            return
        
        payload = response_object(r, "VirusTotal")
        obj = payload.get("data")
        attrs = obj.get("attributes") if isinstance(obj, dict) else None
        stats = attrs.get("last_analysis_stats") if isinstance(attrs, dict) else None
        required = ("malicious", "suspicious", "harmless", "undetected")
        if (not isinstance(stats, dict) or not all(key in stats for key in required)
                or any(type(value) is not int or value < 0 for value in stats.values())
                or sum(stats[key] for key in required) == 0):
            raise ValueError("VirusTotal: analyse absente, incomplète ou indisponible")
        data = {
            "Malicious": stats.get("malicious", 0),
            "Suspicious": stats.get("suspicious", 0),
            "Harmless": stats.get("harmless", 0),
            "Undetected": stats.get("undetected", 0),
            "Reputation": attrs.get("reputation", "N/A"),
        }
        
        for k, v in data.items():
            print_result(k, str(v))
        
        if stats.get("malicious", 0) > 0:
            print_warning(f"⚠ DÉTECTÉ COMME MALVEILLANT PAR {stats['malicious']} MOTEURS!")
        else:
            print_info("Aucune détection malveillante dans cette analyse ; aucune garantie de sécurité")
        
        data["Interpretation"] = "Statistiques de cette analyse uniquement ; aucune garantie de sécurité"
        ask_save("virustotal", data)
    except requests.RequestException:
        print_error("VirusTotal: erreur réseau, résultat indisponible")
    except Exception as e:
        print_error(f"Erreur: {e}")

def subdomain_finder():
    domain = get_input("Domaine (ex: example.com)")
    if not domain:
        return
    print_header(f"SUBDOMAIN FINDER - {domain}")
    
    subdomains = set()
    
    # 1. crt.sh
    print_info("Source: crt.sh (Certificate Transparency)...")
    try:
        r = requests.get(f"https://crt.sh/?q=%.{domain}&output=json", timeout=20)
        if r.status_code == 200:
            for cert in r.json():
                for name in cert.get("name_value", "").split("\n"):
                    name = name.strip().lower()
                    if name.endswith(domain) and "*" not in name:
                        subdomains.add(name)
            print_success(f"crt.sh: {len(subdomains)} trouvé(s)")
    except:
        print_warning("crt.sh timeout ou erreur")
    
    # 2. DNS brute force (commun)
    print_info("Source: DNS brute force (prefixes communs)...")
    common_subs = [
        "www", "mail", "ftp", "smtp", "pop", "imap", "webmail",
        "admin", "portal", "blog", "shop", "store", "api", "dev",
        "staging", "test", "beta", "demo", "app", "m", "mobile",
        "cdn", "static", "assets", "img", "images", "media",
        "vpn", "remote", "gateway", "proxy", "ns1", "ns2", "ns3",
        "dns", "dns1", "dns2", "mx", "mx1", "mx2", "email",
        "login", "auth", "sso", "id", "account", "accounts",
        "dashboard", "panel", "cpanel", "whm", "plesk",
        "db", "database", "mysql", "postgres", "mongo", "redis",
        "git", "gitlab", "github", "svn", "jenkins", "ci", "cd",
        "monitor", "grafana", "kibana", "elastic", "prometheus",
        "docs", "doc", "wiki", "help", "support", "status",
        "cloud", "aws", "azure", "gcp", "s3", "storage",
        "old", "new", "v2", "v3", "legacy", "archive",
        "intranet", "internal", "corp", "office", "exchange",
        "crm", "erp", "hr", "jira", "confluence",
    ]
    
    def check_sub(sub):
        try:
            full = f"{sub}.{domain}"
            socket.gethostbyname(full)
            return full
        except:
            return None
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(check_sub, s): s for s in common_subs}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result:
                subdomains.add(result)
    
    # 3. Résultats
    print(color(f"\n  {'═' * 60}"))
    print_success(f"TOTAL: {len(subdomains)} sous-domaine(s) trouvé(s)\n")
    
    data = {"domain": domain, "subdomains": {}}
    
    for sub in sorted(subdomains):
        try:
            ip = socket.gethostbyname(sub)
            print(color(f"  ✓ {sub:<40} → {ip}"))
            data["subdomains"][sub] = ip
        except:
            print(color(f"  ✓ {sub:<40} → N/A"))
            data["subdomains"][sub] = "N/A"
    
    ask_save(f"subdomains_{domain}", data)

def tech_stack_detector():
    url = get_input("URL (ex: https://example.com)")
    if not url:
        return
    if not url.startswith("http"):
        url = "https://" + url
    
    print_header(f"TECH STACK DETECTOR - {url}")
    
    data = {"url": url, "technologies": []}
    
    try:
        headers_req = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        r = requests.get(url, timeout=15, headers=headers_req, allow_redirects=True)
        
        resp_headers = dict(r.headers)
        body = r.text.lower()
        
        # Détection par headers
        print_info("Analyse des headers HTTP:")
        server = resp_headers.get("Server", "")
        powered = resp_headers.get("X-Powered-By", "")
        
        if server:
            print_result("Server", server)
            data["technologies"].append({"name": server, "category": "Server"})
        if powered:
            print_result("X-Powered-By", powered)
            data["technologies"].append({"name": powered, "category": "Framework"})
        
        # Détection par contenu
        print(color(f"\n  {'─' * 40}"))
        print_info("Analyse du contenu:")
        
        techs = {
            # CMS
            "WordPress": ["wp-content", "wp-includes", "wordpress"],
            "Joomla": ["joomla", "/media/system/js/", "com_content"],
            "Drupal": ["drupal", "sites/all/", "sites/default/"],
            "Shopify": ["shopify", "cdn.shopify.com"],
            "Wix": ["wix.com", "wixstatic.com"],
            "Squarespace": ["squarespace.com", "sqsp.com"],
            "Ghost": ["ghost.io", "ghost.org"],
            "Magento": ["magento", "mage/"],
            "PrestaShop": ["prestashop", "presta"],
            
            # Frameworks JS
            "React": ["react", "reactdom", "_react", "__NEXT_DATA__"],
            "Next.js": ["__next", "_next/static", "__NEXT_DATA__"],
            "Vue.js": ["vue.js", "vuejs", "__vue__", "vue.min.js"],
            "Nuxt.js": ["__nuxt", "_nuxt/"],
            "Angular": ["ng-version", "angular", "ng-app"],
            "Svelte": ["svelte"],
            "jQuery": ["jquery"],
            "Bootstrap": ["bootstrap"],
            "Tailwind CSS": ["tailwind"],
            
            # Analytics
            "Google Analytics": ["google-analytics.com", "gtag", "ga.js", "analytics.js"],
            "Google Tag Manager": ["googletagmanager.com", "gtm.js"],
            "Facebook Pixel": ["fbevents.js", "facebook.com/tr"],
            "Hotjar": ["hotjar.com", "hotjar"],
            
            # CDN
            "Cloudflare": ["cloudflare", "cf-ray"],
            "AWS CloudFront": ["cloudfront.net"],
            "Fastly": ["fastly"],
            "Akamai": ["akamai"],
            
            # Autres
            "Google Fonts": ["fonts.googleapis.com"],
            "Font Awesome": ["fontawesome", "font-awesome"],
            "reCAPTCHA": ["recaptcha", "grecaptcha"],
            "Stripe": ["stripe.com", "stripe.js"],
            "PayPal": ["paypal.com", "paypalobjects"],
        }
        
        for tech, signatures in techs.items():
            for sig in signatures:
                if sig in body or sig in str(resp_headers).lower():
                    print_success(f"Détecté: {tech}")
                    data["technologies"].append({"name": tech, "category": "Detected"})
                    break
        
        # Cookies intéressants
        print(color(f"\n  {'─' * 40}"))
        print_info("Cookies:")
        cookies = r.cookies.get_dict()
        cookie_indicators = {
            "PHPSESSID": "PHP",
            "JSESSIONID": "Java",
            "ASP.NET": "ASP.NET",
            "csrftoken": "Django",
            "_rails": "Ruby on Rails",
            "laravel": "Laravel",
            "express": "Express.js",
        }
        for cookie_name in cookies:
            print_result("Cookie", cookie_name)
            for indicator, tech in cookie_indicators.items():
                if indicator.lower() in cookie_name.lower():
                    print_success(f"Détecté via cookie: {tech}")
                    data["technologies"].append({"name": tech, "category": "Cookie"})
        
        # BuiltWith link
        print(color(f"\n  {'─' * 40}"))
        parsed = urlparse(url)
        print_result("BuiltWith", f"https://builtwith.com/{parsed.netloc}")
        print_result("Wappalyzer", f"https://www.wappalyzer.com/lookup/{parsed.netloc}")
        
        ask_save(f"techstack_{parsed.netloc}", data)
        
    except Exception as e:
        print_error(f"Erreur: {e}")

def report_generator():
    print_header("RAPPORT D'INVESTIGATION")
    
    results_dir = str(config.results_path())
    if not os.path.exists(results_dir):
        print_error("Aucun résultat sauvegardé trouvé")
        return
    
    files = sorted(f for f in os.listdir(results_dir)
                   if f.endswith('.json') and not f.upper().startswith('REPORT_')
                   and os.path.isfile(os.path.join(results_dir, f)))
    if not files:
        print_error("Aucun fichier JSON trouvé dans les résultats")
        return
    
    print_info(f"Fichiers de résultats disponibles ({len(files)}):\n")
    for i, f in enumerate(sorted(files), 1):
        size = os.path.getsize(os.path.join(results_dir, f))
        print(color(f"  {i:3d}. {f} ({size/1024:.1f} KB)"))
    
    print(color(f"\n  0. Générer un rapport avec TOUS les fichiers"))
    
    choice = get_input("Numéro(s) du/des fichier(s) (séparés par des virgules, ou 0 pour tous)")
    
    selected_files = []
    if choice == "0":
        selected_files = files
    else:
        try:
            indices = [int(x.strip()) for x in choice.split(",")]
            sorted_files = sorted(files)
            for idx in indices:
                if 1 <= idx <= len(files):
                    selected_files.append(sorted_files[idx-1])
        except:
            print_error("Entrée invalide")
            return
    
    if not selected_files:
        print_error("Aucun fichier sélectionné")
        return
    
    # Construire le rapport
    report = {
        "title": "BlueFox OSINT Investigation Report",
        "report_kind": "bluefox_investigation",
        "generated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tool": f"BlueFox Tools v{__version__}",
        "sections": []
    }
    
    for f in selected_files:
        try:
            with open(os.path.join(results_dir, f), "r", encoding="utf-8") as fp:
                content = json.load(fp)
                if is_report(content):
                    print_warning(f"Rapport déjà généré ignoré : {f}")
                    continue
                report["sections"].append({
                    "source_file": f,
                    "data": content
                })
        except (OSError, ValueError) as exc:
            print_error(f"Source illisible {f}: {exc}. Rapport annulé")
            return

    if not report["sections"]:
        print_error("Aucune source exploitable ; rapport annulé")
        return
    if save_result("REPORT", report, "json") is None:
        return
    save_result("REPORT", report_text(report), "txt")

# ============================================================
#  SYSTÈME DE MENUS
# ============================================================

def list_saved_results():
    print_header("RÉSULTATS SAUVEGARDÉS")
    results_dir = str(config.results_path())
    if not os.path.exists(results_dir):
        print_info("Aucun résultat sauvegardé")
        return
    
    files = os.listdir(results_dir)
    if not files:
        print_info("Dossier vide")
        return
    
    total_size = 0
    for f in sorted(files):
        path = os.path.join(results_dir, f)
        size = os.path.getsize(path)
        total_size += size
        mod_time = datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M")
        print(color(f"  {mod_time}  {size/1024:>8.1f} KB  {f}"))
    
    print(color(f"\n  {'─' * 40}"))
    print_info(f"Total: {len(files)} fichier(s), {total_size/1024:.1f} KB")

