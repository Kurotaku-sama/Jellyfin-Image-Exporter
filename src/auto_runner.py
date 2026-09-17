import sys
sys.dont_write_bytecode = True
import os
import argparse
from .jellyfin_api import Jellyfin
from .export_prepare import ExportPrepare
from .exporter import Exporter
from .colors import Colors
from .settings import Settings, CONFIG_FILE

class AutomationRunner:
    @staticmethod
    def run_from_args():
        """
        Runs automation mode using command-line arguments.
        This is the main entry point for script execution via command line.
        """
        # Automation mode output is typically consumed by external tooling
        # (e.g. an Unraid User Scripts log), which doesn't render ANSI
        # escape codes, so colored output is always disabled here
        # regardless of the 'colored' setting in config.cfg.
        Colors.ENABLED = False

        # Set up argument parser with all required parameters
        parser = argparse.ArgumentParser(description="Jellyfin Image Exporter Automation")
        parser.add_argument("--library-id", required=True, help="ID of the library to export")
        parser.add_argument("--export-method", choices=["single", "separate"], required=True,
                          help="Export method: 'single' for one output location, 'separate' for multiple")
        parser.add_argument("--episode-thumbnails", type=lambda x: x.lower() in ["true", "1", "yes"],
                          default=False, help="Whether to export episode thumbnails for TV shows")
        parser.add_argument("--target-paths", required=True,
                          help="List of target paths separated by | character")
        parser.add_argument("--connection-method", choices=["file", "parameters"], default="file",
                          help="Connection method: 'file' for config.cfg or 'parameters' for direct input")
        parser.add_argument("--url", help="Jellyfin server URL (required if connection_method=parameters)")
        parser.add_argument("--api-key", help="Jellyfin API key (required if connection_method=parameters)")
        parser.add_argument("--library-path", help="Path to Jellyfin metadata folder (required if connection_method=parameters)")
        parser.add_argument("--music-folder-name", choices=["1", "2"], default="1",
                          help="Music album cover filename: '1' for folder, '2' for cover (only used for music libraries)")
        parser.add_argument("--wipe-existing-exports", action="store_true", default=False,
                          help="Wipe all existing files in each target path before exporting")

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
            # Load connection details stored in config.cfg
            settings = Settings.load()
            if not all(settings.get(key) for key in ["url", "api_key", "library_path"]):
                print(Colors.wrap(f"ERROR: {CONFIG_FILE} is missing url, api_key or library_path. Configure it via menu option 3 first.", Colors.RED))
                sys.exit(1)

            url = settings.get("url")
            api_key = settings.get("api_key")
            library_path = Exporter.normalize_path(settings.get("library_path"))
        elif args.connection_method == "parameters":
            if not all([args.url, args.api_key, args.library_path]):
                print(Colors.wrap("ERROR: --url, --api-key and --library-path are required when using connection-method=parameters", Colors.RED))
                sys.exit(1)
            url = args.url
            api_key = args.api_key
            library_path = Exporter.normalize_path(args.library_path)

        # Verify the library path exists
        if not os.path.isdir(library_path):
            print(Colors.wrap(f"ERROR: Library metadata path doesn't exist: {library_path}", Colors.RED))
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
                print(Colors.wrap("Could not locate the metadata directory. Please verify the path.", Colors.RED))
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
            print(Colors.wrap(f"Library with ID {args.library_id} not found", Colors.RED))
            sys.exit(1)

        # Prepare export data - this organizes the media items for export
        structured_data = ExportPrepare.prepare_and_show_export(jellyfin, selected_library)
        if not structured_data:
            print(Colors.wrap("Failed to prepare export data", Colors.RED))
            sys.exit(1)

        # Validate the number of target paths matches the export method requirements
        library_roots = structured_data["library_root"]
        if not isinstance(library_roots, list):  # Ensure we always work with a list
            library_roots = [library_roots]

        if args.export_method == "single" and len(target_paths) != 1:
            print(Colors.wrap("Single export method requires exactly one target path", Colors.RED))
            sys.exit(1)

        if args.export_method == "separate" and len(target_paths) != len(library_roots):
            print(Colors.wrap(f"Separate export requires {len(library_roots)} target paths, got {len(target_paths)}", Colors.RED))
            sys.exit(1)

        # Prepare export options dictionary with normalized paths
        export_options = {
            "export_method": args.export_method,
            "export_episode_thumbs": args.episode_thumbnails,
            "music_folder_name": "folder" if args.music_folder_name == "1" else "cover",
            "wipe_existing_exports": args.wipe_existing_exports,
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

        # Wipe each target path's existing content before exporting, since
        # automation mode has no interactive prompt to ask through
        if args.wipe_existing_exports:
            for path in target_paths:
                if os.path.isdir(path) and Exporter._directory_has_content(path):
                    print(Colors.wrap(f"Wiping existing content in: {path}", Colors.RED, Colors.BOLD))
                    if Exporter._wipe_directory_contents(path):
                        print(Colors.wrap("Folder wiped.", Colors.GREEN))
                    else:
                        print(Colors.wrap("Some files could not be deleted, see errors above.", Colors.RED))

        # Start the appropriate export based on media type
        if structured_data["type"] in ("series", "tvshows"):
            Exporter.export_series_images(jellyfin, structured_data, export_options)
        elif structured_data["type"] in ("movies", "musicvideos", "homevideos"):
            Exporter.export_movie_images(jellyfin, structured_data, export_options)
        elif structured_data["type"] == "music":
            Exporter.export_music_images(jellyfin, structured_data, export_options)
        elif structured_data["type"] == "mixed":
            Exporter.export_mixed_images(jellyfin, structured_data, export_options)