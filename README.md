# Jellyfin Image Exporter

**If you like my work feel free to support me on:**<br>
[![PayPal](https://img.shields.io/badge/PayPal-8A2BE2?style=for-the-badge&logo=paypal&labelColor=9370DB)](https://paypal.me/kurotaku1337)
[![Ko-fi](https://img.shields.io/badge/Kofi-8A2BE2?style=for-the-badge&logo=ko-fi&labelColor=9370DB)](https://ko-fi.com/kurotaku1337)

A Python script to export images (posters, banners, thumbnails, covers) from your Jellyfin media server's metadata library with both interactive and automation modes.

🧠 **Why this tool?**
Many users have been searching for a way to **easily back up or export metadata images** from their Jellyfin libraries. Unfortunately, Jellyfin does not natively support this, and no plugins exist to automate the process. This tool was created to fill that gap, allowing you to export all artwork without manually browsing every item.

It's especially useful if:
- You want to back up all media images in a structured format
- You're planning to reinstall Jellyfin and want to retain all artwork
- You want to copy images into your media folders for external use
- You need automated exports for backup scripts or media migrations

The script uses Jellyfin's internal metadata structure and mimics the folder layout so that:
- You can export to a separate backup location **or**
- Directly write to the original library folder (e.g. to restore artwork)

✅ The file and folder names are formatted in a way that Jellyfin recognizes them during rescans.

---

## Features

- **Export media images** from Jellyfin to your local file system
- Supports both **interactive menu mode** and **command-line automation**
- Supports **TV Shows, Movies, Music Videos, Home Videos & Photos, Music, and Mixed libraries** (see [Supported Library Types](#supported-library-types))
- Handles:
  - Series posters/banners
  - Season posters
  - Episode thumbnails (optional)
  - Movie/Music Video/Home Video artwork
  - Music album covers, with a choice between `folder` and `cover` as the filename
- **Preserves folder structure** matching your media library, including artist/subfolder nesting for movies, music videos, home videos, and music albums
- **Smart file comparison** only updates changed files
- Supports **multiple library roots** with flexible export paths
- **Optionally wipe a target path's existing content** before exporting, to clear out leftover exports for items that no longer exist in your library
- **Windows long path support** (>260 characters)
- **Command-line interface** with intuitive menus and colored output
- Works against both older Jellyfin versions (10.x) and Jellyfin 12.0+, which switched to a different authentication header by default
- **No third-party dependencies** runs on plain Python out of the box

---

## Supported Library Types

| Jellyfin Library Type | Supported | Notes |
|---|---|---|
| TV Shows | ✅ | Series, season, and optional episode thumbnails |
| Movies | ✅ | Folder structure preserved |
| Music Videos | ✅ | Treated the same as movies |
| Home Videos & Photos | ✅ | Only video items are exported; standalone photos have no companion artwork |
| Music | ✅ | Album-level covers, with a choice of filename convention |
| Mixed Content (no fixed type) | ✅ | Series items are treated as series, movie items are treated as movies, in a single combined export |
| Books | ❌ | Not supported |
| Photos-only | ❌ | Not supported |

---

## ⚠️ Important Note for existing users

This version reworks the file structure and configuration of the programm:
- `connection.json` and `connection_template.json` no longer exist. Connection details now live in `config.cfg`, which is created automatically on first run
- `config.py` no longer exists, its values moved into `src/version.py` and `src/github.py`
- If you're updating from an older version, download the full new release rather than replacing individual files, and re-enter your Jellyfin server URL, API key and metadata path once via the menu

---

## Installation

1. Ensure you have **Python 3.8+** installed
2. Download the programm via releases
3. Run `main.py` to start the application

### ⚠️ Info for Windows users:
The `readline` module is not included by default on Windows.
Install the replacement with:<br>
```bash
pip install pyreadline3
```

---

## Usage

Before exporting to your media folder, it's recommended to run a test export into a separate directory to verify that the structure is correct. Of course, I can't cover every possible case or library structure, so there's no 100% guarantee, but with standard setups, it should work on both Linux and Windows.

### Interactive Mode

1. **Configure connection** to your Jellyfin server via the **"Edit Config"** menu:
   - Server URL
   - API key
   - Path to Jellyfin metadata folder
   - Colored console output (Enabled/Disabled)

2. **Select a library** to export from, grouped by type (see [Supported Library Types](#supported-library-types))

3. **Configure export options**:
   - Export path(s)
   - Include episode thumbnails (for TV Shows and Mixed libraries containing series)
   - For Music libraries: choose whether the album cover is saved as `folder` or `cover`
   - Choose whether to export all images to a single folder, or keep separate folders for each library root
   - If an entered export path already contains files, you are asked whether to wipe its contents first

4. **Review and confirm** the export

### Automation Mode (Command Line)

It is recommended to generate the command using the **"Generate automation command"** option in the menu.
Run exports directly from command line or scripts:

```bash
python main.py --library-id "your-library-id" --export-method "single|separate" --episode-thumbnails "true|false" --target-paths "path1|path2|..." --connection-method "file|parameters" [--music-folder-name "1|2"] [--wipe-existing-exports] [--url "http://your-jellyfin-server"] [--api-key "your_api_key"] [--library-path "/path/to/metadata"]
```

**Parameters:**
- `--library-id`: ID of the Jellyfin library to export (required)
- `--export-method`: `single` (one output location) or `separate` (multiple paths) (required)
- `--episode-thumbnails`: Export episode thumbnails (`true`, `1`, or `yes`) (default: `false`)
- `--target-paths`: Export paths separated by the `|` character (required)
- `--connection-method`: `file` to use `config.cfg`, or `parameters` to manually pass Jellyfin server credentials (default: `file`)
- `--music-folder-name`: Music album cover filename, `1` for `folder` or `2` for `cover` (default: `1`, only relevant for Music libraries)
- `--wipe-existing-exports`: Wipes all existing files in each target path before exporting (flag, no value; default: not set/`false`). Useful to remove leftover exports for items that no longer exist in your library, but cannot be undone
- `--url`: Jellyfin server URL (required if `connection-method=parameters`)
- `--api-key`: Jellyfin API key (required if `connection-method=parameters`)
- `--library-path`: Path to the Jellyfin metadata folder (required if `connection-method=parameters`)

**Example with connection method `file`:**
```bash
python main.py --library-id "12345abcdef" --export-method "single" --episode-thumbnails true --target-paths "/exports/tvshows" --connection-method file
```

**Example with connection method `parameters`:**
```bash
python main.py --library-id "12345abcdef" --export-method "separate" --episode-thumbnails false --target-paths "/mnt/anime|/mnt/cartoons" --connection-method parameters --url "http://localhost:8096" --api-key "123456789" --library-path "/var/lib/jellyfin/metadata"
```

**Example for a Music library:**
```bash
python main.py --library-id "abcdef12345" --export-method "single" --target-paths "/exports/music" --connection-method file --music-folder-name 2
```

**Example wiping existing exports first:**
```bash
python main.py --library-id "12345abcdef" --export-method "single" --target-paths "/exports/tvshows" --connection-method file --wipe-existing-exports
```

---

## Configuration

The script uses a `config.cfg` file, stored next to `main.py`, to store your Jellyfin connection details and a few general settings. You don't need to create it yourself:
- If `config.cfg` doesn't exist yet, it's created automatically with default values the first time you run the programm
- If it already exists but a newer version of the programm added a new setting, the missing setting is automatically added to your existing file with its default value, your existing values stay untouched
- You can edit the connection details (server URL, API key, metadata path) and the colored output toggle directly through the menu ("Edit Config"), or by opening `config.cfg` in a text editor
- When editing a field through the menu that already has a value, the current value is shown before you enter a new one, and entering `0` cancels without changing it
- Test connection before exporting is available from the same menu

`config.cfg` looks like this:
```ini
[Settings]
url = http://your-jellyfin-server:8096
api_key = your-api-key-here
library_path = /path/to/jellyfin/metadata/library
colored = True
```

- `url`, `api_key`, `library_path`: your Jellyfin server connection details
- `colored`: `True` or `False`, toggles colored console output on or off. Can be changed via the "Edit Config" menu (Enabled/Disabled), or by editing this value directly

library_path is the folder containing the Jellyfin metadata.
This is typically a directory filled with many subfolders, each named with exactly two characters, like `ab`, `1f`, `3c`, `a8`, etc.

The machine running this programm must have access to this path, as it will copy metadata files from there.

## Requirements

- Python
- Jellyfin server with API access
- Proper permissions to access:
  - Jellyfin API
  - Metadata folder
  - Export destination folders

---

## Screenshots

![Main Menu](images/main_menu.png)<br>
*Main menu interface*

![Library Menu](images/library_menu.png)<br>
*Library Menu*

![Export Preview](images/export_preview.png)<br>
*Export preview*

![Export Settings](images/export_settings.png)<br>
*Export configuration*

![Operation Summary](images/operation_summary.png)<br>
*Operation Summary*

![Folder](images/folder.png)<br>
*Folder*

---

## Support

- For **bug reports or issues**, contact me directly on **Discord (Kurotaku)**
- Please include detailed information about any problems

---

## Notes

This tool does **not** generate `.nfo` files. To enable NFO generation in Jellyfin:
1. Go to **Library** → **Manage library** → **Metadata Savers**
2. Enable **NFO** option
3. Trigger **Refresh Metadata** with "Search for missing metadata"

This will put all .nfo files in your file system

### Series with nested subfolders

Jellyfin does not support placing series inside subfolders within a TV Shows library; the subfolder itself gets picked up as a fake series with the nested shows treated as its seasons. Because of this, series are always exported flat under their own folder name, without preserving any subfolder structure. This matches how Jellyfin itself handles (or rather, doesn't support) that layout.

### Music cover filename

Jellyfin writes the album cover as `folder.ext` by default when "Save artwork into media folders" is enabled, while many other tools (e.g. beets, Navidrome) expect `cover.ext` instead. This tool lets you choose which filename to use per export, so you can match either convention.

### Wiping existing exports

Enabling the wipe option deletes every file and subfolder directly inside a target export path before that export starts. This is useful when an item (e.g. a series or album) no longer exists in your Jellyfin library but its previously exported images are still sitting in the target folder. In interactive mode, you are only asked about this the moment a non-empty path is entered, and the deletion happens immediately if confirmed. In automation mode, it applies unconditionally to every target path whenever `--wipe-existing-exports` is set. This action cannot be undone.

---

## License

This project is licensed under **CC BY-NC-SA 4.0**.
You may share and adapt the material for non-commercial purposes, with attribution and under the same license.

For details: [Creative Commons License](https://creativecommons.org/licenses/by-nc-sa/4.0/)

---

## Disclaimer

This software is provided as-is without any warranty. The developer is not responsible for any potential issues including but not limited to data loss or system instability. Use at your own risk.