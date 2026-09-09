# Contribuer aux fondations v3

Travaillez sur une branche et proposez une PR décrivant le problème, le comportement obtenu et les contrôles exécutés. Réservez les outils au diagnostic, à l’apprentissage et aux évaluations autorisées.

## Environnement

Depuis le dépôt, créez `.venv`, puis utilisez son Python :

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[full,dev]"
.venv/bin/python -m pytest -q
.venv/bin/python -m build
bash -n start.sh
```

Sous Windows, utilisez `py -3 -m venv .venv`, puis `.venv\Scripts\python.exe` pour les commandes Python ; le contrôle Bash est réservé aux systèmes POSIX. La CI cible Python 3.10–3.14 sur Linux/Windows/macOS. Un job configuré n’est pas une preuve d’exécution : indiquez ses résultats réels dans la PR.

## Migrer un outil

1. Garder son ID dans `Program/catalogue.py` ; ne pas prendre son nom affiché comme identifiant.
2. Implémenter une sous-classe `BaseTool` : pas de `input`, `print`, pause ou export imposé dans `run`. La saisie et la présentation appartiennent à l’UI.
3. Remplacer `kind`, `module`, `entrypoint` de l’entrée existante, conserver ses catégories et documenter toute différence de comportement. Déclarer les dépendances requises/enrichissements dans le registre.
4. Vérifier la conservation des entrées, traitements, données et erreurs avec des fixtures ; mettre à jour l’inventaire et le changelog. Une hausse du nombre d’outils ne prouve pas la conservation du catalogue.
5. Conserver si nécessaire un wrapper interactif temporaire pour les anciens appelants. Ne pas étendre le monolithe et ne pas créer d’adaptateur fabriquant des données structurées à partir de stdout.

Les listes `Program/<category>.py` sont désormais de simples interfaces de compatibilité. N’y ajouter aucun import d’outil : l’inventaire unique commande ces listes. Les doublons d’ID doivent produire une erreur et les imports cassés une entrée indisponible.

## Configuration et tests

Utiliser `Program.config.config`, sans copie des valeurs ni accès direct au JSON. `config.set` modifie la couche locale validée ; `set_overrides` réserve des valeurs à la session. Les chemins d’exports passent par `results_path`. Ne jamais persister une vue fusionnée des couches.

Les tests utilisent une configuration temporaire. Les fixtures globales interdisent HTTP, DNS, sockets et commandes réelles. Simuler explicitement les transports nécessaires avec `monkeypatch`/`Mock`. Les tests qui lancent le CLI utilisent la fixture `process`, qui installe aussi un garde dans les enfants et signale toute tentative réseau, même si l’outil masque l’exception. Ne pas lancer de scan ou de recherche OSINT contre un tiers.

Le test Windows de `setup.bat` simule un échec de pip ; les tests de lanceurs créent un vrai venv et réutilisent les dépendances déjà installées par un fichier `.pth`, sans téléchargement. La validation séparée d’une installation vierge depuis le wheel est consignée dans `VALIDATION.md`.

Le fichier utilisateur `Program/bluefox_config.json` a été retiré du suivi ; `.gitignore` ne retire jamais un fichier déjà suivi. Ne commitez ni clés, ni résultats, ni fichiers d’environnement. Utilisez `bluefox_config.example.json` sans secrets. Aucun historique Git ne doit être réécrit pour ce lot.
