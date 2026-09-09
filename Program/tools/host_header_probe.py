from Program import legacy_tools as core


def run():
    url = core.normalize_url(core.get_input("URL cible"))
    if not url:
        return
    host_header = core.get_input("Host header custom")
    if not host_header:
        return

    core.print_header("HOST HEADER PROBE")
    headers = {"Host": host_header, "User-Agent": f"BlueFox/{core.__version__}"}
    data = {"url": url, "host_header": host_header}

    try:
        r = core.requests.get(url, headers=headers, timeout=15, allow_redirects=False)
        data["status_code"] = r.status_code
        data["location"] = r.headers.get("Location", "N/A")
        data["server"] = r.headers.get("Server", "N/A")
        core.print_result("Status", str(r.status_code))
        core.print_result("Location", data["location"])
        core.print_result("Server", data["server"])
        core.ask_save("host_header_probe", data)
    except Exception as e:
        core.print_error(f"Erreur: {e}")

