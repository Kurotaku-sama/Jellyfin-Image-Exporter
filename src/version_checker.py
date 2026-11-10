import sys
sys.dont_write_bytecode = True
import os
import re
import json
import urllib.request
import urllib.error
from .version import VERSION
from .github import REPO_API_URL, PROJECT_URL
from .colors import Colors

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
        print(Colors.wrap("Checking for updates via GitHub Releases...", Colors.CYAN, Colors.BOLD))

        try:
            # Request the latest release JSON data from GitHub API
            with urllib.request.urlopen(REPO_API_URL, timeout=10) as response:
                if response.status != 200:
                    print(Colors.wrap(f"\n❌ Server returned status code: {response.status}", Colors.RED))
                    raise Exception("Bad response from GitHub API")

                release_data = json.loads(response.read().decode("utf-8"))

                # Extract the tag_name, e.g. 'v1.2.3' or 'V1.2.3', and strip
                # a leading v/V if present regardless of its case
                remote_version = release_data.get("tag_name", "").lstrip("vV")

                if not remote_version:
                    print(Colors.wrap("\n❌ Could not find 'tag_name' in the latest release data.", Colors.RED))
                    raise Exception("No version info in release data")

                # Compare local and remote versions
                result = VersionChecker._compare_versions(VERSION, remote_version)

                if result == -1:
                    print(Colors.wrap("\n⚠️ Update available!", Colors.YELLOW, Colors.BOLD))
                    print(f"New version {remote_version} is available.")
                    print(f"You are using version {VERSION}.")

                    # Prompt user to open project page for downloading the update
                    print("\nDo you want to open the project page to download the update? [y/n]")
                    choice = input("→ ").strip().lower()
                    if choice in ("y", "j"):
                        VersionChecker._open_project_page()
                    else:
                        input("\nPress Enter to continue...")

                elif result == 0:
                    print(Colors.wrap("\n✓ You are using the latest version.", Colors.GREEN))
                    input("\nPress Enter to continue...")
                else:
                    print(Colors.wrap("\n⚠️ You are using a development version (newer than latest release).", Colors.YELLOW))
                    input("\nPress Enter to continue...")

        except Exception as e:
            print(Colors.wrap(f"\n❌ Failed to check for updates: {str(e)}", Colors.RED))

            # Ask if user wants to open the project page manually on error
            print("\nDo you want to open the project page? [y/n]")
            choice = input("→ ").strip().lower()
            if choice in ("y", "j"):
                VersionChecker._open_project_page()
            else:
                input("\nPress Enter to continue...")

    @staticmethod
    def _compare_versions(version1, version2):
        """
        Compare two version strings numerically. Only the leading dotted
        number sequence counts, so any suffix like "-beta" or "rc1" is
        ignored and e.g. "1.2-beta" compares equal to "1.2".

        Args:
            version1 (str): First version string (e.g. "1.2.3")
            version2 (str): Second version string

        Returns:
            int: -1 if version1 < version2,
                 0 if version1 == version2,
                 1 if version1 > version2
        """
        v1_parts = VersionChecker._parse_version(version1)
        v2_parts = VersionChecker._parse_version(version2)

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
    def _parse_version(version):
        """
        Extracts the leading dotted number sequence of a version string as
        a list of integers, e.g. "1.2.3-beta" -> [1, 2, 3]. A string without
        any leading number yields [0].
        """
        match = re.match(r"\s*(\d+(?:\.\d+)*)", version)
        if not match:
            return [0]
        return [int(part) for part in match.group(1).split(".")]

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