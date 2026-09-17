import sys
sys.dont_write_bytecode = True
import os
from .export_prompts import ExportPrompts
from .colors import Colors

class AutoGenerator:
    @staticmethod
    def clear_screen():
        """Clears the terminal screen"""
        os.system("cls" if os.name == "nt" else "clear")

    @staticmethod
    def prepare_export_automation(jellyfin, selected_library):
        """
        Starts an interactive automation setup and prints the final command.

        Args:
            jellyfin: Jellyfin API client instance
            selected_library (dict): Jellyfin library metadata
        """

        # Extract required fields from selected_library
        library_name = selected_library.get("Name", "Unknown")
        library_roots = selected_library.get("Locations", [])
        library_type = (selected_library.get("CollectionType") or "").lower()
        if not library_type:
            library_type = "mixed"
        library_id = selected_library.get("ItemId")

        structured_data = {
            "library_name": library_name,
            "library_root": library_roots,
            "type": library_type
        }

        # Prompt user for options in automation mode
        export_options = ExportPrompts.prompt_export_settings(jellyfin, structured_data, automation_mode=True)

        target_paths = export_options.get("target_paths", [])
        connection_method = export_options.get("connection_method", "file")

        # Prepare argument strings
        export_method = export_options.get("export_method", "single")
        export_episode_thumbs = str(export_options.get("export_episode_thumbs", False)).lower()
        joined_paths = "|".join(target_paths)

        # Build the base command
        final_command = [
            "main.py",
            f"--library-id \"{library_id}\"",
            f"--export-method {export_method}",
            f"--episode-thumbnails {export_episode_thumbs}",
            f"--target-paths \"{joined_paths}\"",
            f"--connection-method {connection_method}"
        ]

        # Add the music cover filename choice for music libraries
        if library_type == "music":
            music_folder_name = export_options.get("music_folder_name", "folder")
            music_folder_name_arg = "1" if music_folder_name == "folder" else "2"
            final_command.append(f"--music-folder-name {music_folder_name_arg}")

        # Add the wipe flag if the generated command should clear each
        # target path's existing content before exporting
        if export_options.get("wipe_existing_exports"):
            final_command.append("--wipe-existing-exports")

        # Add connection-specific parameters
        if connection_method == "parameters":
            final_command.extend([
                f"--url \"{export_options.get('jellyfin_url', '')}\"",
                f"--api-key \"{export_options.get('api_key', '')}\"",
                f"--library-path \"{export_options.get('library_path', '')}\""
            ])

        # Join all parts into a single command string
        final_command_str = " ".join(final_command)

        # Output result
        AutoGenerator.clear_screen()
        print(Colors.wrap("=== Automation Command ===", Colors.CYAN, Colors.BOLD))
        print("\nCopy this command for automated execution:\n")
        print(Colors.wrap(final_command_str, Colors.GREEN))

        print("\nNote: You need to add py/python/python3 in front of the command depending on how you call python scripty via CLI")
        if connection_method == "file":
            print("Ensure config.cfg has a valid url, api_key and library_path")
        if export_options.get("wipe_existing_exports"):
            print(Colors.wrap("WARNING: This command wipes all existing files in the target path(s) before exporting!", Colors.RED, Colors.BOLD))
        input("\nPress Enter to return to main menu...")
        return True