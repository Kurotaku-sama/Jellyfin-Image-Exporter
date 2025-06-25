import sys
sys.dont_write_bytecode = True
import os
import json
from .exporter import Exporter

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
        print(header)

        # Show export confirmation status (only in interactive mode)
        if "export" in export_options and not export_options.get("automation_mode"):
            print(f"Export: {'Yes' if export_options.get('export') else 'No'}")

        # Show episode thumbnails option (for series only)
        if "export_episode_thumbs" in export_options:
            print(f"Include Episode Thumbnails: {'Yes' if export_options['export_episode_thumbs'] else 'No'}")

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
                print(f"\nConnection Method: {'File (connection.json)' if export_options['connection_method'] == 'file' else 'Manual Parameters'}")
                print("Jellyfin API:")
                print(f"  URL: {export_options.get('jellyfin_url', 'Not set')}")
                print(f"  API Token: {export_options.get('api_key', 'Not set')}")
                if export_options.get('library_path'):
                    print(f"\nMetadata Path: \"{export_options['library_path']}\"")

        # Footer separator
        print("=" * len(header) + "\n")

        # Display error message if provided
        if error_message:
            print(f"ERROR: {error_message}")

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
        if structured_data["type"] in ("series", "tvshows"):
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

        # Get library_path from jellyfin connection and add to export_options
        export_options['library_path'] = jellyfin.library_path

        if automation_mode:
            # Automation Mode - Choose between file or manual parameters
            while True:
                ExportPrompts._show_export_configuration(export_options, structured_data)

                print("Connection Type:")
                print("1. Use connection.json file (recommended)")
                print("2. Use manual parameters")
                choice = input("→ ").strip()

                if choice == "1":
                    # File-based mode
                    export_options['connection_method'] = 'file'
                    export_options['jellyfin_url'] = jellyfin.url
                    export_options['api_key'] = jellyfin.api_key
                    print("NOTE: Using current connection parameters from connection.json")
                    break

                elif choice == "2":
                    # Manual parameters mode
                    export_options['connection_method'] = 'parameters'
                    export_options['jellyfin_url'] = jellyfin.url
                    export_options['api_key'] = jellyfin.api_key
                    print("\nWARNING: Using current session parameters without verification")
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
                elif structured_data["type"] == "movies":
                    Exporter.export_movie_images(jellyfin, structured_data, export_options)
                return
            elif choice == "n":
                return