from Program import legacy_tools as core


def run():
    target = core.normalize_url(core.get_input("Domaine ou URL"))
    if not target:
        return
    parsed = core.urlparse(target)
    base = f"{parsed.scheme}://{parsed.netloc}"
    url = f"{base}/.well-known/security.txt"

    core.print_header(f"SECURITY.TXT AUDIT - {parsed.netloc}")
    data = {"url": url}
    try:
        r = core.requests.get(url, timeout=10, headers={"User-Agent": f"BlueFox/{core.__version__}"})
        data["status_code"] = r.status_code
        data["length"] = len(r.text)
        if r.status_code == 200 and r.text.strip():
            core.print_success("security.txt trouve")
            lines = [line.strip() for line in r.text.splitlines() if line.strip() and not line.strip().startswith("#")]
            important = [l for l in lines if l.lower().startswith(("contact:", "expires:", "encryption:", "policy:"))]
            for line in important[:15]:
                core.print_result("entry", line)
            data["entries"] = important
        else:
            core.print_warning(f"security.txt absent ({r.status_code})")
        core.ask_save(f"security_txt_{parsed.netloc}", data)
    except Exception as e:
        core.print_error(f"Erreur: {e}")

