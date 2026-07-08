# -*- coding: utf-8 -*-

import shutil
from pathlib import Path


def _require_single_file(path):
    path = Path(path).expanduser()
    if any(character in str(path) for character in ("*", "?")):
        raise ValueError("安全文件操作不允许使用通配符路径。")
    if not path.is_file():
        raise FileNotFoundError(f"不是可处理的单个文件：{path}")
    return path


def move_single_file(source_path, destination_path):
    source_path = _require_single_file(source_path)
    destination_path = Path(destination_path).expanduser()
    if destination_path.exists():
        raise FileExistsError(f"目标文件已存在：{destination_path}")
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    return Path(shutil.move(str(source_path), str(destination_path)))


def delete_single_file(path):
    path = _require_single_file(path)
    path.unlink()
