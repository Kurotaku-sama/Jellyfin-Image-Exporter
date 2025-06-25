import sys
sys.dont_write_bytecode = True
import os
import json
import argparse
from .jellyfin_api import Jellyfin
from .export_prepare import ExportPrepare
from .exporter import Exporter
from config import CONNECTION_FILE

class AutomationRunner:
    @staticmethod
    def run_from_args():
        """
        Runs automation mode using command-line arguments.
        This is the main entry point for script execution via command line.
        """
        # Set up argument parser with all required parameters
        parser = argparse.ArgumentParser(description="Jellyfin Image Exporter Automation")
        parser.add_argument("--library_id", required=True, help="ID of the library to export")
        parser.add_argument("--export_method", choices=["single", "separate"], required=True,
                          help="Export method: 'single' for one output location, 'separate' for multiple")
        parser.add_argument("--episode_thumbnails", type=lambda x: x.lower() in ["true", "1", "yes"],
                          default=False, help="Whether to export episode thumbnails for TV shows")
        parser.add_argument("--target_paths", required=True,
                          help="List of target paths separated by | character")
        parser.add_argument("--connection_method", choices=["file", "parameters"], default="file",
                          help="Connection method: 'file' for connection.json or 'parameters' for direct input")
        parser.add_argument("--url", help="Jellyfin server URL (required if connection_method=parameters)")
        parser.add_argument("--api_key", help="Jellyfin API key (required if connection_method=parameters)")
        parser.add_argument("--library_path", help="Path to Jellyfin metadata folder (required if connection_method=parameters)")

        # Parse command line arguments
        args = parser.parse_args()

        # Process target paths - split by |, normalize, and remove empty paths
        target_paths = [Exporter.normalize_path(p.strip())
                       for p in args.target_paths.split("|") if p.strip()]

        # Initialize connection variables
        url = None
        api_key = None
        library_path = None

        if args.connection_method == "file":
            # Verify connection configuration file exists
            normalized_config_path = Exporter.normalize_path(CONNECTION_FILE)
            if not os.path.exists(normalized_config_path):
                print(f"ERROR: Connection file {normalized_config_path} not found")
                sys.exit(1)

            # Load Jellyfin server connection details
            with open(normalized_config_path, "r") as f:
                connection_data = json.load(f)
                url = connection_data.get("url")
                api_key = connection_data.get("api_key")
                library_path = Exporter.normalize_path(connection_data.get("library_path"))
        elif args.connection_method == "parameters":
            if not all([args.url, args.api_key, args.library_path]):
                print("ERROR: --url, --api_key and --library_path are required when using connection_method=parameters")
                sys.exit(1)
            url = args.url
            api_key = args.api_key
            library_path = Exporter.normalize_path(args.library_path)

        # Verify the library path exists
        if not os.path.isdir(library_path):
            print(f"ERROR: Library metadata path doesn't exist: {library_path}")
            print("Attempting to find the correct path...")

            # Try common alternative paths
            common_paths = [
                library_path,
                library_path.replace('\\', '/'),
                library_path.replace('/', '\\'),
                os.path.expanduser(library_path),
                os.path.abspath(library_path)
            ]

            found = False
            for test_path in common_paths:
                if os.path.isdir(test_path):
                    library_path = Exporter.normalize_path(test_path)
                    print(f"Found alternative path: {library_path}")
                    found = True
                    break

            if not found:
                print("Could not locate the metadata directory. Please verify the path.")
                sys.exit(1)

        # Initialize Jellyfin API client and test connection
        jellyfin = Jellyfin(url, api_key)
        if not jellyfin.test_connection():
            print(f"URL: {url}")
            print(f"API Key: {api_key}")
            sys.exit(1)

        # Get all libraries and find the one matching the provided ID
        libraries = jellyfin.get_libraries()
        selected_library = next((lib for lib in libraries if lib.get("ItemId") == args.library_id), None)

        if not selected_library:
            print(f"Library with ID {args.library_id} not found")
            sys.exit(1)

        # Prepare export data - this organizes the media items for export
        structured_data = ExportPrepare.prepare_and_show_export(jellyfin, selected_library)
        if not structured_data:
            print("Failed to prepare export data")
            sys.exit(1)

        # Validate the number of target paths matches the export method requirements
        library_roots = structured_data["library_root"]
        if not isinstance(library_roots, list):  # Ensure we always work with a list
            library_roots = [library_roots]

        if args.export_method == "single" and len(target_paths) != 1:
            print("Single export method requires exactly one target path")
            sys.exit(1)

        if args.export_method == "separate" and len(target_paths) != len(library_roots):
            print(f"Separate export requires {len(library_roots)} target paths, got {len(target_paths)}")
            sys.exit(1)

        # Prepare export options dictionary with normalized paths
        export_options = {
            "export_method": args.export_method,
            "export_episode_thumbs": args.episode_thumbnails,
            "confirmed": True,
            "automation_mode": True,
            "connection_method": args.connection_method,
            "jellyfin_url": url,
            "api_key": api_key,
            "library_path": library_path,
            "target_paths": target_paths
        }

        # Print connection information
        print("\n=== Connection Information ===")
        print(f"Connection Method: {args.connection_method}")
        print(f"Jellyfin URL: {url}")
        print(f"API Token: {api_key}")
        print(f"Metadata Path: {library_path}\n")

        # Start the appropriate export based on media type
        if structured_data["type"] in ("series", "tvshows"):
            Exporter.export_series_images(jellyfin, structured_data, export_options)
        elif structured_data["type"] == "movies":
            Exporter.export_movie_images(jellyfin, structured_data, export_options)