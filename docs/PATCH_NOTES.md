# BlueFox Patch Notes

## Lot 2 — fiabilité, préversion non publiée

- VirusTotal valide HTTP, JSON et statistiques avant interprétation ; analyse absente distincte de zéro détection, sans garantie de sécurité.
- IP Lookup partage la validation entre le moteur et le chemin historique ; schémas incomplets refusés ou signalés comme partiels, enrichissement facultatif indisponible explicite.
- Social lookup exporte aussi les absences apparentes et erreurs ; les HTTP 200 restent des profils possibles, sans confirmation d'identité.
- Calculs CIDR sans énumération, cas IPv4 /31–/32 et IPv6 /127–/128 corrigés ; sweep limité avant consommation à 256 hôtes ; bornes des ports validées avant matérialisation.
- IOC validés avec `ipaddress`, IPv6 reconnu, hôtes des URL analysés sans identifiants/port pour les liens ; types, valeurs et liens conservés dans les exports.
- Exports JSON/CSV/TXT publiés complets sous noms uniques, sans écrasement concurrent ; erreurs remontées, formats inconnus refusés, cellules CSV à risque préfixées par une apostrophe. Rapports précédents exclus des sources, sources illisibles signalées.
- Saisie masquée commune des mots de passe avec espaces conservés ; Pwned Passwords transmet seulement les cinq caractères du préfixe SHA-1 ; aucun secret saisi ni hash complet de mot de passe affiché/exporté. Les charges de BreachDirectory sont limitées au champ source dans l'export. Score de robustesse présenté comme estimation limitée.
- Validation locale Linux Python 3.12.3 : **171 tests réussis, 1 ignoré**, construction wheel/sdist, contrôle des dépendances et syntaxe Bash réussis. Matrice CI de 15 environnements conservée ; état et limites dans [VALIDATION_LOT2.md](VALIDATION_LOT2.md).

## 3.0.0a1 — fondations v3, non publiée

- Répare les imports, les menus, réglages, Ctrl+C/EOF et ajoute aide/version/démarrage rapide sans attente.
- Restaure l’inventaire complet avec 51 IDs, alias Ping et réintégration de Subnet Calculator. Conserve explicitement 49 fonctions historiques interactives et distingue leur dispatch des deux BaseTool.
- Garde les outils indisponibles au catalogue avec leur cause ; ordre stable et doublons refusés.
- Unifie la configuration, valide les types/thèmes/workers et applique défauts < local < environnement < options. Les clés d’environnement ne sont pas copiées lors d’une sauvegarde.
- Rétablit thème/dossier/workers et saisie masquée des clés, conservation/suppression explicite et erreurs de sauvegarde honnêtes. Migration conservant l’original, écriture atomique et protection des JSON illisibles.
- Retire le fichier utilisateur du suivi Git, fournit un exemple vide et sépare la version logicielle.
- Corrige les chemins/interpréteurs/arguments/codes de sortie des lanceurs ; installation isolée explicite et packaging déclaratif avec commande `bluefox`.
- Ajoute un doctor sans réseau, des tests de régression simulés et une matrice CI Linux/Windows/macOS, Python 3.10–3.14.
- Après activation de GitHub Actions : 15/15 jobs exécutés avec succès, 63 tests par version sous Windows et 62 réussis/1 ignoré sous Linux et macOS ; aucune correction applicative nécessaire. Preuves et limites dans le bilan de validation.

Vérifications exécutées et limites : [VALIDATION.md](VALIDATION.md). Bugs métier conservés : [KNOWN_ISSUES.md](KNOWN_ISSUES.md).

## Historique antérieur

Les notes ci-dessous sont conservées comme historique. Leurs affirmations de couverture plateforme, de fiabilité ou de capacités ne valent pas certification de cette préversion ; seule la validation documentée du lot 1 s’applique.

---

## v2.5 beta

### Boot Animation — Complete Rewrite

The startup sequence is now a **4-phase cinematic boot**:

1. **Matrix Rain** — screen fills with random ASCII characters scrolling at speed, setting the hacker atmosphere.
2. **Boot Log Stream** — a bordered box scrolls through detailed system initialization messages: platform detection, Python version, thread pool capacity, API key status, and module imports. A progress bar tracks overall boot progress.
3. **Module Loading Panel** — each internal module (core, network, OSINT, web, intel, discovery, reports, RPC) is displayed with an animated fill bar transitioning from PENDING → LOADING → LOADED.
4. **Logo Reveal + Press Enter** — the BlueFox ASCII banner appears with system info (OS, architecture, Python version), followed by a blinking prompt border.

### macOS Support

- All tools are now fully tested on macOS (Intel and Apple Silicon).
- `my_ip_info()` uses the native `ifconfig` path on Darwin instead of the Linux fallback chain.
- `start.sh` auto-detects the platform and selects the correct Python interpreter (3.10+).
- Documentation updated with macOS-specific installation and troubleshooting steps.
- `traceroute` and `ping` already used POSIX flags compatible with macOS — no changes required.

### Linux / macOS Launcher — `start.sh`

New `start.sh` script:
- Scans for Python 3.10, 3.11, 3.12 in PATH.
- Activates `.venv` or `venv` if found.
- Auto-installs dependencies if `requests` is missing.
- Cross-platform: works on Debian, Ubuntu, Arch, Fedora, macOS.

### UI Improvements

- Improved category cards now show tool count and description inline.
- Settings panel shows API key status with `✓ SET` / `✗ EMPTY` indicators.
- Transition animation replaced with a smoother arrow-flow style.
- System info (OS, arch, Python version) displayed in the main banner on every screen.
- `animated_banner()` refreshes timestamp on each menu visit.

### Minor Fixes

- Boot sequence timing tuned for smoother feel across fast and slow terminals.
- Box drawing characters consistent across all panels (80-char terminal width assumed).
- `center_line()` now accepts explicit width argument for flexible box layouts.
- Various string padding fixes to prevent text overflow in bordered panels.

---

## v2.4 beta

### UI and UX
- Reworked terminal interface with a stronger hacker-style visual identity.
- New startup animation with scrolling code and `Press Enter to Start`.
- Improved menu and submenu presentation.
- Theme selection from settings.

### Architecture
- Refactored category structure and runtime wiring.
- Tool entrypoints split into `Program/tools/` (one file per option).
- Added dedicated category modules (`network`, `osint`, `web`, `discovery`, `intel`, `reports`).

### New Categories
- `Discovery`
- `Intel & Forensics`

### New Tools Added
- IOC Analyzer
- File Hash Audit
- Password Strength Estimator
- Username Variations
- Email Permutations
- IP/Domain Reputation Links
- Netblock Host Counter
- TLS Version Probe
- Host Header Probe
- Security.txt Audit
- Redirect Chain Analyzer
- DNS Resolver Compare
- Plus additional recon helpers in Discovery category

### Fixes and Hardening
- Improved social lookup robustness for special-character usernames.
- Better handling of blocked/limited HTTP statuses in lookup workflows.
- Safer result filename sanitization during export.
- Cleaner RPC shutdown to reduce Windows transport warnings.

---

## v2.3 beta (summary)

- Added persistent local API-key configuration.
- Added web recon capabilities and additional network utilities.
- Began modularization and category cleanup.
