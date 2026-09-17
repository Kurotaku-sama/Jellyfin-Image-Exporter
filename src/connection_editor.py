import sys
sys.dont_write_bytecode = True
import os
from .settings import Settings
from .jellyfin_api import Jellyfin
from .colors import Colors

class ConnectionEditor:
    @staticmethod
    def clear_screen():
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def edit_or_create_connection_file():
        settings = Settings.load()

        while True:
            ConnectionEditor.clear_screen()
            print(Colors.wrap("=== Edit Config ===", Colors.CYAN, Colors.BOLD) + "\n")
            print("0. Save and return\n")
            print(f"1. Server URL: {settings.get('url', '') or '[is empty - should be edited]'}")
            print(f"2. API Key: {settings.get('api_key', '') or '[is empty - should be edited]'}")
            print(f"3. Library Path: {settings.get('library_path', '') or '[is empty - should be edited]'}")
            print(f"4. Colored Output: {'Enabled' if Settings.is_colored_enabled(settings) else 'Disabled'}")

            if settings.get("library_path") and not os.path.isdir(settings["library_path"]):
                print(Colors.wrap("\nWARNING: The library path is not accessible from this machine!", Colors.YELLOW))

            field_choice = input("\nWhich field do you want to edit? ").strip()

            if field_choice == "1":
                ConnectionEditor.clear_screen()
                print(Colors.wrap("=== Server URL ===", Colors.CYAN, Colors.BOLD) + "\n")
                if settings.get("url"):
                    print(f"Current: {settings['url']}\n")
                new_value = input("Enter new server URL (0 to cancel): ").strip()
                if new_value == "0":
                    continue
                settings["url"] = new_value
            elif field_choice == "2":
                ConnectionEditor.clear_screen()
                print(Colors.wrap("=== API Key ===", Colors.CYAN, Colors.BOLD) + "\n")
                if settings.get("api_key"):
                    print(f"Current: {settings['api_key']}\n")
                new_value = input("Enter new API key (0 to cancel): ").strip()
                if new_value == "0":
                    continue
                settings["api_key"] = new_value
            elif field_choice == "3":
                ConnectionEditor.clear_screen()
                print(Colors.wrap("=== Library Path ===", Colors.CYAN, Colors.BOLD) + "\n")
                print("Please enter the full path to the **Jellyfin Metadata folder**.")
                print("This folder usually contains many subfolders with hexadecimal names, like:")
                print("ab | 1f | 3c | a8 | ...")
                print("\nExample paths (not actual paths):")
                print("  - Windows: C:/ProgramData/Jellyfin/metadata/library")
                print("  - Linux: /var/lib/jellyfin/metadata/library")
                print("  - Network Share e.g. Unraid: \\\\Server\\appdata\\jellyfin\\data\\metadata\\library\n")

                if settings.get("library_path"):
                    print(f"Current: {settings['library_path']}\n")
                new_value = input("Enter the path to the Jellyfin metadata folder (0 to cancel): ").strip()
                if new_value == "0":
                    continue
                settings["library_path"] = new_value

                if not os.path.isdir(settings["library_path"]):
                    print(Colors.wrap("\nWARNING: The provided path does not exist or is not accessible!\n", Colors.YELLOW))
                    input("Press Enter to continue...")
            elif field_choice == "4":
                ConnectionEditor.clear_screen()
                print(Colors.wrap("=== Colored Output ===", Colors.CYAN, Colors.BOLD) + "\n")
                print(f"Current: {'Enabled' if Settings.is_colored_enabled(settings) else 'Disabled'}\n")
                print("1. Enabled")
                print("2. Disabled")
                color_choice = input("\nChoose an option (0 to cancel): ").strip()
                if color_choice == "1":
                    settings["colored"] = "True"
                    Colors.ENABLED = True
                elif color_choice == "2":
                    settings["colored"] = "False"
                    Colors.ENABLED = False
            elif field_choice == "0":
                break

        Settings.save(settings)

        print(Colors.wrap("Config updated.\n", Colors.GREEN))
        input("Press Enter to continue...")
        while True:
            ConnectionEditor.clear_screen()
            print("Would you like to test the connection now? [y/n]")

            choice = input("→ ").strip().lower()
            if choice in ("y", "j"):
                jellyfin = Jellyfin(settings.get("url"), settings.get("api_key"))
                print(Colors.wrap("\nTesting connection...\n", Colors.CYAN))
                if jellyfin.test_connection():
                    input(Colors.wrap("Connection successful.\n\n", Colors.GREEN) + "Press Enter to return to main menu...")
                else:
                    input("Press Enter to return to main menu...")
                break
            elif choice == "n":
                return