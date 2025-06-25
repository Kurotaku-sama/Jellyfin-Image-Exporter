import sys
sys.dont_write_bytecode = True
import os
import json
from config import CONNECTION_FILE
from .jellyfin_api import Jellyfin

class ConnectionEditor:
    @staticmethod
    def clear_screen():
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def edit_or_create_connection_file():
        data = {"url": "", "api_key": "", "library_path": ""}
        if os.path.exists(CONNECTION_FILE):
            try:
                with open(CONNECTION_FILE, "r") as f:
                    data = json.load(f)
            except Exception as e:
                while(True):
                    ConnectionEditor.clear_screen()
                    print(f"ERROR: Connection file is invalid or corrupted.\nReason: {e}")
                    print("\nYou can either fix it manually or recreate it now.")
                    print("Do you want to recreate the file? [y/n]")

                    choice = input("→ ").strip().lower()
                    if choice in ("y", "j"):
                        break
                    elif choice == "n":
                        return

        while True:
            ConnectionEditor.clear_screen()
            print("=== Edit or Create Connection File ===\n")
            print("0. Save and return\n")
            print(f"1. Server URL: {data.get('url', '') or '[is empty – should be edited]'}")
            print(f"2. API Key: {data.get('api_key', '') or '[is empty – should be edited]'}")
            print(f"3. Library Path: {data.get('library_path', '') or '[is empty – should be edited]'}")

            if data.get("library_path") and not os.path.isdir(data["library_path"]):
                print("\nWARNING: The library path is not accessible from this machine!")

            field_choice = input("\nWhich field do you want to edit? ").strip()

            if field_choice == "1":
                ConnectionEditor.clear_screen()
                data["url"] = input("Enter new server URL: ").strip()
            elif field_choice == "2":
                ConnectionEditor.clear_screen()
                data["api_key"] = input("Enter new API key: ").strip()
            elif field_choice == "3":
                ConnectionEditor.clear_screen()
                print("Please enter the full path to the **Jellyfin Metadata folder**.")
                print("This folder usually contains many subfolders with hexadecimal names, like:")
                print("ab | 1f | 3c | a8 | ...")
                print("\nExample paths (not actual paths):")
                print("  - Windows: C:/ProgramData/Jellyfin/metadata/library")
                print("  - Linux: /var/lib/jellyfin/metadata/library")
                print("  - Network Share e.g. Unraid: \\\\Server\\appdata\\jellyfin\\data\\metadata\\library\n")

                data["library_path"] = input("Enter the path to the Jellyfin metadata folder: ").strip()

                if not os.path.isdir(data["library_path"]):
                    print("\nWARNING: The provided path does not exist or is not accessible!\n")
                    input("Press Enter to continue...")
            elif field_choice == "0":
                break

        with open(CONNECTION_FILE, "w") as f:
            json.dump(data, f, indent=4)

        print("Connection file updated.\n")
        input("Press Enter to continue...")
        while True:
            ConnectionEditor.clear_screen()
            print("Would you like to test the connection now? [y/n]")

            choice = input("→ ").strip().lower()
            if choice in ("y", "j"):
                jellyfin = Jellyfin(data.get("url"), data.get("api_key"))
                print("\nTesting connection...\n")
                if jellyfin.test_connection():
                    input("\nConnection successful.\nPress Enter to return to main menu...")
                else:
                    input("\nPress Enter to return to main menu...")
                break
            elif choice == "n":
                return