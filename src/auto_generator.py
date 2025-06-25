import sys
sys.dont_write_bytecode = True
import os
from .export_prompts import ExportPrompts

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
        library_type = selected_library.get("CollectionType", "").lower()
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
            f"--library_id {library_id}",
            f"--export_method {export_method}",
            f"--episode_thumbnails {export_episode_thumbs}",
            f"--target_paths \"{joined_paths}\"",
            f"--connection_method {connection_method}"
        ]

        # Add connection-specific parameters
        if connection_method == "parameters":
            final_command.extend([
                f"--url \"{export_options.get('jellyfin_url', '')}\"",
                f"--api_key \"{export_options.get('api_key', '')}\"",
                f"--library_path \"{export_options.get('library_path', '')}\""
            ])

        # Join all parts into a single command string
        final_command_str = " ".join(final_command)

        # Output result
        AutoGenerator.clear_screen()
        print("=== Automation Command ===")
        print("\nCopy this command for automated execution:\n")
        print(final_command_str)

        print("\nNote: You need to add py/python/python3 in front of the command depending on how you call python scripty via CLI")
        if connection_method == "file":
            print("Ensure connection.json exists and is valid")
        input("\nPress Enter to return to main menu...")
        return True