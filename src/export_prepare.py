import sys
sys.dont_write_bytecode = True
import os

class ExportPrepare:
    """Handles data preparation and user interaction for media library exports."""

    @staticmethod
    def prepare_and_show_export(jellyfin, library_obj):
        """
        Main method to prepare export data and show preview.

        Args:
            jellyfin: Jellyfin API client instance
            library_obj: Dictionary containing library information

        Returns:
            Structured data ready for export, or None if preparation failed
        """
        collection_type = library_obj.get("CollectionType", "").lower()

        # Route to appropriate preparation method based on library type
        if collection_type == "tvshows":
            return ExportPrepare._prepare_series_data(jellyfin, library_obj)
        elif collection_type == "movies":
            return ExportPrepare._prepare_movie_data(jellyfin, library_obj)

        print(f"\nERROR: Unsupported Library Type: {collection_type}")
        return None

    @staticmethod
    def _prepare_series_data(jellyfin, library_obj):
        """
        Prepares structured data for TV series export.

        Args:
            jellyfin: Jellyfin API client instance
            library_obj: Dictionary containing library information

        Returns:
            Dictionary containing:
            - type: 'series'
            - series_collection: List of series data
            - library_root: Root path of the library
            - library_name: Name of the library
        """
        library_id = library_obj["ItemId"]
        library_root = library_obj.get("Locations", [])
        library_name = library_obj["Name"]

        # Get all items from the library
        items = jellyfin.get_library_items(library_id)

        if not items:
            print("\nNo series found in this library")
            return None

        series_collection = []

        for item in items:
            if item.get("Type") != "Series":
                continue

            # Extract basic series information
            item_path = item.get("Path", "")
            folder_name = os.path.basename(item_path.rstrip("/"))
            images_data = jellyfin.get_item_images(item["Id"])

            # Process seasons data
            seasons_data = []
            seasons = jellyfin.get_seasons(item["Id"])
            for season in seasons:
                season_images = jellyfin.get_item_images(season["Id"])
                seasons_data.append({
                    "season_number": season.get("IndexNumber", "Unknown"),
                    "metadata_dir": season_images["metadata_dir"],
                    "files": season_images["files"]
                })

            # Build series entry
            series_collection.append({
                "id": item["Id"],
                "folder_name": folder_name,
                "metadata_dir": images_data["metadata_dir"],
                "series_files": images_data["files"],
                "seasons": seasons_data,
                "path": item_path
            })

        return {
            "type": "series",
            "series_collection": series_collection,
            "library_root": library_root,
            "library_name": library_name
        }

    @staticmethod
    def _prepare_movie_data(jellyfin, library_obj):
        """
        Prepares structured data for movie export.

        Args:
            jellyfin: Jellyfin API client instance
            library_obj: Dictionary containing library information

        Returns:
            Dictionary containing:
            - type: 'movies'
            - movie_collection: List of movie data
            - library_root: Root pathes of the library
            - library_name: Name of the library
        """
        library_id = library_obj["ItemId"]
        library_root = library_obj.get("Locations", [])
        library_name = library_obj["Name"]

        items = jellyfin.get_library_items(library_id)
        if not items:
            print("\nNo movies found in this library")
            return None

        movie_collection = []

        for item in items:
            if item.get("Type") != "Movie":
                continue

            item_path = item.get("Path", "")
            images_data = jellyfin.get_item_images(item["Id"])

            movie_collection.append({
                "id": item["Id"],
                "path": item_path,
                "filename": os.path.basename(item_path),
                "folder_path": os.path.dirname(item_path),
                "metadata_dir": images_data["metadata_dir"],
                "files": images_data["files"]
            })

        return {
            "type": "movies",
            "movie_collection": movie_collection,
            "library_root": library_root,
            "library_name": library_name
        }

    @staticmethod
    def show_export_preview(structured_data):
        """
        Displays a preview of the files that will be exported.

        Args:
            structured_data: Prepared export data from _prepare_*_data methods
        """
        # Print header with library name
        print(f"=== Export Preview: {structured_data['library_name']}===")

        # Handle series type export preview
        if structured_data["type"] == "series":
            for series in structured_data["series_collection"]:
                # Print series folder name and metadata directory
                print(f"\n{series['folder_name']} [Metadata: {series['metadata_dir']}]")

                # Print all series-level files (sorted alphabetically)
                for filename in sorted(series["series_files"]):
                    print(f"- {filename}")

                # Iterate through each season in the series
                for season in series["seasons"]:
                    # Print season number and metadata directory
                    print(f"\n  Season {season['season_number']} [Metdata: {series['metadata_dir']}]")

                    # Print all season-level files (sorted alphabetically)
                    for filename in sorted(season["files"]):
                        print(f"  - {filename}")

        # Handle movies type export preview
        elif structured_data["type"] == "movies":
            for movie in structured_data["movie_collection"]:
                # Print movie filename and metadata directory
                print(f"\n{movie['filename']} [Metadata: {movie['metadata_dir']}]")

                # Print all movie files (sorted alphabetically)
                for filename in sorted(movie["files"]):
                    print(f"- {filename}")