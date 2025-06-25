import sys
sys.dont_write_bytecode = True
import os
from .version_checker import VersionChecker
from .menu_library import MenuLibrary
from .connection_editor import ConnectionEditor
from config import VERSION

class MenuMain:
    @staticmethod
    def clear_screen():
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def show_main_menu():
        while True:
            MenuMain.clear_screen()
            print(f"=== Jellyfin Image Exporter {VERSION + ' ' if VERSION else ''}by Kurotaku===\n")
            print("0. Exit")
            print("1. Read from connection file")
            print("2. Connect via user input")
            print("3. Create or edit connection file")
            print("4. Generate automation command")
            print("5. Check for updates")
            print()

            choice = input("→ ").strip()
            {
                "0": lambda: [MenuMain.clear_screen(), sys.exit()][1],
                "1": lambda: MenuLibrary.connect_and_show_menu("file"),
                "2": lambda: MenuLibrary.connect_and_show_menu("user"),
                "3": ConnectionEditor.edit_or_create_connection_file,
                "4": lambda: MenuLibrary.connect_and_show_menu("auto"),
                "5": VersionChecker.check_for_updates
            }.get(choice, lambda: None)()