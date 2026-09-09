# Architecture — fondations v3

Le point d’entrée `BlueFox.main(argv)` traite les options puis les menus. `Program.ui` reste léger : bibliothèque standard, gestionnaire de configuration, saisie, affichage avec masquage des clés configurées et dispatch. Il ne dépend pas du monolithe historique. L’import de `Program` n’importe plus `legacy_tools`.

## Registre et compatibilité temporaire

`Program/catalogue.py` constitue l’inventaire explicite : identifiant, nom, catégories, module, point d’entrée, mode `base` ou `legacy`. `ToolRegistry` valide les identifiants et catégories avant les imports, trie par identifiant et construit un seul `ToolEntry` par outil. Un échec d’import renseigne `unavailable_reason` sur l’entrée existante. Les dépendances requises et les enrichissements facultatifs sont distingués. Les commandes système sont détectées par leur présence, sans exécution.

Le dispatch des entrées `base` collecte les entrées, appelle `BaseTool.run(**inputs)` et présente son dictionnaire existant. Ping et IP Lookup sont les deux implémentations migrées. Le contrat existant n’est pas encore l’enveloppe complète proposée par l’audit (`status`, `sources`, temps, etc.). Ce lot ne prétend pas achever cette évolution.

Le dispatch `legacy` appelle directement la fonction interactive et ignore son retour. Il ne capture pas stdout et ne fabrique pas un résultat de succès. Les pauses, exports, erreurs et interactions internes restent ceux de ces fonctions, avec des alias d’UI partagés. Cette compatibilité est **temporaire** : lors de chaque migration, conserver l’ID, remplacer son point d’entrée dans l’inventaire par une classe et vérifier les comportements conservés.

Les six anciens modules de catégorie exportent toujours une liste `TOOLS` de noms et fonctions interactives, en passant par le même registre/dispatch. `Program.tools.ip_lookup.run()` et `ping_ip.run()` sont des wrappers explicites. `ping_ip` est un alias du seul ID `ping`. Les anciennes fonctions directes de `legacy_tools` subsistent pour les anciens appelants ; elles ne constituent pas une seconde inscription au menu.

L’[inventaire détaillé](CATALOGUE.md) et la fixture issue du commit audité rendent visibles les alias, raccourcis intercatégories et l’ancien outil orphelin.

## Configuration unique

`Program.config.config`, `Program.CONFIG`, `Program.settings.CONFIG` et `legacy_tools.CONFIG` désignent le même gestionnaire. L’interface `MutableMapping` maintient temporairement les accès `CONFIG[key]` sans dictionnaire séparé. Les méthodes `load_local_config`/`save_local_config` délèguent au gestionnaire ; le monolithe ne recharge plus la configuration à l’import.

Les couches sont séparées : défauts, JSON local, environnement, options explicites. `set` modifie seulement la couche locale ; `set_overrides` configure la session. Seule la couche locale est sérialisée. Les exports historiques utilisent `config.results_path()`, partagé avec le diagnostic. La version est dans `Program/version.py`, utilisée par l’entrée CLI, les métadonnées du paquet, les rapports et l’agent HTTP historique.

Les erreurs de chargement de modules ne restituent pas le contenu arbitraire des exceptions. L’UI commune masque les valeurs des clés présentes dans les couches de configuration. Cette mesure ne remplace pas la future refonte des requêtes et des exports : les résultats métier historiques ne sont pas validés par ce lot.

## Packaging et diagnostic

`pyproject.toml` est déclaratif et expose `bluefox = BlueFox:main`. `requests` est la dépendance minimale ; `[full]` installe les imports facultatifs historiques et `[dev]` les outils de test/construction. `requirements.txt` et `setup.py` délèguent à ces métadonnées. Aucun fichier utilisateur de configuration ne doit entrer dans les distributions.

`doctor` importe les modules, inspecte les commandes du PATH et teste localement l’écriture. Il ne teste aucune capacité réseau et le démarrage ne déclare plus de pile réseau ou RPC « active ». Discord n’est pas initialisé par l’application. Les tests bloquent le réseau et simulent HTTP, DNS, sockets et commandes pour les parcours qui en ont besoin.
