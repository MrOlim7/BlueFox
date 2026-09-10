# Suivi local — après le lot 2

Référence : audit du 9 septembre 2026, commit `5bedac249cbffb3195955c194b6faad431780fa3`. Les moteurs historiques n’ont pas été réécrits. B06–B11 et les saisies secrètes de B14 sont corrigés dans le lot 2 et testés avec des transports simulés ; leur présence au catalogue ne certifie pas leur fonctionnement en ligne. Voir [le bilan du lot 2](VALIDATION_LOT2.md).

| Référence | Travail restant |
|---|---|
| B06 | Corrigé : export toujours initialisé, absences apparentes/erreurs/profils possibles séparés. Heuristiques propres aux plateformes à approfondir. |
| B07 | Corrigé : HTTP/JSON/statistiques validés ; zéro détection sans garantie de sécurité. |
| B08 | Corrigé : moteur partagé avec le chemin historique, schéma primaire validé, résultats partiels signalés. Source primaire HTTP historique conservée. |
| B09 | Corrigé : limite de 256 avant consommation du sweep, calculateurs par arithmétique ; tests /8 IPv4 et /64 IPv6 sans énumération. |
| B10 | Corrigé : IPv4/IPv6 validés avec ipaddress ; bornes /31, /32, /127, /128 testées ; hostname des URL pour les liens. |
| B11 | Corrigé : fichiers complets publiés par lien physique atomique sans remplacement, noms uniques et erreurs explicites. Systèmes de fichiers sans liens physiques refusés ; pas de transaction JSON+TXT globale. |
| B12–B13 | Configuration suivie et ordre de priorité corrigés dans le lot 1 ; aucun nettoyage de l’historique. Garder ces régressions couvertes. |
| B14 | Corrigé : saisie masquée commune dans les deux outils de mots de passe, espaces conservés, requête Pwned Passwords par préfixe seulement. |
| OSINT | Heuristiques de présence 200/404, redirections, soft-404, preuves et statuts incertains à revoir ; un pseudo identique ne prouve pas une identité. |
| Email | Deux définitions `email_osint` dans le monolithe ; SMTP à rendre explicite, pas une preuve absolue d’existence. |
| Téléphone | Normalisation française et fraîcheur des données d’opérateur à corriger/qualifier. |
| TLS | Exceptions transformées en `not_supported` ; séparer indétermination, réseau et certificat. |
| Mots de passe | Score toujours simpliste (ex. Password123!) ; avertissement explicite ajouté. Aucune résistance démontrée. |
| Breach | Clarifier les fournisseurs et données transmises : fonction `haveibeenpwned` utilisant aussi BreachDirectory. |
| Transport | Chemins HTTP historiques, dont NumVerify avec clé en URL ; revalider le HTTPS et les conditions du fournisseur avant release. |
| Exports | Corrigé dans le lot 2 : collisions, écritures partielles, erreurs ignorées, réingestion des rapports et formules CSV. Enveloppe complète et export commun des BaseTool reportés ; aucun export HTML ajouté. |
| Validation | Bornes des plages de ports matérialisées corrigées. Autres workers, URL, limites de réponse et suffixes de sous-domaines restent à borner. |
| Ressources | Fermeture sockets/images, annulation des futures en attente et distinction des erreurs réseau à uniformiser. |
| Architecture | 49 outils interactifs restent à migrer. `requests` est encore requis à l’import du monolithe, y compris pour des outils locaux. |
| Configuration | Pas de verrouillage entre plusieurs sessions ; les ACL Windows dépendent du dossier utilisateur. |
| Produit | Recherche, FR/EN homogène, parcours guidés et enveloppe de résultats complète reportés. |
| Discord | Non initialisé ; future option désactivable et présence générique sans cible à concevoir. |

Restent notamment la fiabilisation générale des transports, les heuristiques OSINT et la migration des outils. Le lot 3 n’a pas commencé. Les quotas, tarifs, autorisations des fournisseurs et performances n’ont pas été testés. Aucune nouvelle collecte ou fonctionnalité offensive n’est ajoutée ici.
