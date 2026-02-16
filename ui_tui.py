from __future__ import annotations

import sys
from pathlib import Path


def _bootstrap_src_path() -> None:
    root = Path(__file__).resolve().parent
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def main() -> None:
    _bootstrap_src_path()
    from anicliru_tui.app import main as app_main

    app_main()


if __name__ == "__main__":
    main()
