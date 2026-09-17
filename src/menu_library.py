import sys
sys.dont_write_bytecode = True
import os
from .jellyfin_api import Jellyfin
from .export_prompts import ExportPrompts
from .export_prepare import ExportPrepare
from .auto_generator import AutoGenerator
from .settings import Settings
from .colors import Colors

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
            print(Colors.wrap(f"Unknown connection mode: {mode}", Colors.RED))
            input("Press Enter to continue...")

    @staticmethod
    def _can_connect_with_file():
        """Check if we can connect using the values stored in config.cfg"""
        try:
            settings = Settings.load()

            # Minimal validation
            if not all(settings.get(key) for key in ["url", "api_key", "library_path"]):
                return False

            # Test connection
            jellyfin = Jellyfin(settings["url"], settings["api_key"])
            return jellyfin.test_connection()
        except Exception:
            return False

    @staticmethod
    def _connect_via_connection_file(automation_mode=False):
        settings = Settings.load()

        if not all(settings.get(key) for key in ["url", "api_key", "library_path"]):
            print(Colors.wrap("Connection settings are incomplete. Please configure them via menu option 3.", Colors.YELLOW))
            input("Press Enter to return to main menu...")
            return

        library_path = settings.get("library_path", "")
        if not os.path.isdir(library_path):
            print(Colors.wrap("WARNING: The library path is not accessible from this machine!", Colors.YELLOW))
            input("Press Enter to continue...")

        # Pass library_path to Jellyfin constructor
        jellyfin = Jellyfin(
            url=settings.get("url"),
            api_key=settings.get("api_key"),
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
                    print(Colors.wrap("\nWARNING: The provided path does not exist or is not accessible!", Colors.YELLOW))
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
                # In automation mode, library_path is not collected here and
                # stays empty; show_library_menu handles both modes the same way.
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

            # Library content types this tool can prepare and export images for
            supported_collection_types = ("tvshows", "movies", "musicvideos", "homevideos", "music")

            while True:
                MenuLibrary.clear_screen()
                max_index = 1 + len([lib for lib in raw_libraries if (lib.get("CollectionType") or "").lower() in supported_collection_types or not lib.get("CollectionType")]) - 1
                index_width = len(str(max_index)) if max_index > 0 else 1

                print(Colors.wrap("=== Select Library for Command Generator ===" if automation_mode else "=== Select Library ===", Colors.CYAN, Colors.BOLD))
                print(f"{'0'.rjust(index_width)}. Return to main menu")

                # Handle case when no libraries are found
                if not raw_libraries:
                    print(Colors.wrap("\nNo libraries found or couldn't connect to server", Colors.YELLOW))
                    print("Possible reasons:")
                    print("- No libraries exist on the server")
                    print("- API key doesn't have proper permissions")
                    print("- Server URL is incorrect")
                    input("\nPress Enter to continue...")
                    return

                # Initialize lists for different library types
                series_libraries      = []  # TV Show libraries
                movie_libraries       = []  # Movie libraries
                musicvideo_libraries  = []  # Music Video libraries
                homevideo_libraries   = []  # Home Videos & Photos libraries
                music_libraries       = []  # Music libraries
                mixed_libraries       = []  # Libraries with no fixed content type
                unsupported_libraries = []  # Libraries of unsupported types

                # Maps a library's CollectionType to the bucket it belongs in
                type_buckets = {
                    "tvshows": series_libraries,
                    "movies": movie_libraries,
                    "musicvideos": musicvideo_libraries,
                    "homevideos": homevideo_libraries,
                    "music": music_libraries,
                }

                # Categorize each library by its type
                for lib in raw_libraries:
                    # CollectionType can be explicitly null in the Jellyfin
                    # API response for libraries without a fixed content
                    # type, so fall back to an empty string before
                    # lowercasing it and route those into Mixed Libraries.
                    collection_type = (lib.get("CollectionType") or "").lower()
                    if collection_type == "":
                        mixed_libraries.append(lib)
                        continue
                    bucket = type_buckets.get(collection_type)
                    if bucket is not None:
                        bucket.append(lib)
                    else:
                        unsupported_libraries.append(lib)

                current_index = 1  # Starting menu index
                selection_map = {}  # Maps menu numbers to library objects

                # Maximum index for width calculation
                total_supported = (
                    len(series_libraries) + len(movie_libraries) +
                    len(musicvideo_libraries) + len(homevideo_libraries) +
                    len(music_libraries) + len(mixed_libraries)
                )
                max_index = current_index + total_supported - 1
                index_width = len(str(max_index)) if max_index >= current_index else 1  # for example: 100 = 3

                # Display each supported library type in its own section, if any exist
                sections = (
                    ("Series Libraries", series_libraries),
                    ("Movie Libraries", movie_libraries),
                    ("Music Video Libraries", musicvideo_libraries),
                    ("Home Video Libraries", homevideo_libraries),
                    ("Music Libraries", music_libraries),
                    ("Mixed Libraries", mixed_libraries),
                )
                for section_title, libraries in sections:
                    if libraries:
                        print(Colors.wrap(f"\n=== {section_title} ===", Colors.BLUE, Colors.BOLD))
                        for lib in libraries:
                            print(f"{str(current_index).rjust(index_width)}. {lib['Name']}")
                            selection_map[current_index] = lib
                            current_index += 1

                # Display informational section about unsupported libraries
                if unsupported_libraries:
                    print(Colors.wrap("\n=== Unsupported Libraries ===", Colors.YELLOW, Colors.BOLD))
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
            print(Colors.wrap(f"Unexpected ERROR: {str(e)}", Colors.RED))
            input("\nPress Enter to continue...")
            return

    @staticmethod
    def show_library_images(jellyfin, library_obj):
        """Display export preview and handle export confirmation"""

        # Fetch and display library content
        MenuLibrary.clear_screen()
        print(Colors.wrap("=== Fetching image files... ===", Colors.CYAN, Colors.BOLD))
        print("\nThis might take a while depending on the size of the library...")
        structured_data = ExportPrepare.prepare_and_show_export(jellyfin, library_obj)
        MenuLibrary.clear_screen()

        if not structured_data:
            library_name = library_obj["Name"]
            print(Colors.wrap(f"=== {library_name} ===", Colors.CYAN, Colors.BOLD))
            print(Colors.wrap("Library items could not be fetched. The library may be empty or unavailable.", Colors.YELLOW))
            input("Press Enter to return to library selection...")
            MenuLibrary.show_library_menu(jellyfin)
            return

        # Show export preview
        ExportPrepare.show_export_preview(structured_data)

        # Print separator with extra newline
        print(Colors.wrap("\n" + "="*50 + "\n", Colors.CYAN, Colors.BOLD))

        input("Press Enter to open export menu...")
        ExportPrompts.prompt_export_settings(jellyfin, structured_data)