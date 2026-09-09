# BlueFox Tools — fondations v3

Préversion de remise en route pour le diagnostic, l’apprentissage et les évaluations autorisées en terminal. La version logicielle provient uniquement de `Program/version.py` (`3.0.0a1`). Ce lot ne constitue pas une validation des fournisseurs OSINT ni une release publiée.

## Ce qui fonctionne dans ce lot

- Démarrage, six catégories, retour, réglages, sortie, Ctrl+C et EOF.
- Catalogue explicite de **51 outils distincts** : 2 `BaseTool`, 49 fonctions historiques conservées derrière une compatibilité temporaire. Les raccourcis entre catégories partagent le même identifiant. `ping_ip` devient un alias de `ping` ; `subnet_calculator` retrouve la catégorie NETWORK.
- Les outils indisponibles restent visibles avec leur cause. Les dépendances d’enrichissement manquantes sont signalées.
- Une configuration commune, des clés saisies sans écho, un thème, un dossier de résultats et 1 à 256 workers.
- `--help`, `--version`, `--no-animation`, `--no-color` et `doctor` local sans réseau.
- Lanceurs utilisant explicitement le Python du venv, depuis un autre dossier et avec des espaces dans les chemins.

Les fonctions historiques restent interactives et conservent leurs limites. Les deux outils migrés ne proposent pas encore l’export commun. Consultez le [suivi des défauts métier](docs/KNOWN_ISSUES.md) avant d’interpréter leurs résultats.

## Installation isolée

Python **3.10 à 3.14** est la cible de cette préversion et de la matrice CI Linux/Windows/macOS. Les vérifications effectivement réalisées sont consignées dans [VALIDATION.md](docs/VALIDATION.md) ; cette matrice ne certifie pas les intégrations réseau.

Linux / macOS, depuis le dépôt :

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[full]"
./start.sh --no-animation
./start.sh doctor
```

Windows, depuis le dépôt :

```bat
setup.bat
start.bat --no-animation
start.bat doctor
```

`setup.bat` crée `.venv` puis installe avec son interpréteur. Les lanceurs ne font aucune installation implicite. Ils privilégient `.venv`, acceptent l’ancien nom `venv`, transmettent les arguments et retournent le code de sortie de Python. Sans venv, ils indiquent la procédure d’installation.

Après activation du venv, la commande `bluefox` est également disponible :

```sh
bluefox --help
bluefox --version
bluefox --no-animation --no-color
bluefox doctor
```

`python -m pip install -r requirements.txt` est une autre entrée vers les mêmes dépendances `[full]`, à exécuter dans le venv depuis le dépôt. Une installation minimale `python -m pip install -e .` permet le démarrage avec `requests` ; le catalogue explique les dépendances manquantes. Réparez l’installation avec l’interpréteur du venv et `-e ".[full]"`.

## Configuration

Le fichier utilisateur sort du code : `$XDG_CONFIG_HOME/bluefox/config.json` (par défaut `~/.config/bluefox/config.json`) sous Linux, `~/Library/Application Support/bluefox/config.json` sous macOS et `%APPDATA%\bluefox\config.json` sous Windows. `BLUEFOX_CONFIG_FILE` permet d’isoler explicitement une configuration.

Priorité : **défauts < fichier local < environnement < options explicites**. Enregistrer un thème ne copie pas les clés d’environnement dans le fichier. Les clés locales restent en clair dans le fichier utilisateur ; la création utilise les droits privés du fichier temporaire sous POSIX et les ACL du dossier sous Windows.

Si le nouveau fichier n’existe pas, l’ancien `Program/bluefox_config.json` est copié sans supprimer l’original. Ses chemins de résultats relatifs sont conservés par conversion en chemins absolus depuis l’ancienne racine du dépôt. `BLUEFOX_CONFIG_FILE` désactive cette migration automatique. Le fichier utilisateur n’est plus suivi par Git ; [un exemple sans clés](Program/bluefox_config.example.json) est fourni. Voir les règles de migration et d’erreur dans le [guide](docs/USAGE.md).

## Organisation

```text
BlueFox.py                 Entrée CLI et menus
Program/ui.py              Affichage, saisie et dispatch
Program/catalogue.py       Inventaire et alias explicites
Program/registry.py        Chargement, disponibilité, catégories
Program/config.py          Gestionnaire partagé et sauvegarde atomique
Program/doctor.py          Diagnostic local
Program/version.py         Version logicielle unique
Program/tools/base.py      Contrat cible BaseTool
Program/tools/             Outils migrés et entrées historiques
Program/legacy_tools.py    Moteurs historiques, encore en migration
Program/extra_tools.py     Autres moteurs historiques
Program/<category>.py      Compatibilité des anciens imports
pyproject.toml             Packaging, dépendances et commande bluefox
tests/                     Régressions sans réseau réel
```

## Documentation

- [Utilisation](docs/USAGE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Inventaire et migration](docs/CATALOGUE.md)
- [Contribution](docs/CONTRIBUTING.md)
- [Changelog](docs/PATCH_NOTES.md)
- [Vérifications et limites](docs/VALIDATION.md)

Usage éducatif et évaluations autorisées uniquement : [avertissement](DISCLAIMER-fr.md). Licence [MIT](LICENSE).

## Donation

Bitcoin:
```
bc1q8urqhsnlt0h43ufs5et5ajxjaekngs6dt3udd7
```
Ethereum:
```
0x9CC941d1A9173867cd50248f2d886C55E265aD98
```
Solana:
```
DAonu76tu3XfyTnGX5MDD1gfLJj9QHYeeNaavu7TB9NQ
```
