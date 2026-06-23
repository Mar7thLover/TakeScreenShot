"""PyInstaller entry point.

Imports macshot as a package so its relative imports resolve, then runs the
CLI/tray main(). Pointing PyInstaller at macshot/__main__.py directly would treat
it as a top-level script with no parent package and break `from . import ...`.
"""

import sys

from macshot.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
