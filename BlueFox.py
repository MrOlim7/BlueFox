"""BlueFox terminal entrypoint."""
import argparse
import sys

from Program import config, registry, ui
from Program.version import __version__

APP_VERSION = __version__
BANNER = r"""
 ▄▄▄▄    ██▓     █    ██ ▓█████   █████▒▒█████  ▒██   ██▒
▓█████▄ ▓██▒     ██  ▓██▒▓█   ▀ ▓██   ▒▒██▒  ██▒▒▒ █ █ ▒░
▒██▒ ▄██▒██░    ▓██  ▒██░▒███   ▒████ ░▒██░  ██▒░░  █   ░
▒██░█▀  ▒██░    ▓▓█  ░██░▒▓█  ▄ ░▓█▒  ░▒██   ██░ ░ █ █ ▒
░▓█  ▀█▓░██████▒▒▒█████▓ ░▒████▒░▒█░   ░ ████▓▒░▒██▒ ▒██▒
░▒▓███▀▒░ ▒░▓  ░░▒▓▒ ▒ ▒ ░░ ▒░ ░ ▒ ░   ░ ▒ ▒░ ░░   ░▒ ░
▒░▒   ░ ░ ░ ▒  ░░░▒░ ░ ░  ░ ░  ░ ░       ░ ▒ ▒░ ░░   ░▒ ░
 ░    ░   ░ ░    ░░░ ░ ░    ░    ░ ░   ░ ░ ░ ▒   ░    ░
 ░          ░  ░   ░        ░  ░           ░ ░   ░    ░
      ░
"""


def boot_sequence():
    if config.config["animations_enabled"] and ui.interactive():
        print(ui.color("  Chargement du catalogue BlueFox…"))
        ui.delay(0.25)
    # No synthetic diagnostics, RPC startup or Enter gate.


def main_menu():
    ui.clear()
    print(ui.color(BANNER))
    print(ui.color(f"  BlueFox {APP_VERSION} — Network | OSINT | Recon | Intel"))
    keys = list(registry.CATEGORIES)
    for index, key in enumerate(keys, 1):
        cat = registry.CATEGORIES[key]
        available = sum(entry.available for _, entry in cat["tools"])
        print(ui.color(f"  [{index}] {cat['name']} ({available}/{len(cat['tools'])} disponibles)"))
    print(ui.color("  [S] Réglages / API Keys   [D] Doctor local   [Q] Quitter"))
    return keys


def category_menu(key):
    cat = registry.CATEGORIES[key]
    ui.print_header(cat["name"])
    for index, (name, entry) in enumerate(cat["tools"], 1):
        mode = "BaseTool" if entry.kind == "base" else "historique temporaire"
        state = "" if entry.available else f" — INDISPONIBLE : {entry.unavailable_reason}"
        if entry.available and entry.warnings:
            state = " — " + "; ".join(entry.warnings)
        print(ui.color(f"  [{index}] {name} [{entry.id}; {mode}]{state}"))
    print(ui.color("  [B] Retour"))
    return cat["tools"]


run_tool = ui.run_tool


def save_settings():
    if config.config.save():
        ui.print_success("Réglages locaux sauvegardés")
    else:
        ui.print_error(config.config.last_error)
        ui.print_warning("Changements gardés seulement pour cette session")


