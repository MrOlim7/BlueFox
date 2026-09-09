# Utilisation de la préversion v3

## Démarrer et naviguer

Installez dans un environnement virtuel selon le README. `start.sh` / `start.bat` peuvent être invoqués par leur chemin depuis n’importe quel dossier. `--no-animation` arrive directement au menu et ne demande pas Entrée. L’affichage non interactif n’utilise ni couleurs ni pauses ; `--no-color` ou `NO_COLOR` désactive aussi les couleurs en terminal.

Entrez 1 à 6 pour ouvrir une catégorie, son numéro d’outil pour le lancer, `B` pour revenir, `S` pour les réglages, `D` pour le diagnostic local et `Q` pour quitter. Les identifiants stables et le mode BaseTool/historique sont affichés dans les sous-menus. Les raccourcis d’un outil dans plusieurs catégories partagent sa même implémentation.

Une saisie vide annule un outil BaseTool ; les outils historiques gardent leurs propres invites. Ctrl+C dans un outil l’annule, dans un sous-menu revient au menu, dans les réglages abandonne l’édition en cours. Au démarrage ou au menu principal, Ctrl+C quitte avec 130. EOF quitte proprement avec 0 depuis les menus, réglages et saisies d’outil. Les tâches historiques déjà lancées ne disposent pas encore d’une annulation uniforme de leurs workers.

## Réglages et priorités

`S`, puis `1` : saisie masquée des six clés. Entrée conserve une clé locale ; `-` supprime sa valeur locale. Une clé d’environnement reste prioritaire : retirez la variable puis relancez pour la désactiver. Le panneau indique la provenance de la valeur effective et n’affiche aucun fragment de clé. Si la saisie masquée n’est pas possible, l’édition est refusée plutôt que de retomber sur une saisie visible.

`2` modifie le thème (`blue`, `cyan`, `green`, `red`, `purple`), `3` le dossier des résultats, `4` les workers (entier 1–256). Une saisie vide annule. Les changements locaux sont visibles immédiatement par les deux familles d’outils, sauf si une couche prioritaire les remplace. Après un échec d’écriture, le message précise que les changements restent seulement en mémoire ; aucun succès de sauvegarde n’est annoncé.

| Réglage | Environnement | Option explicite |
|---|---|---|
| Thème | `BLUEFOX_THEME` | `--theme` |
| Résultats | `BLUEFOX_RESULTS_FOLDER` | `--results-folder` |
| Workers | `BLUEFOX_MAX_WORKERS` | `--max-workers` |
| Animation | `BLUEFOX_ANIMATIONS` (`true`/`false` ou `1`/`0`) | `--no-animation` |
| IPGeolocation | `IPGEO_API_KEY` | — |
| AbuseIPDB | `ABUSEIPDB_API_KEY` | — |
| Shodan | `SHODAN_API_KEY` | — |
| VirusTotal | `VIRUSTOTAL_API_KEY` | — |
| Hunter.io | `HUNTER_API_KEY` | — |
| NumVerify | `NUMVERIFY_API_KEY` | — |

Les options de lancement sont temporaires. L’environnement est lu au chargement du gestionnaire. Le JSON exige des types natifs : workers entier, animation booléen, clés/dossier/thème chaînes. Les valeurs invalides sont diagnostiquées sans afficher leur contenu ; la dernière couche valide reste utilisée. Les valeurs locales invalides et les champs inconnus sont conservés dans le fichier pour ne pas perdre les données de l’utilisateur.

## Fichier et migration

Les emplacements par OS figurent dans le README ; `doctor` affiche le chemin effectif. Tous les nouveaux chemins de résultats relatifs, y compris ceux fournis par une option, sont interprétés relativement au dossier de ce fichier, indépendamment du dossier courant.

La migration automatique ne s’applique que si la nouvelle configuration est absente et si `BLUEFOX_CONFIG_FILE` n’est pas défini. Elle copie les données locales, retire la version logicielle du JSON et convertit le chemin des anciens résultats relativement à la racine du dépôt. L’original est conservé. La nouvelle configuration existante prend ensuite le relais ; aucune fusion répétée de l’ancien fichier n’est faite. Lors d’une mise à jour Git, sauvegardez votre ancien fichier local personnalisé avant le changement de branche/version si Git signale un conflit : l’application ne peut migrer que ce qui est encore présent sur disque.

Le chemin explicite permet aussi une migration manuelle : copiez le fichier d’exemple ou votre ancienne configuration vers ce chemin et adaptez son dossier de résultats. Ne placez pas de clés dans un fichier suivi.

La sauvegarde écrit un fichier temporaire dans le même dossier, force son contenu sur disque puis le remplace atomiquement. En cas d’échec, le fichier précédent reste intact. Un JSON corrompu, une racine JSON non objet ou un fichier illisible déclenche l’utilisation des défauts/environnement et bloque la sauvegarde : réparez ou sauvegardez/déplacez le fichier avant de recharger. Les erreurs de droits sont signalées sans contenu secret. Il n’y a pas de verrouillage entre deux sessions concurrentes : la dernière sauvegarde réussie l’emporte.

## Diagnostic et dépendances

`bluefox doctor` vérifie localement Python, les imports des dépendances, la présence de ping/traceroute/nslookup et des commandes d’informations réseau, la configuration et la création d’un fichier temporaire dans les dossiers de configuration et de résultats. Il peut créer ces dossiers ; il ne lance aucune commande système, requête HTTP, résolution DNS, connexion de socket ou présence Discord. Code 0 si tous ses contrôles passent, 1 s’il manque un composant ou si un avertissement subsiste.

Une commande facultative absente n’empêche pas le menu. Un composant Python requis manquant laisse l’outil visible comme indisponible ; certains enrichissements restent facultatifs et sont signalés séparément. `requests` est encore importé par le monolithe historique, donc son absence rend aussi des outils locaux historiques indisponibles. `doctor` explique ce cas ; les futurs lots doivent supprimer ce couplage.

Les clés ne sont pas nécessaires pour démarrer, mais certains outils en exigent une. Le diagnostic ne vérifie pas l’authentification, les quotas, la disponibilité des fournisseurs ou l’exactitude des résultats. Les appels réseau ne commencent qu’au lancement explicite d’un outil. Voir [KNOWN_ISSUES.md](KNOWN_ISSUES.md), notamment les réponses API invalides encore mal interprétées et les anciens chemins HTTP.
