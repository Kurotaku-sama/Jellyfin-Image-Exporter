import sys
sys.dont_write_bytecode = True
import os
import json
from .exporter import Exporter
from .colors import Colors

class ExportPrompts:
    @staticmethod
    def _show_export_configuration(export_options, structured_data=None, error_message=None):
        """Displays the export configuration panel with current settings"""
        os.system("cls" if os.name == "nt" else "clear")

        # Display header with library name
        library_name = structured_data.get("library_name", "Unknown") if structured_data else "Unnamed Library"
        library_roots = structured_data.get("library_root", []) if structured_data else []

        if not isinstance(library_roots, list):
            library_roots = [library_roots]

        header = f"=== Export Configuration: {library_name} ==="
        print(Colors.wrap(header, Colors.CYAN, Colors.BOLD))

        # Show export confirmation status (only in interactive mode)
        if "export" in export_options and not export_options.get("automation_mode"):
            print(f"Export: {'Yes' if export_options.get('export') else 'No'}")

        # Show episode thumbnails option (for series only)
        if "export_episode_thumbs" in export_options:
            print(f"Include Episode Thumbnails: {'Yes' if export_options['export_episode_thumbs'] else 'No'}")

        # Show music cover filename option (for music only)
        if "music_folder_name" in export_options:
            print(f"Music Cover Filename: {export_options['music_folder_name']}")

        # Show the wipe setting prominently, since it is a destructive operation
        if export_options.get("wipe_existing_exports"):
            print(Colors.wrap("WIPE EXISTING EXPORTS: YES - target folders will be emptied first!", Colors.RED, Colors.BOLD))

        # Show selected export method
        if "export_method" in export_options:
            print(f"Export Structure: {'Single Path' if export_options['export_method'] == 'single' else 'Separate Paths'}")

        # Display target paths
        target_paths = export_options.get("target_paths")
        if target_paths:
            if export_options.get("export_method", "single") == "single":
                print(f"Export Path: {target_paths[0]}")
            else:
                print("Per-Root Export Paths:")
                for i, path in enumerate(target_paths):
                    root_name = library_roots[i] if i < len(library_roots) else f"Root {i+1}"
                    print(f"  {root_name}: {path}")

        # Show connection details in automation mode
        if export_options.get("automation_mode"):
            if "connection_method" in export_options:
                print(f"\nConnection Method: {'File (config.cfg)' if export_options['connection_method'] == 'file' else 'Manual Parameters'}")
                print("Jellyfin API:")
                print(f"  URL: {export_options.get('jellyfin_url', 'Not set')}")
                print(f"  API Token: {export_options.get('api_key', 'Not set')}")
                if export_options.get('library_path'):
                    print(f"\nMetadata Path: \"{export_options['library_path']}\"")

        # Footer separator
        print(Colors.wrap("=" * len(header), Colors.CYAN, Colors.BOLD) + "\n")

        # Display error message if provided
        if error_message:
            print(Colors.wrap(f"ERROR: {error_message}", Colors.RED))

    @staticmethod
    def _check_and_prompt_wipe(path, automation_mode):
        """
        Warns and asks whether to wipe an export path's existing content.

        Automation mode skips this entirely, since paths are not validated
        or checked locally while a command is only being generated. An
        empty or non-existent path is skipped too, since there is nothing
        to wipe. Wiping happens immediately so that a stale export (e.g.
        from a series that no longer exists in the library) is gone before
        the new export starts.

        Args:
            path (str): The export path just entered by the user
            automation_mode (bool): Whether settings are being gathered for
                an automation command instead of a real export
        """
        if automation_mode or not os.path.isdir(path) or not Exporter._directory_has_content(path):
            return

        print(Colors.wrap(f"\nWARNING: The folder \"{path}\" is not empty!", Colors.RED, Colors.BOLD))
        print(Colors.wrap("Wiping it deletes EVERYTHING inside it before the export starts.", Colors.RED, Colors.BOLD))
        print("This is useful to remove leftover exports for items that no")
        print("longer exist in your library, but cannot be undone.")
        print("Wipe all existing content in this folder? [y/n]")
        choice = input("→ ").strip().lower()
        if choice in ("y", "j"):
            if Exporter._wipe_directory_contents(path):
                print(Colors.wrap("Folder wiped.", Colors.GREEN))
            else:
                print(Colors.wrap("Some files could not be deleted, see errors above.", Colors.RED))
            input("Press Enter to continue...")

    @staticmethod
    def prompt_export_settings(jellyfin, structured_data, automation_mode=False):
        """Handles the interactive export configuration process"""
        export_options = {
            "automation_mode": automation_mode,
            "target_paths": []
        }

        # Normalize library roots to always be a list
        library_roots = structured_data["library_root"] if isinstance(structured_data["library_root"], list) else [structured_data["library_root"]]

        # --- Initial Export Confirmation ---
        if not automation_mode:
            while True:
                ExportPrompts._show_export_configuration(export_options, structured_data)
                print("Do you want to export these files? [y/n]")
                choice = input("→ ").strip().lower()
                if choice in ("y", "j"):
                    export_options["export"] = True
                    break
                elif choice == "n":
                    return

        # --- Episode Thumbnails Option (Series Only) ---
        # A mixed library's series items aren't known yet while generating
        # an automation command, so the prompt is shown unconditionally in
        # that case instead of depending on an actual series_collection.
        if structured_data["type"] in ("series", "tvshows") or (
            structured_data["type"] == "mixed" and (automation_mode or structured_data.get("series_collection"))
        ):
            while True:
                ExportPrompts._show_export_configuration(export_options, structured_data)
                print("Include episode thumbnails? [y/n]")
                choice = input("→ ").strip().lower()
                if choice in ("y", "j"):
                    export_options["export_episode_thumbs"] = True
                    break
                elif choice == "n":
                    export_options["export_episode_thumbs"] = False
                    break

        # --- Music Cover Filename Option (Music Only) ---
        if structured_data["type"] == "music":
            while True:
                ExportPrompts._show_export_configuration(export_options, structured_data)
                print("Choose the filename for each album's primary cover image:")
                print("1. folder (Jellyfin's own default when \"Save artwork into media folders\" is enabled)")
                print("2. cover (used by other tools like beets and Navidrome)")
                choice = input("→ ").strip()
                if choice == "1":
                    export_options["music_folder_name"] = "folder"
                    break
                elif choice == "2":
                    export_options["music_folder_name"] = "cover"
                    break
                else:
                    ExportPrompts._show_export_configuration(export_options, structured_data, "Invalid choice. Enter 1 or 2.")

        # --- Path Selection Method ---
        if len(library_roots) > 1:
            while True:
                ExportPrompts._show_export_configuration(export_options, structured_data)
                print(f"This library consists of {len(library_roots)} separate roots.")
                print("You need to choose whether to save all images in the same path")
                print("or specify separate paths for each root.\n")
                print("Export method:")
                print("1. Single target path (all roots use same export location)")
                print("2. Separate paths (specify different location for each root)")
                choice = input("→ ").strip()

                if choice == "1":
                    export_options["export_method"] = "single"
                    ExportPrompts._show_export_configuration(export_options, structured_data)
                    while True:
                        path = input("Enter export path for all: ").strip()
                        if automation_mode or os.path.isdir(path):
                            export_options["target_paths"].append(path)
                            break
                        ExportPrompts._show_export_configuration(export_options, structured_data, f"Invalid path: {path}")
                    ExportPrompts._check_and_prompt_wipe(path, automation_mode)
                    break

                elif choice == "2":
                    export_options["export_method"] = "separate"
                    for i in range(len(library_roots)):
                        ExportPrompts._show_export_configuration(export_options, structured_data)
                        while True:
                            current_root = library_roots[i]
                            path = input(f"Enter path for root {i+1} ({current_root}): ").strip()
                            if automation_mode:
                                pass  # Skip validation in automation mode
                            elif not os.path.isdir(path):
                                ExportPrompts._show_export_configuration(export_options, structured_data, f"Invalid path: {path}")
                                continue
                            if path in export_options["target_paths"]:
                                ExportPrompts._show_export_configuration(export_options, structured_data, "Path already used for another root")
                                continue
                            if len(export_options["target_paths"]) <= i:
                                export_options["target_paths"].append(path)
                            else:
                                export_options["target_paths"][i] = path
                            break
                        ExportPrompts._check_and_prompt_wipe(path, automation_mode)
                    break
                else:
                    ExportPrompts._show_export_configuration(export_options, structured_data, "Invalid choice. Enter 1 or 2.")
        else:
            # Single root - automatically use single path method
            export_options["export_method"] = "single"
            ExportPrompts._show_export_configuration(export_options, structured_data)
            while True:
                path = input("Enter export path: ").strip()
                if automation_mode or os.path.isdir(path):
                    export_options["target_paths"] = [path]
                    break
                ExportPrompts._show_export_configuration(export_options, structured_data, f"Invalid path: {path}")
            ExportPrompts._check_and_prompt_wipe(path, automation_mode)

        # Get library_path from jellyfin connection and add to export_options
        export_options['library_path'] = jellyfin.library_path

        if automation_mode:
            # Ask whether the generated command should wipe each target
            # path's existing content before exporting. Paths are not
            # checked locally at generation time, so this is a single
            # yes/no toggle instead of the per-path prompt used for a real
            # interactive export.
            while True:
                ExportPrompts._show_export_configuration(export_options, structured_data)
                print("Should the generated command wipe all existing files in each")
                print("target path before exporting? Useful to remove leftover exports")
                print("for items that no longer exist in the library.")
                print("Include --wipe-existing-exports in the command? [y/n]")
                choice = input("→ ").strip().lower()
                if choice in ("y", "j"):
                    export_options["wipe_existing_exports"] = True
                    break
                elif choice == "n":
                    export_options["wipe_existing_exports"] = False
                    break

            # Automation Mode - Choose between file or manual parameters
            while True:
                ExportPrompts._show_export_configuration(export_options, structured_data)

                print("Connection Type:")
                print("1. Use config.cfg (recommended)")
                print("2. Use manual parameters")
                choice = input("→ ").strip()

                if choice == "1":
                    # File-based mode
                    export_options['connection_method'] = 'file'
                    export_options['jellyfin_url'] = jellyfin.url
                    export_options['api_key'] = jellyfin.api_key
                    print(Colors.wrap("NOTE: Using current connection parameters from config.cfg", Colors.CYAN))
                    break

                elif choice == "2":
                    # Manual parameters mode
                    export_options['connection_method'] = 'parameters'
                    export_options['jellyfin_url'] = jellyfin.url
                    export_options['api_key'] = jellyfin.api_key
                    print(Colors.wrap("\nWARNING: Using current session parameters without verification", Colors.YELLOW))
                    # library_path is only collected outside automation mode, so warn here if it is still empty before
                    # it ends up in the generated command.
                    if not export_options.get('library_path'):
                        print(Colors.wrap("WARNING: No library path was set for this session.", Colors.YELLOW))
                        print("The generated command will contain an empty --library-path")
                        print("and must be edited manually before it can be used.")
                    break

                else:
                    ExportPrompts._show_export_configuration(export_options, structured_data, "Invalid choice. Enter 1 or 2.")

            # Final verification prompt
            ExportPrompts._show_export_configuration(export_options, structured_data)
            print("PLEASE VERIFY ALL SETTINGS BEFORE CONTINUING:")
            print("- Ensure paths are accessible from target machine")
            print("- Verify API credentials are correct")
            print("- Check metadata path exists on target system")
            input("\nPress Enter to generate automation command...")

            return export_options

        # --- Final Confirmation (interactive mode only) ---
        while True:
            ExportPrompts._show_export_configuration(export_options, structured_data)
            print("Are you sure you want to export the images with these settings? [y/n]")
            choice = input("→ ").strip().lower()
            if choice in ("y", "j"):
                ExportPrompts._show_export_configuration(export_options, structured_data)
                if structured_data["type"] == "series":
                    Exporter.export_series_images(jellyfin, structured_data, export_options)
                elif structured_data["type"] in ("movies", "musicvideos", "homevideos"):
                    Exporter.export_movie_images(jellyfin, structured_data, export_options)
                elif structured_data["type"] == "music":
                    Exporter.export_music_images(jellyfin, structured_data, export_options)
                elif structured_data["type"] == "mixed":
                    Exporter.export_mixed_images(jellyfin, structured_data, export_options)
                return
            elif choice == "n":
                return