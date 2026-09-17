import sys
sys.dont_write_bytecode = True
import os
from .colors import Colors

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
        # CollectionType can be explicitly null in the Jellyfin API response
        # for libraries without a fixed content type, so fall back to an
        # empty string before lowercasing it.
        collection_type = (library_obj.get("CollectionType") or "").lower()

        # Route to appropriate preparation method based on library type
        if collection_type == "tvshows":
            return ExportPrepare._prepare_series_data(jellyfin, library_obj)
        elif collection_type == "movies":
            return ExportPrepare._prepare_movie_data(jellyfin, library_obj)
        elif collection_type == "musicvideos":
            return ExportPrepare._prepare_musicvideo_data(jellyfin, library_obj)
        elif collection_type == "homevideos":
            return ExportPrepare._prepare_homevideo_data(jellyfin, library_obj)
        elif collection_type == "music":
            return ExportPrepare._prepare_music_data(jellyfin, library_obj)
        elif collection_type == "":
            return ExportPrepare._prepare_mixed_data(jellyfin, library_obj)

        print(Colors.wrap(f"\nERROR: Unsupported Library Type: {collection_type}", Colors.RED))
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
            print(Colors.wrap("\nNo series found in this library", Colors.YELLOW))
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
            print(Colors.wrap("\nNo movies found in this library", Colors.YELLOW))
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
    def _prepare_musicvideo_data(jellyfin, library_obj):
        """
        Prepares structured data for a Music Videos library export.

        Music video items sit directly under the library root with no
        season/episode nesting, so they share the exact same per-item shape
        as movies and are exported through the same movie export path.

        Args:
            jellyfin: Jellyfin API client instance
            library_obj: Dictionary containing library information

        Returns:
            Dictionary containing:
            - type: 'musicvideos'
            - movie_collection: List of music video item data
            - library_root: Root paths of the library
            - library_name: Name of the library
        """
        library_id = library_obj["ItemId"]
        library_root = library_obj.get("Locations", [])
        library_name = library_obj["Name"]

        items = jellyfin.get_library_items(library_id, item_types="MusicVideo")
        if not items:
            print(Colors.wrap("\nNo music videos found in this library", Colors.YELLOW))
            return None

        movie_collection = []

        for item in items:
            if item.get("Type") != "MusicVideo":
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
            "type": "musicvideos",
            "movie_collection": movie_collection,
            "library_root": library_root,
            "library_name": library_name
        }

    @staticmethod
    def _prepare_homevideo_data(jellyfin, library_obj):
        """
        Prepares structured data for a Home Videos & Photos library export.

        Requesting only the "Video" item type keeps standalone Photo and
        PhotoAlbum items out of the result entirely, since those have no
        video file to attach companion artwork to. Video items in this
        library type share the same flat, per-item shape as movies and are
        exported through the same movie export path.

        Args:
            jellyfin: Jellyfin API client instance
            library_obj: Dictionary containing library information

        Returns:
            Dictionary containing:
            - type: 'homevideos'
            - movie_collection: List of video item data
            - library_root: Root paths of the library
            - library_name: Name of the library
        """
        library_id = library_obj["ItemId"]
        library_root = library_obj.get("Locations", [])
        library_name = library_obj["Name"]

        items = jellyfin.get_library_items(library_id, item_types="Video")
        if not items:
            print(Colors.wrap("\nNo videos found in this library", Colors.YELLOW))
            return None

        movie_collection = []

        for item in items:
            if item.get("Type") != "Video":
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
            "type": "homevideos",
            "movie_collection": movie_collection,
            "library_root": library_root,
            "library_name": library_name
        }

    @staticmethod
    def _prepare_music_data(jellyfin, library_obj):
        """
        Prepares structured data for a Music library export.

        Album items sit directly under the library root (or under an
        artist folder), each with its own set of images such as the cover,
        backdrop, banner, and logo. There is no further nesting to export
        below album level, so each album is handled as a single folder of
        images, the same way series-level images are handled for a series.

        Args:
            jellyfin: Jellyfin API client instance
            library_obj: Dictionary containing library information

        Returns:
            Dictionary containing:
            - type: 'music'
            - album_collection: List of album data
            - library_root: Root paths of the library
            - library_name: Name of the library
        """
        library_id = library_obj["ItemId"]
        library_root = library_obj.get("Locations", [])
        library_name = library_obj["Name"]

        items = jellyfin.get_library_items(library_id, item_types="MusicAlbum")
        if not items:
            print(Colors.wrap("\nNo albums found in this library", Colors.YELLOW))
            return None

        album_collection = []

        for item in items:
            if item.get("Type") != "MusicAlbum":
                continue

            item_path = item.get("Path", "")
            folder_name = os.path.basename(item_path.rstrip("/"))
            images_data = jellyfin.get_item_images(item["Id"])

            album_collection.append({
                "id": item["Id"],
                "folder_name": folder_name,
                "metadata_dir": images_data["metadata_dir"],
                "files": images_data["files"],
                "path": item_path
            })

        return {
            "type": "music",
            "album_collection": album_collection,
            "library_root": library_root,
            "library_name": library_name
        }

    @staticmethod
    def _prepare_mixed_data(jellyfin, library_obj):
        """
        Prepares structured data for a library with no fixed content type,
        where movies and series sit side by side. Each item is routed to
        the same series or movie handling used for a dedicated library of
        that type.

        Args:
            jellyfin: Jellyfin API client instance
            library_obj: Dictionary containing library information

        Returns:
            Dictionary containing:
            - type: 'mixed'
            - series_collection: List of series data
            - movie_collection: List of movie data
            - library_root: Root paths of the library
            - library_name: Name of the library
        """
        library_id = library_obj["ItemId"]
        library_root = library_obj.get("Locations", [])
        library_name = library_obj["Name"]

        items = jellyfin.get_library_items(library_id)
        if not items:
            print(Colors.wrap("\nNo movies or series found in this library", Colors.YELLOW))
            return None

        series_collection = []
        movie_collection = []

        for item in items:
            item_type = item.get("Type")

            if item_type == "Series":
                item_path = item.get("Path", "")
                folder_name = os.path.basename(item_path.rstrip("/"))
                images_data = jellyfin.get_item_images(item["Id"])

                seasons_data = []
                seasons = jellyfin.get_seasons(item["Id"])
                for season in seasons:
                    season_images = jellyfin.get_item_images(season["Id"])
                    seasons_data.append({
                        "season_number": season.get("IndexNumber", "Unknown"),
                        "metadata_dir": season_images["metadata_dir"],
                        "files": season_images["files"]
                    })

                series_collection.append({
                    "id": item["Id"],
                    "folder_name": folder_name,
                    "metadata_dir": images_data["metadata_dir"],
                    "series_files": images_data["files"],
                    "seasons": seasons_data,
                    "path": item_path
                })

            elif item_type == "Movie":
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

        if not series_collection and not movie_collection:
            print(Colors.wrap("\nNo movies or series found in this library", Colors.YELLOW))
            return None

        return {
            "type": "mixed",
            "series_collection": series_collection,
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
        print(Colors.wrap(f"=== Export Preview: {structured_data['library_name']}===", Colors.CYAN, Colors.BOLD))

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

        # Handle movies, music videos and home videos export preview - all
        # three share the same flat, per-item collection shape
        elif structured_data["type"] in ("movies", "musicvideos", "homevideos"):
            for movie in structured_data["movie_collection"]:
                # Print item filename and metadata directory
                print(f"\n{movie['filename']} [Metadata: {movie['metadata_dir']}]")

                # Print all item files (sorted alphabetically)
                for filename in sorted(movie["files"]):
                    print(f"- {filename}")

        # Handle music library export preview
        elif structured_data["type"] == "music":
            for album in structured_data["album_collection"]:
                # Print album folder name and metadata directory
                print(f"\n{album['folder_name']} [Metadata: {album['metadata_dir']}]")

                # Print all album-level files (sorted alphabetically)
                for filename in sorted(album["files"]):
                    print(f"- {filename}")

        # Handle mixed library export preview - series and movies each in
        # their own section
        elif structured_data["type"] == "mixed":
            if structured_data["series_collection"]:
                print(Colors.wrap("\n=== Series Items ===", Colors.BLUE, Colors.BOLD))
                for series in structured_data["series_collection"]:
                    print(f"\n{series['folder_name']} [Metadata: {series['metadata_dir']}]")
                    for filename in sorted(series["series_files"]):
                        print(f"- {filename}")
                    for season in series["seasons"]:
                        print(f"\n  Season {season['season_number']} [Metdata: {series['metadata_dir']}]")
                        for filename in sorted(season["files"]):
                            print(f"  - {filename}")

            if structured_data["movie_collection"]:
                print(Colors.wrap("\n=== Movie Items ===", Colors.BLUE, Colors.BOLD))
                for movie in structured_data["movie_collection"]:
                    print(f"\n{movie['filename']} [Metadata: {movie['metadata_dir']}]")
                    for filename in sorted(movie["files"]):
                        print(f"- {filename}")