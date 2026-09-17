import sys
sys.dont_write_bytecode = True
import os

# Windows terminals ignore ANSI escape codes unless virtual terminal
# processing is explicitly turned on for the console. Calling os.system("")
# once is a lightweight, well-known trick that enables it as a side effect
# on modern Windows 10+ terminals, without pulling in a third-party
# dependency like colorama.
if os.name == "nt":
    os.system("")

class Colors:
    """ANSI escape codes for colored terminal output."""
    ENABLED = True

    # Text styles
    RESET         = "\033[0m"
    BOLD          = "\033[1m"
    DIM           = "\033[2m"
    ITALIC        = "\033[3m"
    UNDERLINE     = "\033[4m"
    BLINK         = "\033[5m"
    REVERSE       = "\033[7m"
    HIDDEN        = "\033[8m"
    STRIKETHROUGH = "\033[9m"

    # Standard foreground colors. The exact rendered color depends on the
    # terminal's own color scheme/theme, since these codes only select a
    # palette slot rather than a fixed RGB value, so e.g. CYAN can look
    # different (or even greenish) depending on the terminal profile in use.
    BLACK   = "\033[30m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"

    # Bright foreground colors
    BRIGHT_BLACK   = "\033[90m"
    BRIGHT_RED     = "\033[91m"
    BRIGHT_GREEN   = "\033[92m"
    BRIGHT_YELLOW  = "\033[93m"
    BRIGHT_BLUE    = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN    = "\033[96m"
    BRIGHT_WHITE   = "\033[97m"

    # Standard background colors
    BG_BLACK   = "\033[40m"
    BG_RED     = "\033[41m"
    BG_GREEN   = "\033[42m"
    BG_YELLOW  = "\033[43m"
    BG_BLUE    = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN    = "\033[46m"
    BG_WHITE   = "\033[47m"

    # Bright background colors
    BG_BRIGHT_BLACK   = "\033[100m"
    BG_BRIGHT_RED     = "\033[101m"
    BG_BRIGHT_GREEN   = "\033[102m"
    BG_BRIGHT_YELLOW  = "\033[103m"
    BG_BRIGHT_BLUE    = "\033[104m"
    BG_BRIGHT_MAGENTA = "\033[105m"
    BG_BRIGHT_CYAN    = "\033[106m"
    BG_BRIGHT_WHITE   = "\033[107m"

    @staticmethod
    def wrap(text, *codes):
        """Wraps text in the given ANSI codes and resets styling afterwards, unless colored output has been disabled via the 'colored' setting."""
        if not Colors.ENABLED:
            return text
        return f"{''.join(codes)}{text}{Colors.RESET}"