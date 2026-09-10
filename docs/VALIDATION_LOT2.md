# Validation du lot 2 — fiabilité et données locales

## Base et préservation du travail local

Le 10 septembre 2026, la [PR #3](https://github.com/MrOlim7/BlueFox/pull/3) est ouverte en brouillon, sans fusion. Après `git fetch origin`, la branche locale et `origin/fix/v3-foundation` pointent sur `bc9e4a3207364dc023a4211e4b5c683d513bd4f6`. Le lot 2 part de ce commit sur `fix/v3-reliability`, dans le dossier initial BlueFox, sans nouveau worktree. La [PR #4](https://github.com/MrOlim7/BlueFox/pull/4), créée en brouillon, cible `fix/v3-foundation` et dépend de #3.

Les deux documents non suivis `BlueFox-v3-audit-et-prompt.md` et `BlueFox-v3-lot2-prompt.md` restent non suivis et leurs SHA-256 sont inchangés. Le stash `eb611b435929136df763c693150d1e3b94059153` n'a été ni appliqué ni supprimé. La sauvegarde existante `BlueFox-local-backup-20260910-191837` n'a pas été modifiée. Aucune fusion, release ou modification des réglages GitHub.

## Défauts revérifiés et preuves

Les lectures du code de base ont confirmé les défauts avant modification. Les régressions ci-dessous utilisent uniquement des réponses et transports simulés ; aucun scan, DNS public, service OSINT ou API métier réel n'a été appelé.

| Défaut confirmé | Correction et validation |
|---|---|
| VirusTotal ignorait HTTP et remplaçait toute statistique absente par zéro. | Statut 200 et objets JSON requis ; compteurs entiers non négatifs et au moins une analyse exploitable. Tests 401/429/404/503, JSON invalide, timeout, objets absents/incomplets, statistiques nulles et quatre modes avec détections ou zéro détection. Zéro reste une observation sans garantie de sécurité. |
| IP Lookup acceptait `{}` et remplissait des `N/A` ; enrichissement perdu ou silencieux. | Validation de status/query/pays/ISP/coordonnées ; autres champs absents signalés, enrichissement optionnel indisponible explicite. Chemin historique délégué au même moteur. Tests d'erreurs HTTP/JSON, types/champs incohérents, résultat complet et partiel, identité des données exportées par le chemin historique. |
| Social lookup initialisait l'export seulement si un profil était trouvé. | Export inconditionnel avec listes et nombres de profils possibles, absences apparentes et erreurs. Tests tous 404, soft-404, tous 200, 429/500 et timeouts. Aucun HTTP 200 ne confirme un profil ou une identité. |
| CIDR et compteur matérialisaient les hôtes ; calcul IPv6 utilisait les règles IPv4. | Arithmétique reproduisant les bornes de `ipaddress.hosts()` ; /31, /32, /127 et /128 vérifiés. Tests /8 IPv4 et /64 IPv6 interdisant tout appel à `hosts()` dans les calculateurs. Le sweep utilise `islice(..., 256)` ; générateur de test levant immédiatement au 257e hôte, commandes ping simulées. |
| Plages de ports étendues avant validation. | Validation 1 ≤ début ≤ fin ≤ 65535, déduplication bornée pour TCP Connect. Tests limites, inversion, saisies invalides et nombres énormes ; aucun transport appelé pour les plages refusées. Limites/capacité de scan inchangées. |
| Regex IPv4 acceptant 999.999.999.999 et IPv6 absent ; liens URL bâtis depuis netloc. | Classification par `ipaddress`, hostname analysé, port d'URL validé, conservation des types/valeurs/liens dans l'export. Tests IP invalides, IPv6 y compris IPv4 mappée, domaines/email/hash, URL avec identifiants/port et IPv6 entre crochets. Aucun enrichissement réseau ajouté. |
| Exports et rapports écrasables, fichiers partiels, erreurs silencieuses, rapports réingérés. | Écriture temporaire dans le dossier destination, flush/fsync puis publication par lien physique atomique sans remplacement. Tests de 64 exports concurrents dans une seconde figée, collision forcée, erreurs de création/écriture/fsync/publication, absence de succès et de fichiers finaux partiels. Formats inconnus refusés, anciennes sorties REPORT et marqueurs de rapport exclus, source JSON invalide signalée. Les rapports TXT acceptent aussi des sources listes/scalaires. |
| CSV interprétable comme formules. | Préfixe apostrophe pour cellules commençant par =, +, -, @ ou contrôles, y compris après espaces. Tests de lecture CSV et conservation exacte des valeurs dans JSON. |
| Deux saisies de mots de passe visibles et dépouillées de leurs espaces. | `get_secret` commun sans strip. Tests getpass, longueur avec espaces, mot de passe composé d'espaces, SHA-1 exact et requête limitée aux cinq premiers caractères. Tests absence du secret/digest complet dans requête, affichage et export, même sur exception ; réponse Pwned Passwords invalide distincte d'absence. Le résultat brut BreachDirectory n'est plus exporté : seul le champ source est conservé. Estimation de robustesse explicitement limitée. |

## Contrôles locaux exécutés

Linux, Python 3.12.3, environnement `.venv` existant :

- Première passe ciblée HTTP/réseau/configuration : **81 réussis**.
- Première passe ciblée exports/IOC/secrets : **40 réussis**.
- Suite complète après ajout des derniers cas : **171 réussis, 1 ignoré** (`test_windows_setup_propagates_install_failure`, réservé à Windows).
- `python -m build` : wheel et sdist construits ; `python -m pip check`, `bash -n start.sh` et `git diff --check` réussis.
- Catalogue, alias, configuration unique, migration et lanceurs contrôlés par les tests existants. Aucun changement de leurs fichiers ni du workflow de la matrice 15 environnements.

Les quatre nouveaux fichiers `tests/test_reliability_*.py` couvrent les risques corrigés avec les gardes réseau du lot 1. Le mock de configuration existant a été mis à jour pour fournir un statut HTTP et un schéma primaire valides.

## CI

La matrice existante Linux/Windows/macOS × Python 3.10–3.14 est conservée. Le [run 34509287470](https://github.com/MrOlim7/BlueFox/actions/runs/34509287470), déclenché sur la PR #4 pour le commit `299e13ad086310527ccf2a0eb8ce7ebfb2ea25ec`, est terminé avec **15/15 jobs réussis**. Les journaux des 15 jobs ont été lus :

| Runner | Python | Pytest par version | Distributions |
|---|---|---|---|
| ubuntu-latest | 3.10, 3.11, 3.12, 3.13, 3.14 | 171 réussis, 1 ignoré | wheel + sdist réussis dans les 5 jobs |
| windows-latest | 3.10, 3.11, 3.12, 3.13, 3.14 | 172 réussis, aucun ignoré | wheel + sdist réussis dans les 5 jobs |
| macos-latest | 3.10, 3.11, 3.12, 3.13, 3.14 | 171 réussis, 1 ignoré | wheel + sdist réussis dans les 5 jobs |

Le test réservé à Windows explique l'unique différence de compte. Cette preuve porte sur le code du lot 2, sans réutiliser les succès du lot 1. La présente consignation modifie uniquement la documentation ; la description de la PR indique aussi le contrôle du dernier commit publié.

## Limites et travail reporté

- Aucun résultat métier en ligne, quota fournisseur ni résistance réelle d'un mot de passe n'est certifié. Les heuristiques sociales restent approximatives (redirections, pages de connexion, soft-404). La source primaire IP conserve son transport HTTP historique.
- Les liens physiques sont requis pour publier un résultat sans écrasement ; un système de fichiers qui ne les prend pas en charge produit une erreur explicite. JSON et TXT d'un rapport sont chacun atomiques, sans transaction commune : si TXT échoue, le JSON complet déjà publié reste disponible. Une interruption brutale peut laisser un temporaire `.bluefox-*.tmp`, jamais utilisé comme source JSON. La durabilité après coupure électrique n'est pas certifiée.
- L'apostrophe CSV modifie volontairement la représentation de cellules à risque ; JSON conserve les types/valeurs. Pas de nouveau format HTML ni de nouveau système complet de rapports. Les exports historiques déjà sur disque ne sont pas réécrits.
- La refonte des 49 outils historiques, l'enveloppe commune de résultats, l'export des BaseTool, le score de mots de passe avancé, les autres transports/validations et les autres points de KNOWN_ISSUES restent reportés. Le lot 3 n'est pas commencé et la v3 finale n'est pas annoncée.
