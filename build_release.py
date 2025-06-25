import sys
sys.dont_write_bytecode = True
import os
import zipfile
from config import VERSION

# List of files and directories to include in the release ZIP
items_to_include = [
    "src",
    "main.py",
    "config.py",
    "connection_template.json",
    "LICENSE",
    "README.md"
]

def add_to_zip(zipf, path, base_folder):
    """
    Recursively add a file or directory to the ZIP archive.

    Args:
        zipf (ZipFile): The open ZipFile object to write to.
        path (str): The file or directory path on disk to add.
        base_folder (str): The base folder name inside the ZIP archive under which
                           all files/folders should be placed.

    Behavior:
        - If 'path' is a directory, walk through all files recursively.
        - For each file, calculate the relative path from the current working directory,
          then prefix it with 'base_folder' to preserve the directory structure inside the ZIP.
        - If 'path' is a single file, add it directly with the base_folder prefix.
    """
    if os.path.isdir(path):
        for root, dirs, files in os.walk(path):
            for file in files:
                full_path = os.path.join(root, file)
                # Calculate the relative path of the file from current working dir
                relative_path = os.path.relpath(full_path, start=os.getcwd())
                # Prepend the base_folder to the relative path for proper structure in ZIP
                arcname = os.path.join(base_folder, relative_path)
                zipf.write(full_path, arcname)
    else:
        # For a single file, just add it under the base_folder with its basename
        arcname = os.path.join(base_folder, os.path.basename(path))
        zipf.write(path, arcname)

def build_release_zip():
    """
    Create the release ZIP file containing specified files and folders.

    The ZIP will be named "Jellyfin Image Exporter VX.X.X.zip" based on the VERSION
    imported from config.py.

    Inside the ZIP, all files and folders will be contained within a top-level
    directory named "Jellyfin Image Exporter VX.X.X" to keep everything organized.
    """
    folder_name = f"Jellyfin Image Exporter V{VERSION}"
    zip_name = folder_name + ".zip"
    print(f"Creating release zip: {zip_name}")

    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for item in items_to_include:
            if os.path.exists(item):
                print(f"Adding {item} ...")
                add_to_zip(zipf, item, folder_name)
            else:
                print(f"Warning: {item} does not exist and will be skipped.")

    print("Done.")

if __name__ == "__main__":
    build_release_zip()