def hacker_settings():
    manager = config.config
    while True:
        ui.print_header("BLUEFOX — RÉGLAGES")
        ui.print_info(f"Fichier : {manager.path}")
        ui.print_info("Les options explicites et l'environnement restent prioritaires sur le fichier")
        for key, meta in config.API_KEY_FIELDS.items():
            ui.print_result(meta["label"], f"{config.mask_secret(manager[key])} ({manager.source(key)})")
        ui.print_result("Thème", manager["ui_theme"])
        ui.print_result("Résultats", manager.results_path())
        ui.print_result("Workers", manager["max_workers"])
        print(ui.color("  [1] Clés API   [2] Thème   [3] Dossier de résultats   [4] Workers   [B] Retour"))
        try:
            choice = ui.get_input("Choix").lower()
            if choice == "b":
                return
            updates = {}
            if choice == "1":
                ui.print_info("Entrée = conserver ; '-' = supprimer la clé locale")
                for key, meta in config.API_KEY_FIELDS.items():
                    value = ui.get_secret(meta["label"])
                    if value:
                        updates[key] = "" if value == "-" else value
            elif choice == "2":
                value = ui.get_input("Thème (" + ", ".join(config.THEMES) + "; vide = annuler)")
                if value:
                    updates["ui_theme"] = value
            elif choice == "3":
                value = ui.get_input("Dossier (relatif au fichier de config ; vide = annuler)")
                if value:
                    updates["results_folder"] = value
            elif choice == "4":
                value = ui.get_input("Workers (1–256 ; vide = annuler)")
                if value:
                    try:
                        updates["max_workers"] = int(value)
                    except ValueError:
                        raise ValueError("Workers : entier requis") from None
            else:
                ui.print_error("Choix invalide")
                continue
            # Validate the whole edit before committing any field in memory.
            for key, value in updates.items():
                config.validate(key, value)
            for key, value in updates.items():
                manager.set(key, value)
            if updates:
                save_settings()
        except KeyboardInterrupt:
            ui.print_info("Modification annulée")
            return
        except ValueError as exc:
            ui.print_error(exc)


def browse_category(key):
    try:
        while True:
            tools = category_menu(key)
            choice = ui.get_input("Choix").lower()
            if choice == "b":
                return
            if choice.isdigit() and 1 <= int(choice) <= len(tools):
                run_tool(tools[int(choice) - 1][1])
            else:
                ui.print_error("Choix invalide")
    except KeyboardInterrupt:
        ui.print_info("Retour au menu")


def parser():
    command = argparse.ArgumentParser(description="BlueFox — outils en terminal")
    command.add_argument("command", nargs="?", choices=("doctor",), help="diagnostic local sans réseau")
    command.add_argument("--version", action="version", version=f"BlueFox {APP_VERSION}")
    command.add_argument("--no-animation", action="store_true", help="démarrage immédiat sans attente")
    command.add_argument("--no-color", action="store_true", help="désactiver les couleurs")
    command.add_argument("--theme", choices=config.THEMES)
    command.add_argument("--results-folder")
    command.add_argument("--max-workers", type=int)
    return command


def main(argv=None):
    command = parser()
    args = command.parse_args(argv)
    overrides = {key: value for key, value in {
        "ui_theme": args.theme, "results_folder": args.results_folder,
        "max_workers": args.max_workers,
        "animations_enabled": False if args.no_animation else None,
    }.items() if value is not None}
    try:
        config.config.set_overrides(overrides)
    except ValueError as exc:
        command.error(str(exc))
    ui.NO_COLOR = args.no_color
    try:
        if args.command == "doctor":
            from Program.doctor import run_doctor
            return run_doctor()
        for issue in config.config.issues:
            ui.print_warning(issue)
        boot_sequence()
        while True:
            keys = main_menu()
            choice = ui.get_input("Choix").lower()
            if choice == "q":
                print(ui.color(f"  Au revoir — BlueFox {APP_VERSION}"))
                return 0
            if choice == "s":
                hacker_settings()
            elif choice == "d":
                from Program.doctor import run_doctor
                run_doctor()
                ui.pause()
            elif choice.isdigit() and 1 <= int(choice) <= len(keys):
                browse_category(keys[int(choice) - 1])
            else:
                ui.print_error("Choix invalide")
    except EOFError:
        print(ui.color("\n  Fin de l'entrée — au revoir"))
        return 0
    except KeyboardInterrupt:
        print(ui.color("\n  Interrompu — au revoir"))
        return 130


if __name__ == "__main__":
    sys.exit(main())
