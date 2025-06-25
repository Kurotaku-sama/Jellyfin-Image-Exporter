import sys
sys.dont_write_bytecode = True
import json
import re
import urllib.request

class Jellyfin:
    """
    A class to interact with Jellyfin media server API.
    Handles authentication, data retrieval, and media library operations.
    """

    def __init__(self, url=None, api_key=None, library_path=None):
        """
        Initialize the Jellyfin API client.

        Args:
            url (str): Base URL of the Jellyfin server
            api_key (str): API key for authentication
            library_path (str): Path to Jellyfin metadata folder
        """
        self.url = url
        self.api_key = api_key
        self.library_path = library_path

    def _get_headers(self):
        """Return headers required for Jellyfin API requests"""
        return {
            "X-Emby-Token": self.api_key,   # Authentication header
            "Accept": "application/json"    # Request JSON responses
        }

    def _get_json(self, path):
        """
        Helper method to make GET requests to Jellyfin API and return JSON data.

        Args:
            path (str): API endpoint path (relative to base URL)

        Returns:
            list/dict: Parsed JSON response or empty list on error
        """
        try:
            req = urllib.request.Request(
                f"{self.url}/{path}",
                headers=self._get_headers()
            )
            with urllib.request.urlopen(req) as response:
                data = json.load(response)
                return data.get("Items", []) if isinstance(data, dict) else data
        except Exception as e:
            print(f"Error fetching {path}: {e}")
            return []

    def test_connection(self):
        """
        Test connection to Jellyfin server by making a simple API call.
        Automatically detects HTTP/HTTPS if protocol isn't specified.

        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self.url or not self.api_key:
            return False

        # Try both protocols if URL doesn't specify one
        protocols = ["http://", "https://"]
        if self.url.startswith("http://") or self.url.startswith("https://"):
            protocols = [""]  # Already has protocol

        for proto in protocols:
            try:
                test_url = f"{proto}{self.url}/Users"
                req = urllib.request.Request(
                    test_url,
                    headers=self._get_headers()
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    if response.status == 200:
                        self.url = f"{proto}{self.url}"  # Save correct URL format
                        return True
            except Exception as e:
                print(f"Connection failed for {test_url}: {e}")
                continue
        return False

    def get_item_images(self, item_id):
        """
        Get metadata about images associated with a specific media item.

        Args:
            item_id (str): Jellyfin ID of the media item

        Returns:
            dict: Contains metadata directory path and list of image files
                  Format: {'metadata_dir': str, 'files': list}
        """
        try:
            req = urllib.request.Request(
                f"{self.url}/Items/{item_id}/Images",
                headers=self._get_headers()
            )
            with urllib.request.urlopen(req) as response:
                images = json.load(response)
                files = []
                metadata_dir = None

                # Extract metadata directory and filenames from image paths
                for image in images:
                    if "Path" in image:
                        # Pattern explanation:
                        # library/ - constant path segment
                        # (\w{2}/\w{32}) - captures metadata dir (2 hex chars + 32 hex chars)
                        # /(.+) - captures filename
                        match = re.search(r"library/(\w{2}/\w{32})/(.+)", image["Path"])

                        if match:
                            if not metadata_dir:  # Only set metadata_dir once
                                metadata_dir = match.group(1)
                            files.append(match.group(2))

                return {
                    "metadata_dir": metadata_dir,  # Directory where images are stored
                    "files": files                 # List of image filenames
                }
        except Exception as e:
            print(f"Error fetching actual image files: {str(e)}")
            return {"metadata_dir": None, "files": []}

    def get_libraries(self):
        """
        Get list of all media libraries from Jellyfin server.

        Returns:
            list: List of library objects or empty list on error
        """
        try:
            libraries = self._get_json("Library/VirtualFolders")
            return libraries if isinstance(libraries, list) else []
        except Exception as e:
            print(f"Error while fetching libraries: {e}")
            return []

    def get_library_items(self, library_id):
        """
        Get all items (movies/series) in a specific library.

        Args:
            library_id (str): ID of the library to query

        Returns:
            list: List of media items or empty list on error
        """
        try:
            url = (
                f"{self.url}/Items?"
                f"ParentId={library_id}&"
                f"Recursive=true&"
                f"IncludeItemTypes=Movie,Series&"
                f"fields=Path,ImageTags,Id,Name,Type"
            )
            req = urllib.request.Request(url, headers=self._get_headers())
            with urllib.request.urlopen(req) as response:
                return json.load(response).get("Items", [])
        except Exception as e:
            print(f"Error fetching library items: {str(e)}")
            return []

    def get_seasons(self, series_id):
        """
        Get all seasons for a TV series.

        Args:
            series_id (str): ID of the series

        Returns:
            list: List of season objects or empty list on error
        """
        try:
            url = f"{self.url}/Shows/{series_id}/Seasons"
            req = urllib.request.Request(url, headers=self._get_headers())
            with urllib.request.urlopen(req) as response:
                return json.load(response).get("Items", [])
        except Exception as e:
            print(f"Error fetching seasons: {str(e)}")
            return []

    def get_episodes(self, series_id):
        """
        Get all episodes for a TV series with their paths and numbering.

        Args:
            series_id (str): ID of the series

        Returns:
            list: List of episode objects or empty list on error
        """
        try:
            url = f"{self.url}/Shows/{series_id}/Episodes?Fields=Path,ParentIndexNumber,IndexNumber"
            req = urllib.request.Request(url, headers=self._get_headers())
            with urllib.request.urlopen(req) as response:
                data = json.load(response)
                return data.get("Items", [])
        except Exception as e:
            print(f"Error fetching episodes: {str(e)}")
            return []

    def get_series_paths(self, library_id):
        """
        Get paths for all TV series in a library (legacy method).

        Args:
            library_id (str): ID of the library

        Returns:
            list: List of dictionaries with series paths
        """
        results = []
        items = self.get_library_items(library_id)
        for item in items:
            if item.get("Type") == "Series" and (item_path := item.get("Path")):
                results.append({"type": "tvshow", "path": item_path})
        return results