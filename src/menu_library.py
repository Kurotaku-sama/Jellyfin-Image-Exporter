
import sys
sys.dont_write_bytecode = True
import os
import json
from .jellyfin_api import Jellyfin
from .export_prompts import ExportPrompts
from .export_prepare import ExportPrepare
from .auto_generator import AutoGenerator
from config import CONNECTION_FILE

class MenuLibrary:
    @staticmethod
    def clear_screen():
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def connect_and_show_menu(mode):
        """
        Handles Jellyfin connection and starts the library menu.

        Args:
            mode (str): "file", "user" or "auto"
        """
        automation_mode = (mode == "auto")

        if mode == "file":
            MenuLibrary._connect_via_connection_file(automation_mode)
        elif mode == "user":
            MenuLibrary._connect_via_user_input(automation_mode)
        elif mode == "auto":
            # AUTO-Modus Logik
            if MenuLibrary._can_connect_with_file():
                MenuLibrary._connect_via_connection_file(automation_mode)
            else:
                MenuLibrary._connect_via_user_input(automation_mode)
        else:
            print(f"Unknown connection mode: {mode}")
            input("Press Enter to continue...")

    @staticmethod
    def _can_connect_with_file():
        """Check if we can connect using connection file"""
        if not os.path.exists(CONNECTION_FILE):
            return False

        try:
            with open(CONNECTION_FILE, "r") as f:
                data = json.load(f)

            # Minimal validation
            if not all(data.get(key) for key in ["url", "api_key", "library_path"]):
                return False

            # Test connection
            jellyfin = Jellyfin(data["url"], data["api_key"])
            return jellyfin.test_connection()
        except Exception:
            return False

    @staticmethod
    def _connect_via_connection_file(automation_mode=False):
        if not os.path.exists(CONNECTION_FILE):
            print("Connection file not found. Please create it via menu option 3.")
            input("Press Enter to return to main menu...")
            return

        try:
            with open(CONNECTION_FILE, "r") as f:
                data = json.load(f)
        except Exception as e:
            MenuLibrary.clear_screen()
            print(f"ERROR: Connection file is invalid or corrupted.\nReason: {e}")
            input("Press Enter to return to main menu...")
            return

        library_path = data.get("library_path", "")
        if not os.path.isdir(library_path):
            print("WARNING: The library path is not accessible from this machine!")
            input("Press Enter to continue...")

        # Pass library_path to Jellyfin constructor
        jellyfin = Jellyfin(
            url=data.get("url"),
            api_key=data.get("api_key"),
            library_path=library_path
        )

        if jellyfin.test_connection():
            MenuLibrary.show_library_menu(jellyfin, automation_mode)
        else:
            input("\nPress Enter to return to main menu...")

    @staticmethod
    def _connect_via_user_input(automation_mode=False):
        while True:
            MenuLibrary.clear_screen()
            url = input("Enter Jellyfin server URL: ").strip()
            api_key = input("Enter API key: ").strip()
            print()

            # Get library_path in interactive mode
            library_path = ""
            if not automation_mode:
                while True:
                    MenuLibrary.clear_screen()
                    library_path = input("Enter library folder path (local or network share): ").strip()
                    if os.path.isdir(library_path):
                        break
                    print("\nWARNING: The provided path does not exist or is not accessible!")
                    print("\nDo you want to try again? [y/n]")
                    choice = input("→ ").strip().lower()
                    if choice in ("y", "j"):
                        continue
                    elif choice == "n":
                        return

            # Pass library_path to Jellyfin constructor
            jellyfin = Jellyfin(
                url=url,
                api_key=api_key,
                library_path=library_path
            )

            if jellyfin.test_connection():
                if automation_mode:
                    # For automation mode, we don't have library_path yet
                    MenuLibrary.show_library_menu(jellyfin, automation_mode)
                    return
                else:
                    MenuLibrary.show_library_menu(jellyfin, automation_mode)
                    return
            else:
                print("\nDo you want to try again? [y/n]")
                choice = input("→ ").strip().lower()
                if choice in ("y", "j"):
                    continue
                elif choice == "n":
                    return

    @staticmethod
    def show_library_menu(jellyfin, automation_mode=False):
        """
        Displays the library selection menu and handles user interaction.

        Args:
            jellyfin: Authenticated Jellyfin API client instance
        """
        try:
            # Fetch all libraries from Jellyfin server
            raw_libraries = jellyfin.get_libraries()
            return_to_main = False # Only set on True if after the auto command generation, this will send the user back to main instead library menu

            while True:
                MenuLibrary.clear_screen()
                max_index = 1 + len([lib for lib in raw_libraries if lib.get("CollectionType", "").lower() in ("tvshows", "movies")]) - 1
                index_width = len(str(max_index)) if max_index > 0 else 1

                print("=== Select Library for Command Generator ===" if automation_mode else "=== Select Library ===")
                print(f"{'0'.rjust(index_width)}. Return to main menu")

                # Handle case when no libraries are found
                if not raw_libraries:
                    print("\nNo libraries found or couldn't connect to server")
                    print("Possible reasons:")
                    print("- No libraries exist on the server")
                    print("- API key doesn't have proper permissions")
                    print("- Server URL is incorrect")
                    input("\nPress Enter to continue...")
                    return

                # Initialize lists for different library types
                series_libraries      = []  # TV Show libraries
                movie_libraries       = []  # Movie libraries
                unsupported_libraries = []  # Libraries of unsupported types

                # Categorize each library by its type
                for lib in raw_libraries:
                    collection_type = lib.get("CollectionType", "").lower()

                    if collection_type not in ("tvshows", "movies"):
                        unsupported_libraries.append(lib)
                    elif collection_type == "tvshows":
                        series_libraries.append(lib)
                    elif collection_type == "movies":
                        movie_libraries.append(lib)
                    else:
                        continue  # Skip any unhandled types

                current_index = 1  # Starting menu index
                selection_map = {}  # Maps menu numbers to library objects

                # Maximum index for width calculation
                max_index = current_index + len(series_libraries) + len(movie_libraries) - 1
                index_width = len(str(max_index))  # for example: 100 = 3

                # Display TV Show libraries section if any exist
                if series_libraries:
                    print("\n=== Series Libraries ===")
                    for lib in series_libraries:
                        print(f"{str(current_index).rjust(index_width)}. {lib['Name']}")
                        selection_map[current_index] = lib
                        current_index += 1

                # Display Movie libraries section if any exist
                if movie_libraries:
                    print("\n=== Movie Libraries ===")
                    for lib in movie_libraries:
                        print(f"{str(current_index).rjust(index_width)}. {lib['Name']}")
                        selection_map[current_index] = lib
                        current_index += 1

                # Display informational section about unsupported libraries
                if unsupported_libraries:
                    print("\n=== Unsupported Libraries ===")
                    print(" | ".join([lib["Name"] for lib in unsupported_libraries]))

                choice = input("\nSelect library: ").strip()

                # Return to main menu
                if choice == "0":
                    return

                try:
                    choice_num = int(choice)
                    if choice_num in selection_map:
                        selected_lib = selection_map[choice_num]
                        # Show images for selected library or go to automation
                        if not automation_mode:
                            MenuLibrary.show_library_images(jellyfin, selected_lib)
                        else:
                            return_to_main = AutoGenerator.prepare_export_automation(jellyfin, selected_lib)
                except ValueError:
                    pass

                if return_to_main:
                    return

        except Exception as e:
            print(f"Unexpected ERROR: {str(e)}")
            input("\nPress Enter to continue...")
            return

    @staticmethod
    def show_library_images(jellyfin, library_obj):
        """Display export preview and handle export confirmation"""

        # Fetch and display library content
        MenuLibrary.clear_screen()
        print("=== Fetching image files... ===")
        print("\nThis might take a while depending on the size of the library...")
        structured_data = ExportPrepare.prepare_and_show_export(jellyfin, library_obj)
        MenuLibrary.clear_screen()

        if not structured_data:
            library_name = library_obj["Name"]
            print(f"=== {library_name} ===")
            print("Library items could not be fetched. The library may be empty or unavailable.")
            input("Press Enter to return to library selection...")
            MenuLibrary.show_library_menu(jellyfin)
            return

        # Show export preview
        ExportPrepare.show_export_preview(structured_data)

        # Print separator with extra newline
        print("\n" + "="*50 + "\n")

        input("Press Enter to open export menu...")
        ExportPrompts.prompt_export_settings(jellyfin, structured_data)