import sys
sys.dont_write_bytecode = True
import os
import configparser

CONFIG_FILE = "config.cfg"
SECTION = "Settings"

# Every setting the program expects, with its default value. Used both to
# create a fresh config.cfg and to backfill any setting missing from an
# existing one, e.g. after an update introduced a new setting.
DEFAULT_SETTINGS = {
    "url": "",
    "api_key": "",
    "library_path": "",
    "colored": "True"
}

class Settings:
    @staticmethod
    def load():
        """
        Loads settings from config.cfg, creating the file with default
        values if it doesn't exist yet. Any setting missing from an
        existing file is backfilled with its default value and appended
        to the file. Any setting present in the file that the program no
        longer knows about (e.g. left over from an older version) is
        removed from the file.

        Returns:
            dict: All settings as plain string values, keyed by setting name
        """
        parser = configparser.ConfigParser()
        file_exists = os.path.exists(CONFIG_FILE)

        if file_exists:
            parser.read(CONFIG_FILE)

        if SECTION not in parser:
            parser[SECTION] = {}

        changed = False
        for key, default_value in DEFAULT_SETTINGS.items():
            if key not in parser[SECTION]:
                parser[SECTION][key] = default_value
                changed = True

        for key in list(parser[SECTION].keys()):
            if key not in DEFAULT_SETTINGS:
                del parser[SECTION][key]
                changed = True

        if not file_exists or changed:
            Settings._write(parser)

        return dict(parser[SECTION])

    @staticmethod
    def save(settings):
        """
        Persists the given settings dict to config.cfg, overwriting the
        file with exactly the given values.

        Args:
            settings (dict): Settings to write, keyed the same way as DEFAULT_SETTINGS
        """
        parser = configparser.ConfigParser()
        parser[SECTION] = {key: str(value) for key, value in settings.items()}
        Settings._write(parser)

    @staticmethod
    def is_colored_enabled(settings):
        """Interprets the 'colored' setting as a boolean."""
        return str(settings.get("colored", "True")).strip().lower() in ("true", "1", "yes")

    @staticmethod
    def _write(parser):
        with open(CONFIG_FILE, "w") as f:
            parser.write(f)