import sys
sys.dont_write_bytecode = True
import os

# Ensure relative paths (config.cfg, export paths passed relatively, etc.)
# always resolve against the script's own location, regardless of the
# directory the script was invoked from.
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import readline
from src.menu_main import MenuMain
from src.auto_runner import AutomationRunner
from src.settings import Settings
from src.colors import Colors

if __name__ == "__main__":
    # Load settings once at startup and apply the colored output toggle
    # globally before anything else gets printed.
    settings = Settings.load()
    Colors.ENABLED = Settings.is_colored_enabled(settings)

    try:
        if len(sys.argv) > 1:
            AutomationRunner.run_from_args()
        else:
            MenuMain.show_main_menu()
    except KeyboardInterrupt:
        MenuMain.clear_screen()
        sys.exit(0)