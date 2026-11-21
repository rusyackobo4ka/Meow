"""Позволяет запускать приложение как ``python3 -m meow --catalog ...``."""
import sys

from meow.main import main

if __name__ == "__main__":
    sys.exit(main())
