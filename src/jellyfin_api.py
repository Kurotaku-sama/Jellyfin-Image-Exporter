import sys
sys.dont_write_bytecode = True
import json
import re
import urllib.request
import urllib.error
from .version import VERSION

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

        # Index into _auth_header_styles() that last succeeded for this
        # instance. None until the first request, at which point both
        # styles get tried once and whichever works is locked in.
        self._working_auth_index = None

    def _auth_header_styles(self):
        """
        Returns both known Jellyfin auth header styles, in the order they
        should be tried. The new Authorization header is required by
        Jellyfin 12.0+, since 12.0 disabled the legacy X-Emby-Token header
        by default. Older Jellyfin versions (10.x) still require
        X-Emby-Token instead.
        """
        return (
            {"Authorization": f'MediaBrowser Token="{self.api_key}"'},
            {"X-Emby-Token": self.api_key},
        )

    def _request_with_auth_fallback(self, url, timeout=None):
        """
        Opens a Jellyfin API URL, trying the last known-working auth header
        style first (both styles on the very first call for this instance).
        Falls back to the other style only if the current one is rejected
        with 401, and remembers whichever style succeeds so later calls
        use it directly instead of testing both every time.

        Args:
            url (str): Full request URL
            timeout (int|None): Optional request timeout in seconds

        Returns:
            http.client.HTTPResponse: The opened response, ready for a
            `with` block by the caller

        Raises:
            urllib.error.HTTPError: If neither header style is accepted,
                the last 401 is re-raised. Any non-401 HTTP error is
                raised immediately without trying the other style.
        """
        styles = self._auth_header_styles()
        start_index = self._working_auth_index if self._working_auth_index is not None else 0

        last_error = None
        for offset in range(len(styles)):
            index = (start_index + offset) % len(styles)
            headers = {
                **styles[index],
                "Accept": "application/json",
                "User-Agent": f"JellyfinImageExporter/{VERSION}",
            }
            req = urllib.request.Request(url, headers=headers)

            try:
                response = urllib.request.urlopen(req, timeout=timeout)
                self._working_auth_index = index
                return response
            except urllib.error.HTTPError as e:
                last_error = e
                if e.code != 401:
                    raise
                continue

        raise last_error

    def _get_json(self, path):
        """
        Helper method to make GET requests to Jellyfin API and return JSON data.

        Args:
            path (str): API endpoint path (relative to base URL)

        Returns:
            list/dict: Parsed JSON response or empty list on error
        """
        try:
            with self._request_with_auth_fallback(f"{self.url}/{path}") as response:
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
            test_url = f"{proto}{self.url}/Users"
            try:
                with self._request_with_auth_fallback(test_url, timeout=5) as response:
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
            with self._request_with_auth_fallback(f"{self.url}/Items/{item_id}/Images") as response:
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

    def get_library_items(self, library_id, item_types="Movie,Series"):
        """
        Get all items of the given type(s) in a specific library.

        Args:
            library_id (str): ID of the library to query
            item_types (str): Comma-separated Jellyfin item type names to
                request from the API, e.g. "Movie,Series", "MusicVideo",
                "Video", or "MusicAlbum". Filtering by type here means the
                server only returns items of that kind, instead of every
                item under the library being fetched and filtered locally.

        Returns:
            list: List of media items or empty list on error
        """
        try:
            url = (
                f"{self.url}/Items?"
                f"ParentId={library_id}&"
                f"Recursive=true&"
                f"IncludeItemTypes={item_types}&"
                f"fields=Path,ImageTags,Id,Name,Type"
            )
            with self._request_with_auth_fallback(url) as response:
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
            with self._request_with_auth_fallback(url) as response:
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
            with self._request_with_auth_fallback(url) as response:
                data = json.load(response)
                return data.get("Items", [])
        except Exception as e:
            print(f"Error fetching episodes: {str(e)}")
            return []