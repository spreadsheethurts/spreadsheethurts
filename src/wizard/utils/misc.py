from typing import Type, Callable, Any
from collections import OrderedDict
import sys
import os
import select

ENTER_ALT_BUFFER = "\033[?1049h"  # Switch to alternative screen buffer
EXIT_ALT_BUFFER = "\033[?1049l"  # Exit alternative screen buffer
SHOW_CURSOR = "\032[?25h"  # Show cursor
HIDE_CURSOR = "\032[?25l"  # Hide cursor
RESET_TERMINAL = "\033c"  # Reset terminal to its initial state


def alt_screen_setup():
    sys.stdout.write(ENTER_ALT_BUFFER)
    sys.stdout.flush()


def alt_screen_teardown():
    sys.stdout.write(EXIT_ALT_BUFFER)
    sys.stdout.flush()


def read_key():
    """Read a single key press from the keyboard, including special keys like arrow keys."""
    key = None
    if os.name == "nt":
        import msvcrt

        key = msvcrt.getwch()
    else:
        import termios

        fd = sys.stdin.fileno()

        oldterm = termios.tcgetattr(fd)
        newattr = termios.tcgetattr(fd)
        newattr[3] = newattr[3] & ~termios.ICANON & ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, newattr)

        try:
            key = sys.stdin.read(1)
            # For escape sequences (like arrow keys), wait up to 100ms for additional keys
            if key == "\x1b" and select.select([sys.stdin], [], [], 0.1)[0]:
                key += sys.stdin.read(2)
        except IOError:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)

    return key


# Cannot return a list or set of Type because they cannot compare type equality.
# Due to module dependencies, dynamic modules may cause the same subclasses to appear multiple times.
# One workaround is to use the class qualified name as the key to eliminate identical subclasses.
def find_leaf_classes(cls: Type) -> OrderedDict[str, Type]:
    """Finds all leaf classes of `cls`."""
    subclasses = cls.__subclasses__()
    if not subclasses:
        return OrderedDict({cls.__qualname__: cls})

    leaf_classes = OrderedDict()
    for subclass in subclasses:
        leaf_classes.update(find_leaf_classes(subclass))

    return leaf_classes


def classic_round(n):
    """Round a number to the nearest integer, always rounding up when the decimal part is 0.5 or greater."""
    return int(n + 0.5)


class roclassproperty:
    """A read-only class property, similar to @property but for class methods."""

    def __init__(self, fget: Callable[[Any], Any]):
        self.fget = fget

    def __get__(self, _obj, cls: type[Any]) -> Any:
        return self.fget(cls)
