# Suivi local — défauts hors lot 1

Référence : audit du 9 septembre 2026, commit `5bedac249cbffb3195955c194b6faad431780fa3`. Les moteurs historiques n’ont pas été réécrits. Les entrées ci-dessous restent à corriger/revalider ; leur présence au catalogue ne signifie pas qu’elles sont fiables en ligne.

| Référence | Travail restant |
|---|---|
| B06 | Social lookup : résultat initialisé tardivement, cas tous 404 pouvant lever `UnboundLocalError`. |
| B07 | VirusTotal : ne pas présenter une réponse d’authentification/quota invalide comme aucune détection. |
| B08 | IP Lookup : vérifier statut HTTP, schéma et enrichissements partiels ; certains JSON invalides sont encore traités comme succès. |
| B09 | CIDR sweep et calculateurs : allocations non bornées avant troncature. Ne pas valider de grands réseaux par une exécution réelle. |
| B10 | IOC : IPv4 invalide acceptée ; sémantique IPv6 et réseaux /31, /32, /127, /128 à corriger. |
| B11 | Exports de même nom/seconde : écrasement possible ; écriture des **résultats** encore non atomique. La sauvegarde atomique du lot 1 concerne seulement la configuration. |
| B12–B13 | Configuration suivie et ordre de priorité corrigés dans le lot 1 ; aucun nettoyage de l’historique. Garder ces régressions couvertes. |
| B14 | Clés API : masquage, effacement et contrôle de sauvegarde corrigés. La saisie des **mots de passe des outils historiques** reste à migrer, en préservant les espaces. |
| OSINT | Heuristiques de présence 200/404, redirections, soft-404, preuves et statuts incertains à revoir ; un pseudo identique ne prouve pas une identité. |
| Email | Deux définitions `email_osint` dans le monolithe ; SMTP à rendre explicite, pas une preuve absolue d’existence. |
| Téléphone | Normalisation française et fraîcheur des données d’opérateur à corriger/qualifier. |
| TLS | Exceptions transformées en `not_supported` ; séparer indétermination, réseau et certificat. |
| Mots de passe | Score de robustesse simpliste, notamment `Password123!`. Ne pas certifier sa conclusion. |
| Breach | Clarifier les fournisseurs et données transmises : fonction `haveibeenpwned` utilisant aussi BreachDirectory. |
| Transport | Chemins HTTP historiques, dont NumVerify avec clé en URL ; revalider le HTTPS et les conditions du fournisseur avant release. |
| Exports | Données affichées/exportées divergentes, rapports réingérés, erreurs ignorées et échappement CSV/HTML à traiter. Ping/IP Lookup migrés sans export commun. |
| Validation | Ports, workers propres à certains outils, URL, limites de réponse et suffixes de sous-domaines à borner. |
| Ressources | Fermeture sockets/images, annulation des futures en attente et distinction des erreurs réseau à uniformiser. |
| Architecture | 49 outils interactifs restent à migrer. `requests` est encore requis à l’import du monolithe, y compris pour des outils locaux. |
| Configuration | Pas de verrouillage entre plusieurs sessions ; les ACL Windows dépendent du dossier utilisateur. |
| Produit | Recherche, FR/EN homogène, parcours guidés et enveloppe de résultats complète reportés. |
| Discord | Non initialisé ; future option désactivable et présence générique sans cible à concevoir. |

Priorité du prochain lot : B06–B11 et le reste de B14, puis fiabilisation des transports/exports. Les quotas, tarifs, autorisations des fournisseurs et performances n’ont pas été testés. Aucune nouvelle collecte ou fonctionnalité offensive n’est ajoutée ici.
