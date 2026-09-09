# Validation du lot 1

## Référence revérifiée

Le 9 septembre 2026, `main` local et `origin/main` pointaient tous deux sur `5bedac249cbffb3195955c194b6faad431780fa3` (v2.5.1). Aucune version plus récente que la préversion proposée n’apparaissait dans les tags examinés. Le répertoire initial contenait du travail non commité, notamment OSINT ; il a été conservé intact. Le lot a été réalisé dans le worktree séparé `BlueFox-foundation`, branche `fix/v3-foundation`, à partir du commit vérifié. Il ne mélange pas ces changements locaux à la PR.

Avant correction, après installation réelle des sept dépendances de l’ancien `requirements.txt` dans un venv Linux Python 3.12.3 :

| Sonde réelle | Observation |
|---|---|
| `import BlueFox` | `ImportError` sur `Program.ui` |
| `import Program.registry` | NETWORK : IP Lookup, Ping IP ; cinq catégories vides |
| `import Program.network` | `AttributeError` sur `ip_lookup.run` |
| Formatage réglages | `config.mask_secret` absent |
| Configuration partagée | Ancien dictionnaire et nouveau gestionnaire distincts |

Le fichier utilisateur était toujours suivi, les lanceurs dépendaient du dossier courant, les réglages ne proposaient que les clés, les versions étaient divergentes et le commit ne contenait ni tests ni CI. Aucun appel à un fournisseur ni scan n’a été nécessaire pour confirmer ces constats.

## Contrôles exécutés localement

Environnement : Linux, Python 3.12.3, installation dans `.venv` avec `python -m pip install -e ".[full,dev]"`.

- Import réel de `BlueFox`, du registre et des six catégories avec les dépendances installées : réussi ; 51 identifiants et un gestionnaire identique pour les deux familles.
- `python -m pytest -q` : **62 réussis, 1 ignoré**. Le test ignoré exige Windows pour `setup.bat`.
- Inventaire comparé aux modules et à la fixture des six anciennes catégories ; alias Ping, orphelin Subnet Calculator, ordre déterministe, doublons refusés, imports et dépendances facultatives absents sans disparition du catalogue.
- Navigation automatique réelle en processus enfant : aide, version, démarrage rapide, six catégories, réglages, sortie et EOF. Annulations Ctrl+C testées par exceptions simulées aux points d’entrée, saisies et appels d’outils.
- Configuration : partage immédiat, appel HTTP simulé utilisant la même clé dans les deux familles, priorités, suppression, saisie masquée/conservation, JSON invalide, types/bornes, échec de remplacement et permissions simulés, migration conservant l’original, absence de persistance involontaire des clés d’environnement.
- Ping simulé pour Windows/Linux/macOS, reverse DNS simulé par socket et DNS Lookup Suite simulé par résolveur. Les transports réels sont interdits par les fixtures, y compris dans les enfants CLI.
- `start.sh` exécuté depuis un autre dossier dans un chemin avec espaces, avec un vrai venv : démarrage, arguments intacts, interpréteur du venv et propagation d’un code 37 vérifiés ; absence de venv diagnostiquée.
- `bash -n start.sh`, `git diff --check` et `python -m pip check` : réussis.
- `bluefox doctor` réel : imports et écriture locale réussis, `traceroute` absent correctement signalé. Aucun diagnostic réseau effectué.

- `python -m build` : sdist et wheel construits avec succès. Inspection des deux archives : pas de `Program/bluefox_config.json` ; exemple vide présent dans le wheel, fixture d’inventaire présente dans le sdist.
- Installation du wheel `[full]` dans un **second venv vierge** hors dépôt : réussie. Depuis un autre dossier, import confirmé depuis `site-packages`, 51 outils, même gestionnaire, `bluefox --version`, `--help`, parcours catégorie/réglages/sortie et `doctor` exécutés avec un garde réseau. Aucun appel interdit détecté ; `doctor` retourne 1 pour Traceroute absent.

Dépendances réellement résolues localement : requests 2.34.2, pystyle 2.9, python-whois 0.9.6, dnspython 2.8.0, beautifulsoup4 4.15.0, Pillow 12.3.0, pypresence 4.6.2 ; pytest 9.1.1, build 1.6.0. Ces versions décrivent cette exécution, pas un verrouillage universel des dépendances.

## Limites

Windows et macOS ne sont pas disponibles dans cet environnement local. La CI configure 15 combinaisons (3 OS × Python 3.10–3.14) ; tant que les jobs ne sont pas terminés, leur présence n’est pas une validation. Les tests `.bat` ne s’exécutent que sous Windows. Les permissions sont simulées pour rester fiables même avec des droits élevés ; le remplacement atomique et les droits POSIX du fichier créé sont testés réellement sous Linux.

Les dépendances ont été téléchargées pour l’installation, mais aucun outil n’a interrogé un tiers : pas de recherche OSINT, scan, DNS public, API métier ou connexion Discord. Les intégrations, quotas, tarifs et performances ne sont pas certifiés. Les bugs métier et limitations de migration sont explicités dans [KNOWN_ISSUES.md](KNOWN_ISSUES.md). Les tests portent sur la remise en route et la compatibilité, pas sur les 49 moteurs historiques dans tous leurs cas. Une compilation syntaxique n’est pas utilisée comme preuve de démarrage.
