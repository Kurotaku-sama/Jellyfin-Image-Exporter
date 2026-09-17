import sys
sys.dont_write_bytecode = True
import os
import re
import shutil
from .colors import Colors

class Exporter:
    @staticmethod
    def normalize_path(path):
        """Cross-platform path normalization with optional Windows Long Path support.
        Modified to not automatically convert UNC paths to long path format.
        Only converts to long path format when path length > 260 chars.
        """
        if not path:
            return path

        # Expand ~ and resolve symlinks
        path = os.path.realpath(os.path.expanduser(path))

        # On Windows: support long paths
        if sys.platform.startswith("win"):
            # Get absolute path and its length
            abs_path = os.path.abspath(path)
            path_len = len(abs_path)

            # Only convert to long path format if path exceeds MAX_PATH (260 chars)
            if path_len > 260:
                if path.startswith("\\\\") and not path.startswith("\\\\?\\"):
                    # UNC path that needs long path handling
                    return "\\\\?\\UNC\\" + path[2:]
                elif not path.startswith("\\\\?\\"):
                    # Local path that needs long path handling
                    return "\\\\?\\" + abs_path

        # Normalize path (this doesn't change UNC/long path status)
        path = os.path.normpath(path)

        # Add trailing separator for directories
        if os.path.isdir(path) and not path.endswith(os.sep):
            path += os.sep

        return path

    @staticmethod
    def _make_long_path_aware(path):
        """Converts paths to long path format only when absolutely necessary.
        Args:
            path (str): The path to convert
        Returns:
            str: The converted path if needed, original path otherwise
        """
        if os.name == "nt":  # Windows only
            # Skip if already in long path format
            if path.startswith("\\\\?\\"):
                return path

            # Get absolute path length
            abs_path = os.path.abspath(path)
            path_len = len(abs_path)

            # Only convert if path exceeds MAX_PATH (260 chars)
            if path_len > 260:
                if path.startswith("\\\\"):
                    return "\\\\?\\UNC\\" + path[2:]  # Convert UNC path
                else:
                    return "\\\\?\\" + abs_path  # Convert local path
        return path

    @staticmethod
    def _safe_makedirs(path):
        """Creates directories with long path support and accurately tracks long path usage."""
        try:
            # Store original path for length check
            orig_path = path

            # Convert path only if needed
            path = Exporter._make_long_path_aware(path)

            # Create directory
            os.makedirs(path, exist_ok=True)

            # Check if long path was actually needed
            long_path_used = "\\\\?\\" in path and len(os.path.abspath(orig_path)) > 260

            return True, long_path_used  # Return both success status and long path flag
        except Exception as e:
            print(Colors.wrap(f"  Failed to create directory {path}: {e}", Colors.RED))
            return False, False

    @staticmethod
    def _directory_has_content(path):
        """Checks whether the given directory contains any files or subfolders."""
        try:
            return len(os.listdir(path)) > 0
        except Exception:
            return False

    @staticmethod
    def _wipe_directory_contents(path):
        """
        Deletes every file and subfolder directly inside the given
        directory while keeping the directory itself. Windows long-path
        handling is applied per entry, since a nested file can exceed
        MAX_PATH even when the directory itself does not.

        Args:
            path (str): Directory whose contents should be removed

        Returns:
            bool: True if every entry was removed without error
        """
        success = True
        for entry in os.listdir(path):
            entry_path = os.path.join(path, entry)
            try:
                long_path_entry = Exporter._make_long_path_aware(entry_path)
                if os.path.isdir(entry_path) and not os.path.islink(entry_path):
                    shutil.rmtree(long_path_entry)
                else:
                    os.remove(long_path_entry)
            except Exception as e:
                print(Colors.wrap(f"  Failed to delete {entry_path}: {e}", Colors.RED))
                success = False
        return success

    @staticmethod
    def _copy_file_with_comparison(src_path, dest_file):
        """
        Handles file copying with comprehensive version comparison and conflict resolution.
        Includes tracking for long path usage under Windows.

        Args:
            src_path (str): Absolute source file path
            dest_file (str): Absolute destination file path

        Returns:
            tuple: A 7-element tuple containing counters for:
                (files_copied, files_skipped, files_updated,
                conflicts_resolved, source_missing, error_count,
                long_path_used)

        Behavior:
            - Compares file versions using size and modification time
            - Handles Windows long paths (>260 chars) automatically
            - Tracks all operation outcomes including errors
            - Preserves original file metadata (timestamps, etc.)
        """
        # Initialize all counters:
        # [0] files_copied: New files created
        # [1] files_skipped: Identical files skipped
        # [2] files_updated: Files overwritten (source newer)
        # [3] conflicts_resolved: Files kept (destination newer)
        # [4] source_missing: Source files not found
        # [5] error_count: Operation errors
        # [6] long_path_used: Files requiring long path handling
        counters = [0, 0, 0, 0, 0, 0, 0]

        try:
            # Store original paths for length check
            orig_src = src_path
            orig_dest = dest_file

            # Convert paths only if needed
            src_path = Exporter._make_long_path_aware(src_path)
            dest_file = Exporter._make_long_path_aware(dest_file)

            # Check if long path was actually needed
            counters[6] = 1 if (src_path != orig_src or dest_file != orig_dest) else 0

            # Rest of the copy logic remains the same...
            if not os.path.exists(src_path):
                print(Colors.wrap(f"  Source file not found: {src_path}", Colors.RED))
                counters[4] = 1
                return tuple(counters)

            if os.path.exists(dest_file):
                src_stat = os.stat(src_path)
                dest_stat = os.stat(dest_file)

                if src_stat.st_size == dest_stat.st_size and src_stat.st_mtime <= dest_stat.st_mtime:
                    print(Colors.wrap(f"  Skipped (identical): {os.path.basename(dest_file)}", Colors.CYAN))
                    counters[1] = 1
                elif src_stat.st_mtime > dest_stat.st_mtime:
                    shutil.copy2(src_path, dest_file)
                    print(Colors.wrap(f"  Updated (newer version): {os.path.basename(dest_file)}", Colors.GREEN))
                    counters[2] = 1
                else:
                    print(Colors.wrap(f"  Kept existing (newer): {os.path.basename(dest_file)}", Colors.YELLOW))
                    counters[3] = 1
            else:
                shutil.copy2(src_path, dest_file)
                print(Colors.wrap(f"  Copied: {os.path.basename(dest_file)}", Colors.GREEN))
                counters[0] = 1

        except Exception as e:
            print(Colors.wrap(f"  Error processing {os.path.basename(dest_file)}: {type(e).__name__} - {str(e)}", Colors.RED))
            counters[5] = 1

        return tuple(counters)

    @staticmethod
    def _get_matching_root_index(item_path, library_roots):
        """
        Finds which library root directory matches the given item path.

        Args:
            item_path (str): Path to media file/folder
            library_roots (list): List of library root directories

        Returns:
            int or None: Index of matching root or None if no match found
        """
        # Normalize the item path for consistent comparison
        item_path = Exporter.normalize_path(item_path)

        for i, root in enumerate(library_roots):
            # Normalize the root path and ensure trailing separator
            norm_root = Exporter.normalize_path(root)
            if not norm_root.endswith(os.sep):
                norm_root += os.sep

            # Add trailing separator to item path for accurate comparison
            norm_item = item_path
            if not norm_item.endswith(os.sep):
                norm_item += os.sep

            # Check if the item path starts with the normalized root path + separator
            if norm_item.startswith(norm_root):
                return i  # Return the index of the matching root

        return None  # No matching root found

    @staticmethod
    def export_series_images(jellyfin, structured_data, export_options=None, print_summary=True):
        """
        Main method for exporting all series images including:
        - Series-level images (posters, banners)
        - Season-level images
        - Episode thumbnails (if enabled)

        Args:
            jellyfin: Jellyfin API instance
            structured_data: Dictionary containing the series collection and library info
            export_options: Dictionary containing export configuration options
            print_summary (bool): Whether to print the operation summary and
                wait for user input at the end

        Returns:
            tuple: (counters, long_path_dirs) - the operation counters and
            long path directory count
        """
        print(Colors.wrap(f"=== Exporting series images from {structured_data['library_name']} ===", Colors.CYAN, Colors.BOLD))

        # Initialize export options if not provided
        if export_options is None:
            export_options = {}

        # Get library_path from export_options instead of connection file
        library_metadata_path = Exporter.normalize_path(export_options.get('library_path', ''))

        # Ensure library_roots is always a list
        library_roots = structured_data["library_root"]
        if not isinstance(library_roots, list):
            library_roots = [library_roots] if library_roots else []

        # Initialize operation counters:
        # [0] files_copied, [1] files_skipped, [2] files_updated,
        # [3] conflicts_resolved, [4] source_missing, [5] error_count,
        # [6] long_path_files
        counters = [0]*7
        long_path_dirs = 0  # Counter for directories requiring long path support

        # Decide in advance whether only one target path should be used
        export_method = export_options.get("export_method", "single")
        target_paths = export_options.get("target_paths", [])

        # Process each series in the collection
        for series in structured_data["series_collection"]:
            if export_method == "single":
                current_target_path = target_paths[0]
            else:
                target_idx = Exporter._get_matching_root_index(series["path"], library_roots)
                if target_idx is None or target_idx >= len(target_paths):
                    print(Colors.wrap(f"WARNING: No matching root path for series {series['folder_name']}", Colors.YELLOW))
                    continue
                current_target_path = target_paths[target_idx]

            dest_dir = os.path.join(current_target_path, series["folder_name"])

            # Check if there are any files to copy before creating the directory
            has_files_to_copy = False

            # Check series-level images
            if series["metadata_dir"] and len(series["series_files"]) > 0:
                has_files_to_copy = True

            # Check season-level images
            if not has_files_to_copy and len(series["seasons"]) > 0:
                for season in series["seasons"]:
                    if season["metadata_dir"] and len(season["files"]) > 0:
                        has_files_to_copy = True
                        break

            # Check episode thumbnails if enabled
            if not has_files_to_copy and export_options.get("export_episode_thumbs", False):
                episodes = jellyfin.get_episodes(series["id"])
                for episode in episodes:
                    episode_images = jellyfin.get_item_images(episode["Id"])
                    if episode_images["metadata_dir"] and len(episode_images["files"]) > 0:
                        has_files_to_copy = True
                        break

            # Only proceed if there are files to copy
            if not has_files_to_copy:
                print(Colors.wrap(f"\n\nSkipping series {series['folder_name']} - no images to export", Colors.YELLOW))
                continue

            # Create destination folder only if there are files to copy
            success, is_long_path = Exporter._safe_makedirs(dest_dir)
            if success and is_long_path:
                long_path_dirs += 1

            print(Colors.wrap(f"\n\nProcessing series: {series['folder_name']} (to {dest_dir})", Colors.BLUE, Colors.BOLD))

            # Execute all processing steps in sequence:
            processors = [
                # 1. Process series-level images
                lambda: Exporter._process_series_images(series, dest_dir, library_metadata_path),

                # 2. Process season images
                lambda: Exporter._process_season_images(series, dest_dir, library_metadata_path),

                # 3. Process episode thumbnails (if enabled)
                lambda: Exporter._process_episode_thumbnails(jellyfin, series, current_target_path, library_metadata_path)
                    if export_options.get("export_episode_thumbs", False)
                    else (0,) * 7  # Return zero counters if disabled
            ]

            for processor in processors:
                result = processor()  # Execute current step
                counters = [sum(x) for x in zip(counters, result)]  # Aggregate results

        # Display final summary with all counters
        if print_summary:
            Exporter._print_export_summary(counters, long_path_dirs, export_options.get("automation_mode", False))
        return counters, long_path_dirs

    @staticmethod
    def _process_series_images(series, dest_dir, library_metadata_path):
        """
        Processes all series-level images (posters, banners, logos, etc.)

        Args:
            series (dict): Series data including:
                - metadata_dir
                - series_files (list of image files)
            dest_dir (str): Destination directory path
            library_metadata_path (str): Base metadata directory

        Returns:
            tuple: Counters for various operations (7 values)
        """
        # Initialize counters (same structure as export_series_images)
        counters = [0]*7

        # Skip if no metadata directory available or no metadata found
        if not series["metadata_dir"] or len(series["series_files"]) == 0:
            print(Colors.wrap("  No images found", Colors.YELLOW))
            return tuple(counters)

        # Process each series-level image file
        for filename in series["series_files"]:
            try:
                # Build full source and destination paths
                src_path = os.path.join(library_metadata_path, series["metadata_dir"], filename)
                dest_file = os.path.join(dest_dir, filename)

                # Copy file (with comparison logic) and get operation results
                new_counts = Exporter._copy_file_with_comparison(src_path, dest_file)

                # Update main counters
                counters = [sum(x) for x in zip(counters, new_counts)]
            except Exception as e:
                print(Colors.wrap(f"  Error processing {filename}: {e}", Colors.RED))
                counters[5] += 1  # Increment error counter

        return tuple(counters)

    @staticmethod
    def _process_season_images(series, dest_dir, library_metadata_path):
        """
        Handles the export of all season-level images for a series.

        Args:
            series (dict): Series data containing season information
            dest_dir (str): Destination directory for the series
            library_metadata_path (str): Base path for metadata files

        Returns:
            tuple: Counters for various operations (copied, skipped, etc.)
        """
        # Initialize counters for all operation types
        counters = [0]*7  # [copied, skipped, updated, kept, missing, errors, long_paths]
        # Process each season in the series
        if len(series["seasons"]) > 0:
            print(Colors.wrap("Processing season images:", Colors.MAGENTA))
        for season in series["seasons"]:
            # Process each image file in the season
            for filename in season["files"]:
                try:
                    # Skip if no metadata directory exists for this season
                    if not season["metadata_dir"]:
                        continue

                    # Build full source path
                    src_path = os.path.join(library_metadata_path, season["metadata_dir"], filename)

                    # Special handling for season posters
                    if "poster" in filename.lower():
                        if season["season_number"] == 0:
                            # Format special seasons (season 0)
                            new_name = f"season-specials-poster{os.path.splitext(filename)[1]}"
                        else:
                            try:
                                # Format regular seasons with zero-padded numbers (e.g., S01, S02)
                                season_num = int(season["season_number"])
                                new_name = f"season{season_num:02d}-poster{os.path.splitext(filename)[1]}"
                            except (ValueError, TypeError):
                                # Fallback to original filename if season number is invalid
                                new_name = filename
                        dest_file = os.path.join(dest_dir, new_name)
                    else:
                        # Use original filename for non-poster images
                        dest_file = os.path.join(dest_dir, filename)

                    # Copy file and update counters
                    new_counts = Exporter._copy_file_with_comparison(src_path, dest_file)
                    counters = [sum(x) for x in zip(counters, new_counts)]

                except Exception as e:
                    print(Colors.wrap(f"Error processing {filename}: {e}", Colors.RED))
                    counters[5] += 1  # Increment error counter
        if sum(counters) == 0:
            print(Colors.wrap("  No images found", Colors.YELLOW))

        return tuple(counters)

    @staticmethod
    def _process_episode_thumbnails(jellyfin, series, target_path, library_metadata_path):
        """
        Exports episode thumbnails if enabled in export options.
        """
        counters = [0]*7  # Initialize all counters to 0

        # Get all episodes for the series from Jellyfin
        episodes = jellyfin.get_episodes(series["id"])

        # Fetch each episode's image metadata once and reuse it for both the
        # pre-check below and the processing loop that follows.
        episode_images_by_id = {
            episode["Id"]: jellyfin.get_item_images(episode["Id"]) for episode in episodes
        }

        # Check if there are any episode thumbnails to copy
        has_thumbnails_to_copy = any(
            images["metadata_dir"] and any(f.lower() == "poster.jpg" for f in images["files"])
            for images in episode_images_by_id.values()
        )

        if not has_thumbnails_to_copy:
            print(Colors.wrap("  No episode thumbnails found", Colors.YELLOW))
            return tuple(counters)

        print(Colors.wrap("Processing episode thumbnails:", Colors.MAGENTA))
        for episode in episodes:
            try:
                # Reuse the image metadata fetched above instead of querying again
                episode_images = episode_images_by_id[episode["Id"]]

                # Skip if no valid metadata or path
                if not episode_images["metadata_dir"] or not episode.get("Path", ""):
                    continue

                # Calculate relative path within the series
                rel_path = os.path.dirname(episode["Path"].replace(series["path"], "", 1)).strip("/\\")
                dest_dir = os.path.join(target_path, series["folder_name"], rel_path)

                # Only create directory if we actually have thumbnails to copy
                if any(f.lower() == "poster.jpg" for f in episode_images["files"]):
                    # Create the destination directory and track whether it
                    # required Windows long-path handling.
                    success, is_long_path = Exporter._safe_makedirs(dest_dir)
                    if success and is_long_path:
                        counters[6] += 1

                # Sanitize episode name for filesystem use
                episode_name = re.sub(r'[\\/*?:"<>|]', "",
                                    os.path.splitext(os.path.basename(episode["Path"]))[0])

                # Process each image file (we only want poster.jpg)
                for filename in episode_images["files"]:
                    try:
                        # Skip non-thumbnail files
                        if filename.lower() != "poster.jpg":
                            continue

                        # Build full paths
                        src_path = os.path.join(library_metadata_path,
                                            episode_images["metadata_dir"],
                                            filename)
                        dest_file = os.path.join(dest_dir, f"{episode_name}-thumb.jpg")

                        # Copy and count operations
                        new_counts = Exporter._copy_file_with_comparison(src_path, dest_file)
                        counters = [sum(x) for x in zip(counters, new_counts)]

                    except Exception as e:
                        print(Colors.wrap(f"Error processing episode thumb {filename}: {e}", Colors.RED))
                        counters[5] += 1

            except Exception as e:
                print(Colors.wrap(f"Error processing episode: {e}", Colors.RED))
                counters[5] += 1

        return tuple(counters)

    @staticmethod
    def export_movie_images(jellyfin, structured_data, export_options, print_summary=True):
        """
        Main method for exporting images for a flat, non-nested media
        collection while preserving folder structure. Used for movies,
        music videos, and home videos, since all three share the same
        per-item image layout.

        Args:
            jellyfin: Jellyfin API instance
            structured_data: Dictionary containing the item collection and library info
            export_options: Dictionary containing export configuration options
            print_summary (bool): Whether to print the operation summary and
                wait for user input at the end

        Returns:
            tuple: (counters, long_path_dirs) - the operation counters and
            long path directory count
        """
        print(Colors.wrap(f"=== Exporting images from {structured_data['library_name']} ===", Colors.CYAN, Colors.BOLD))

        # Get library_path from export_options instead of connection file
        library_metadata_path = Exporter.normalize_path(export_options.get('library_path', ''))

        # Ensure library_roots is always a list
        library_roots = structured_data["library_root"]
        if not isinstance(library_roots, list):
            library_roots = [library_roots] if library_roots else []

        # Initialize operation counters:
        # [0] files_copied, [1] files_skipped, [2] files_updated,
        # [3] conflicts_resolved, [4] source_missing, [5] error_count,
        # [6] long_path_files
        counters = [0]*7
        long_path_dirs = 0  # Counter for directories requiring long path support

        # Get export method and target paths from options
        export_method = export_options["export_method"]
        target_paths = export_options["target_paths"]

        # Process each movie in the collection
        for movie in structured_data["movie_collection"]:
            # Determine target path based on export method
            if export_method == "single":
                current_target_path = target_paths[0]
                # In single path mode, find matching root to calculate correct relative path
                target_idx = Exporter._get_matching_root_index(movie["path"], library_roots)
                if target_idx is None:
                    print(Colors.wrap(f"WARNING: No matching root path for movie {movie['filename']}", Colors.YELLOW))
                    continue
            else:
                # In separate paths mode, find matching root and corresponding target path
                target_idx = Exporter._get_matching_root_index(movie["path"], library_roots)
                if target_idx is None or target_idx >= len(target_paths):
                    print(Colors.wrap(f"WARNING: No matching root path for movie {movie['filename']}", Colors.YELLOW))
                    continue
                current_target_path = target_paths[target_idx]

            # Calculate relative path from library root
            # First normalize both paths for accurate comparison
            norm_movie_path = Exporter.normalize_path(movie["path"])
            norm_library_root = Exporter.normalize_path(library_roots[target_idx])

            # Ensure library root ends with separator for proper path replacement
            if not norm_library_root.endswith(os.sep):
                norm_library_root += os.sep

            # Get relative path by removing library root from movie path
            if norm_movie_path.startswith(norm_library_root):
                rel_path = norm_movie_path[len(norm_library_root):]
            else:
                # Fallback for unexpected cases
                rel_path = os.path.dirname(norm_movie_path)

            # Get directory portion (remove filename) and clean path
            rel_path = os.path.dirname(rel_path).strip("/\\")

            # Construct full destination directory path
            dest_dir = os.path.join(current_target_path, rel_path)

            # Check if there are any files to copy before creating the directory
            has_files_to_copy = movie["metadata_dir"] and len(movie["files"]) > 0

            # Only proceed if there are files to copy
            if not has_files_to_copy:
                print(Colors.wrap(f"\nSkipping movie {movie['filename']} - no images to export", Colors.YELLOW))
                continue

            # Create destination directory (with long path support) only if files exist
            success, is_long_path = Exporter._safe_makedirs(dest_dir)
            if success and is_long_path:
                long_path_dirs += 1

            print(Colors.wrap(f"\nProcessing movie: {movie['filename']} in {dest_dir}", Colors.BLUE, Colors.BOLD))

            # Process each image file associated with the movie
            for filename in movie["files"]:
                try:
                    # Skip if no metadata directory
                    if not movie["metadata_dir"]:
                        continue

                    # Build full source path
                    src_path = os.path.join(library_metadata_path, movie["metadata_dir"], filename)

                    # Skip if source file doesn't exist
                    if not os.path.exists(src_path):
                        print(f"  Source file not found: {src_path}")
                        counters[4] += 1
                        continue

                    # Create destination filename pattern: moviename-imagetype.ext
                    # Remove video extension from the movie filename
                    base_name = os.path.splitext(movie["filename"])[0]
                    # Extract extension and image type from the image file
                    ext = os.path.splitext(filename)[1]
                    image_type = os.path.splitext(filename)[0]
                    # Final destination filename without video extension
                    dest_file = os.path.join(dest_dir, f"{base_name}-{image_type}{ext}")

                    # Copy file and update counters
                    new_counts = Exporter._copy_file_with_comparison(src_path, dest_file)
                    counters = [sum(x) for x in zip(counters, new_counts)]

                except Exception as e:
                    print(Colors.wrap(f"Error processing {filename}: {e}", Colors.RED))
                    counters[5] += 1

        # Display final operation summary
        if print_summary:
            Exporter._print_export_summary(counters, long_path_dirs, export_options.get("automation_mode", False))
        return counters, long_path_dirs

    @staticmethod
    def export_mixed_images(jellyfin, structured_data, export_options=None):
        """
        Main method for exporting a mixed library. Runs the series and
        movie collections back to back and prints one combined summary at
        the end.

        Args:
            jellyfin: Jellyfin API instance
            structured_data: Dictionary containing the series and movie
                collections along with library info
            export_options: Dictionary containing export configuration options
        """
        if export_options is None:
            export_options = {}

        series_items = structured_data.get("series_collection", [])
        movie_items = structured_data.get("movie_collection", [])
        library_root = structured_data.get("library_root")
        library_name = structured_data.get("library_name")

        combined_counters = [0]*7
        combined_long_path_dirs = 0

        if series_items:
            series_data = {
                "type": "series",
                "series_collection": series_items,
                "library_root": library_root,
                "library_name": library_name
            }
            counters, long_path_dirs = Exporter.export_series_images(jellyfin, series_data, export_options, print_summary=False)
            combined_counters = [sum(x) for x in zip(combined_counters, counters)]
            combined_long_path_dirs += long_path_dirs

        if movie_items:
            movie_data = {
                "type": "movies",
                "movie_collection": movie_items,
                "library_root": library_root,
                "library_name": library_name
            }
            counters, long_path_dirs = Exporter.export_movie_images(jellyfin, movie_data, export_options, print_summary=False)
            combined_counters = [sum(x) for x in zip(combined_counters, counters)]
            combined_long_path_dirs += long_path_dirs

        # Display one combined summary for both collections
        Exporter._print_export_summary(combined_counters, combined_long_path_dirs, export_options.get("automation_mode", False))

    @staticmethod
    def export_music_images(jellyfin, structured_data, export_options=None):
        """
        Main method for exporting album-level images from a music library.

        Each album is a single folder of images (cover, backdrop, banner,
        logo, etc.) with no further nesting below it, so every file found
        for an album is copied into that album's destination folder. The
        primary cover image is cached as folder.ext and gets renamed to
        either folder.ext or cover.ext depending on export_options, since
        Jellyfin itself writes folder.ext when saving artwork into media
        folders while other tools commonly expect cover.ext; every other
        file keeps its original filename, the same way series-level images
        are handled for a series.

        Args:
            jellyfin: Jellyfin API instance
            structured_data: Dictionary containing the album collection and library info
            export_options: Dictionary containing export configuration options
        """
        print(Colors.wrap(f"=== Exporting images from {structured_data['library_name']} ===", Colors.CYAN, Colors.BOLD))

        if export_options is None:
            export_options = {}

        # Get library_path from export_options instead of connection file
        library_metadata_path = Exporter.normalize_path(export_options.get('library_path', ''))

        # Ensure library_roots is always a list
        library_roots = structured_data["library_root"]
        if not isinstance(library_roots, list):
            library_roots = [library_roots] if library_roots else []

        # Initialize operation counters:
        # [0] files_copied, [1] files_skipped, [2] files_updated,
        # [3] conflicts_resolved, [4] source_missing, [5] error_count,
        # [6] long_path_files
        counters = [0]*7
        long_path_dirs = 0  # Counter for directories requiring long path support

        export_method = export_options.get("export_method", "single")
        target_paths = export_options.get("target_paths", [])

        # Process each album in the collection
        for album in structured_data["album_collection"]:
            # Determine target path based on export method
            if export_method == "single":
                current_target_path = target_paths[0]
                target_idx = Exporter._get_matching_root_index(album["path"], library_roots)
                if target_idx is None:
                    print(Colors.wrap(f"WARNING: No matching root path for album {album['folder_name']}", Colors.YELLOW))
                    continue
            else:
                target_idx = Exporter._get_matching_root_index(album["path"], library_roots)
                if target_idx is None or target_idx >= len(target_paths):
                    print(Colors.wrap(f"WARNING: No matching root path for album {album['folder_name']}", Colors.YELLOW))
                    continue
                current_target_path = target_paths[target_idx]

            # Calculate the album's path relative to its library root, so an
            # artist folder the album sits under is preserved in the export
            norm_album_path = Exporter.normalize_path(album["path"])
            norm_library_root = Exporter.normalize_path(library_roots[target_idx])

            if not norm_library_root.endswith(os.sep):
                norm_library_root += os.sep

            if norm_album_path.startswith(norm_library_root):
                rel_path = norm_album_path[len(norm_library_root):].strip("/\\")
            else:
                rel_path = album["folder_name"]

            dest_dir = os.path.join(current_target_path, rel_path)

            # Only proceed if there are files to copy
            has_files_to_copy = album["metadata_dir"] and len(album["files"]) > 0
            if not has_files_to_copy:
                print(Colors.wrap(f"\nSkipping album {album['folder_name']} - no images to export", Colors.YELLOW))
                continue

            # Create destination folder only if there are files to copy
            success, is_long_path = Exporter._safe_makedirs(dest_dir)
            if success and is_long_path:
                long_path_dirs += 1

            print(Colors.wrap(f"\nProcessing album: {album['folder_name']} (to {dest_dir})", Colors.BLUE, Colors.BOLD))

            # Copy every album-level image file, renaming the primary cover
            # image to the configured filename convention
            cover_name = export_options.get("music_folder_name", "folder")
            for filename in album["files"]:
                try:
                    src_path = os.path.join(library_metadata_path, album["metadata_dir"], filename)

                    if os.path.splitext(filename)[0].lower() == "folder":
                        dest_filename = f"{cover_name}{os.path.splitext(filename)[1]}"
                    else:
                        dest_filename = filename
                    dest_file = os.path.join(dest_dir, dest_filename)

                    new_counts = Exporter._copy_file_with_comparison(src_path, dest_file)
                    counters = [sum(x) for x in zip(counters, new_counts)]
                except Exception as e:
                    print(Colors.wrap(f"  Error processing {filename}: {e}", Colors.RED))
                    counters[5] += 1

        # Display final summary with all counters
        Exporter._print_export_summary(counters, long_path_dirs, export_options.get("automation_mode", False))

    @staticmethod
    def _print_export_summary(counters, long_path_dirs=0, automation_mode=False):
        """Enhanced summary with all counters."""
        (
            files_copied,
            files_skipped,
            files_updated,
            conflicts_resolved,
            source_missing,
            error_count,
            long_path_files
        ) = counters

        print(Colors.wrap("\n=== Operation Summary ===", Colors.CYAN, Colors.BOLD))
        print(Colors.wrap(f"Files successfully copied:       {files_copied}", Colors.GREEN))
        print(Colors.wrap(f"Files skipped (identical):       {files_skipped}", Colors.CYAN))
        print(Colors.wrap(f"Files updated (newer version):   {files_updated}", Colors.GREEN))
        print(Colors.wrap(f"Files kept (destination newer):  {conflicts_resolved}", Colors.YELLOW))
        print(Colors.wrap(f"Source files missing:            {source_missing}", Colors.RED if source_missing else Colors.RESET))
        print(Colors.wrap(f"Errors encountered:              {error_count}", Colors.RED if error_count else Colors.RESET))
        if os.name == "nt":  # Only show on Windows
            print(f"Files with long paths handled:   {long_path_files}")
            print(f"Folders with long paths:         {long_path_dirs}")
        print(Colors.wrap("=========================", Colors.CYAN, Colors.BOLD))
        if automation_mode is False:
            input("\nExport completed. Press Enter to return to the library menu...")