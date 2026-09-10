"""Pwned Passwords range check. Never persist or log the secret or digest."""
import hashlib
import re

import requests


def pwned_count(password):
    digest = hashlib.sha1(password.encode("utf-8")).hexdigest().upper()
    response = requests.get(f"https://api.pwnedpasswords.com/range/{digest[:5]}",
                            headers={"Add-Padding": "true"}, timeout=10)
    if response.status_code != 200 or not response.text.strip():
        raise ValueError("Pwned Passwords: résultat indisponible")
    found = 0
    for line in response.text.splitlines():
        if not re.fullmatch(r"[A-Fa-f0-9]{35}:[0-9]+", line):
            raise ValueError("Pwned Passwords: réponse invalide")
        suffix, count = line.split(":")
        if suffix.upper() == digest[5:]:
            found = int(count)
    return found
