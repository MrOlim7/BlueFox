import math
import string

from Program import legacy_tools as core


def run():
    pwd = core.get_secret("Mot de passe a auditer (local only)")
    if not pwd:
        return

    core.print_header("PASSWORD STRENGTH ESTIMATOR")
    core.print_warning("Estimation limitée : longueur et classes de caractères seulement. "
                       "Dictionnaires et réutilisation non évalués ; aucune résistance démontrée.")
    charset = 0
    if any(c.islower() for c in pwd):
        charset += 26
    if any(c.isupper() for c in pwd):
        charset += 26
    if any(c.isdigit() for c in pwd):
        charset += 10
    if any(c in string.punctuation for c in pwd):
        charset += len(string.punctuation)

    entropy = round(len(pwd) * math.log2(max(charset, 1)), 2) if charset else 0.0
    score = 0
    score += 1 if len(pwd) >= 8 else 0
    score += 1 if len(pwd) >= 12 else 0
    score += 1 if any(c.islower() for c in pwd) else 0
    score += 1 if any(c.isupper() for c in pwd) else 0
    score += 1 if any(c.isdigit() for c in pwd) else 0
    score += 1 if any(c in string.punctuation for c in pwd) else 0

    level = "Very Weak"
    if score >= 5 and entropy >= 50:
        level = "Score élevé (estimation limitée)"
    elif score >= 4 and entropy >= 40:
        level = "Medium"
    elif score >= 3:
        level = "Weak"

    data = {
        "length": len(pwd),
        "charset_size": charset,
        "entropy_bits": entropy,
        "score_6": score,
        "level": level,
    }
    core.print_result("Length", str(data["length"]))
    core.print_result("Charset", str(data["charset_size"]))
    core.print_result("Entropie théorique (tirage uniforme supposé)", f"{entropy} bits")
    core.print_result("Score", f"{score}/6")
    core.print_result("Level", level)

    core.print_info("Aucun mot de passe n'est sauvegarde.")

