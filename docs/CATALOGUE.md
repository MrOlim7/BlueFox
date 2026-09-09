# Inventaire de migration du lot 1

Comparaison avec les 52 fichiers d’outils du commit `5bedac249cbffb3195955c194b6faad431780fa3`, hors `base.py` et `__init__.py`. L’ensemble des modules est couvert par 51 identifiants : 2 classes migrées, 49 entrées historiques. Le test compare les ensembles d’identifiants et les catégories avec `tests/fixtures/catalogue_5bedac2.json`, pas seulement les totaux.

`ping_ip.py` est conservé comme alias interactif de l’ID `ping`, qui exécute `PingTool` : quatre sondes, arguments POSIX/Windows et timeout conservés. L’ancien appel RPC n’est pas initialisé. `ip_lookup.run()` est rétabli comme wrapper interactif de la classe existante ; le moteur et ses défauts API ne sont pas réécrits. Les classes conservent leur dictionnaire actuel et n’offrent pas encore l’export commun.

`subnet_calculator` était orphelin des six listes de catégories. Il retrouve NETWORK et continue d’appeler la fonction historique. Il reste distinct de `netblock_host_counter`, dont le traitement et les résultats diffèrent. Leurs problèmes d’allocation et de sémantique IPv6 restent dans le suivi.

Les apparitions multiples entre catégories sont des raccourcis vers une même instance et un même ID, pas des outils dupliqués. L’ordre des catégories est NETWORK, OSINT, WEB, REPORTS, DISCOVERY, INTEL ; l’ordre des outils est lexicographique par ID. Le libellé « Username Search (50+ sites) » est remplacé par « Username Search » sans modification du moteur.

| ID | Catégories / raccourcis | Mode | Point d’entrée dans `Program.tools` |
|---|---|---|---|
| `asn_info` | NETWORK | legacy | `asn_info.run` |
| `banner_grabber` | DISCOVERY | legacy | `banner_grabber.run` |
| `blacklist_check` | NETWORK | legacy | `blacklist_check.run` |
| `dns_lookup_suite` | DISCOVERY | legacy | `dns_lookup_suite.run` |
| `dns_records` | NETWORK | legacy | `dns_records.run` |
| `dns_resolver_compare` | DISCOVERY | legacy | `dns_resolver_compare.run` |
| `dns_zone_transfer_test` | DISCOVERY | legacy | `dns_zone_transfer_test.run` |
| `domain_osint` | OSINT | legacy | `domain_osint.run` |
| `email_osint` | OSINT | legacy | `email_osint.run` |
| `email_permutations` | OSINT, INTEL | legacy | `email_permutations.run` |
| `favicon_hash` | DISCOVERY | legacy | `favicon_hash.run` |
| `file_hash_audit` | INTEL | legacy | `file_hash_audit.run` |
| `github_dork_pack` | OSINT | legacy | `github_dork_pack.run` |
| `google_dork_generator` | OSINT | legacy | `google_dork_generator.run` |
| `haveibeenpwned` | OSINT | legacy | `haveibeenpwned.run` |
| `host_header_probe` | WEB | legacy | `host_header_probe.run` |
| `http_headers` | WEB | legacy | `http_headers.run` |
| `http_title_probe` | DISCOVERY | legacy | `http_title_probe.run` |
| `image_metadata` | OSINT | legacy | `image_metadata.run` |
| `ioc_analyzer` | INTEL | legacy | `ioc_analyzer.run` |
| `ip_lookup` | NETWORK | base | `ip_lookup.IPLookupTool` |
| `ip_reputation_links` | OSINT, INTEL | legacy | `ip_reputation_links.run` |
| `list_saved_results` | REPORTS | legacy | `list_saved_results.run` |
| `my_ip_info` | NETWORK | legacy | `my_ip_info.run` |
| `netblock_host_counter` | NETWORK, INTEL | legacy | `netblock_host_counter.run` |
| `password_strength_estimator` | INTEL | legacy | `password_strength_estimator.run` |
| `phone_osint` | OSINT | legacy | `phone_osint.run` |
| `ping` | NETWORK | base | `ping.PingTool` |
| `ping_sweep_cidr` | DISCOVERY | legacy | `ping_sweep_cidr.run` |
| `port_scanner` | NETWORK | legacy | `port_scanner.run` |
| `redirect_chain_analyzer` | WEB | legacy | `redirect_chain_analyzer.run` |
| `report_generator` | REPORTS | legacy | `report_generator.run` |
| `reverse_dns` | NETWORK | legacy | `reverse_dns.run` |
| `robots_sitemap_audit` | WEB | legacy | `robots_sitemap_audit.run` |
| `security_txt_audit` | WEB | legacy | `security_txt_audit.run` |
| `shodan_search` | OSINT | legacy | `shodan_search.run` |
| `social_media_lookup` | OSINT | legacy | `social_media_lookup.run` |
| `ssl_cert_info` | WEB | legacy | `ssl_cert_info.run` |
| `subdomain_finder` | OSINT | legacy | `subdomain_finder.run` |
| `subdomain_resolver` | DISCOVERY | legacy | `subdomain_resolver.run` |
| `subnet_calculator` | NETWORK | legacy | `subnet_calculator.run` |
| `tcp_connect_test` | NETWORK | legacy | `tcp_connect_test.run` |
| `tech_stack_detector` | OSINT, WEB | legacy | `tech_stack_detector.run` |
| `tls_version_probe` | NETWORK, INTEL | legacy | `tls_version_probe.run` |
| `traceroute` | NETWORK | legacy | `traceroute.run` |
| `url_recon` | WEB | legacy | `url_recon.run` |
| `username_lookup` | OSINT | legacy | `username_lookup.run` |
| `username_variations` | OSINT, INTEL | legacy | `username_variations.run` |
| `virustotal_check` | OSINT | legacy | `virustotal_check.run` |
| `wayback_machine` | OSINT | legacy | `wayback_machine.run` |
| `whois_lookup` | NETWORK | legacy | `whois_lookup.run` |
