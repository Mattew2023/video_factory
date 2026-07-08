# -*- coding: utf-8 -*-

import runpy
from pathlib import Path


SCRIPT_NAME = "视频压缩工具.py"


def main():
    script_path = Path(__file__).resolve().with_name(SCRIPT_NAME)
    if not script_path.exists():
        raise FileNotFoundError(f"Missing script: {script_path}")
    runpy.run_path(str(script_path), run_name="__main__")


if __name__ == "__main__":
    main()
