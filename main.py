import sys
sys.dont_write_bytecode = True
import readline
from src.menu_main import MenuMain
from src.auto_runner import AutomationRunner

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            AutomationRunner.run_from_args()
        else:
            MenuMain.show_main_menu()
    except KeyboardInterrupt:
        MenuMain.clear_screen()
        sys.exit(0)