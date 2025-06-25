import sys
sys.dont_write_bytecode = True
import os
import json
import urllib.request
import urllib.error
from config import VERSION, REPO_API_URL, PROJECT_URL

class VersionChecker:
    @staticmethod
    def check_for_updates():
        """
        Check for updates by comparing the local VERSION with the latest GitHub Release tag.

        Flow:
        1. Query the GitHub Releases API for the latest release info
        2. Extract the release tag_name as the remote version
        3. Compare the remote version with the local VERSION
        4. Inform the user about available updates or if the current version is up to date
        5. On update availability, offer to open the GitHub project page for download
        """
        os.system("cls" if os.name == "nt" else "clear")
        print("Checking for updates via GitHub Releases...")

        try:
            # Request the latest release JSON data from GitHub API
            with urllib.request.urlopen(REPO_API_URL, timeout=10) as response:
                if response.status != 200:
                    print(f"\n❌ Server returned status code: {response.status}")
                    raise Exception("Bad response from GitHub API")

                release_data = json.loads(response.read().decode("utf-8"))

                # Extract the tag_name, e.g. 'v1.2.3' and strip leading 'v' if present
                remote_version = release_data.get("tag_name", "").lstrip("v")

                if not remote_version:
                    print("\n❌ Could not find 'tag_name' in the latest release data.")
                    raise Exception("No version info in release data")

                # Compare local and remote versions
                result = VersionChecker._compare_versions(VERSION, remote_version)

                if result == -1:
                    print(f"\n⚠️ Update available!")
                    print(f"New version {remote_version} is available.")
                    print(f"You are using version {VERSION}.")

                    # Prompt user to open project page for downloading the update
                    print("\nDo you want to open the project page to download the update? [y/n]")
                    choice = input("→ ").strip().lower()
                    if choice in ("y", "j"):
                        VersionChecker._open_project_page()

                elif result == 0:
                    print("\n✓ You are using the latest version.")
                    input("\nPress Enter to continue...")
                else:
                    print("\n⚠️ You are using a development version (newer than latest release).")
                    input("\nPress Enter to continue...")

        except (urllib.error.URLError, urllib.error.HTTPError, Exception) as e:
            print(f"\n❌ Failed to check for updates: {str(e)}")

            # Ask if user wants to open the project page manually on error
            print("\nDo you want to open the project page? [y/n]")
            choice = input("→ ").strip().lower()
            if choice in ("y", "j"):
                VersionChecker._open_project_page()

    @staticmethod
    def _compare_versions(version1, version2):
        """
        Compare two semantic version strings numerically.

        Args:
            version1 (str): First version string (e.g. "1.2.3")
            version2 (str): Second version string

        Returns:
            int: -1 if version1 < version2,
                 0 if version1 == version2,
                 1 if version1 > version2
        """
        # Split version strings into integer components
        v1_parts = list(map(int, version1.split(".")))
        v2_parts = list(map(int, version2.split(".")))

        # Pad the shorter version with zeros for equal length comparison
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts += [0] * (max_len - len(v1_parts))
        v2_parts += [0] * (max_len - len(v2_parts))

        # Compare each numeric part
        for v1, v2 in zip(v1_parts, v2_parts):
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
        return 0

    @staticmethod
    def _open_project_page():
        """
        Open the GitHub project page in the default web browser based on OS.
        """
        if os.name == "nt":
            os.system(f"start {PROJECT_URL}")
        elif sys.platform == "darwin":
            os.system(f"open {PROJECT_URL}")
        else:
            os.system(f"xdg-open {PROJECT_URL}")
