from Program import legacy_tools as core


def run():
    url = core.normalize_url(core.get_input("URL cible"))
    if not url:
        return

    core.print_header(f"REDIRECT CHAIN ANALYZER - {url}")
    data = {"url": url, "chain": []}
    try:
        r = core.requests.get(url, timeout=15, allow_redirects=True, headers={"User-Agent": f"BlueFox/{core.__version__}"})
        if r.history:
            for hop in r.history:
                line = {"status": hop.status_code, "url": hop.url, "location": hop.headers.get("Location", "")}
                data["chain"].append(line)
                core.print_result(f"{hop.status_code}", f"{hop.url} -> {hop.headers.get('Location', '')}")
        core.print_result("Final", r.url)
        data["final_url"] = r.url
        data["final_status"] = r.status_code
        core.ask_save("redirect_chain", data)
    except Exception as e:
        core.print_error(f"Erreur: {e}")

