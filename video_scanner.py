# -*- coding: utf-8 -*-

import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from auto_scan_config import COMPRESSED_NAME_MARKER


@dataclass(frozen=True)
class ScanCandidate:
    path: Path
    size_bytes: int
    modified_at: str


@dataclass(frozen=True)
class ScanSkipped:
    path: Path
    reason: str


@dataclass(frozen=True)
class ScanResult:
    candidates: list[ScanCandidate]
    skipped: list[ScanSkipped]


def _safe_resolve(path):
    return Path(path).expanduser().resolve(strict=False)


def _is_under(child_path, parent_path):
    child_path = _safe_resolve(child_path)
    parent_path = _safe_resolve(parent_path)
    try:
        child_path.relative_to(parent_path)
        return True
    except ValueError:
        return False


def _excluded_directories(config, scan_dir):
    directories = []
    scan_dir = _safe_resolve(scan_dir)
    for configured_path in (config.output_dir, config.pending_delete_dir):
        if configured_path:
            resolved_path = _safe_resolve(configured_path)
            if resolved_path != scan_dir:
                directories.append(resolved_path)
    return directories


def _modified_time_text(timestamp):
    return datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")


def scan_recording_directory(config, records=None, now=None):
    scan_dir = Path(config.scan_dir).expanduser()
    if not scan_dir:
        raise ValueError("请先配置扫描目录。")
    if not scan_dir.exists():
        raise FileNotFoundError(f"扫描目录不存在：{scan_dir}")
    if not scan_dir.is_dir():
        raise NotADirectoryError(f"扫描路径不是目录：{scan_dir}")

    now = time.time() if now is None else now
    extensions = set(config.normalized_extensions)
    excluded_dirs = _excluded_directories(config, scan_dir)
    candidates = []
    skipped = []

    for path in scan_dir.rglob("*"):
        if not path.is_file():
            continue

        suffix = path.suffix.lower()
        if suffix not in extensions:
            continue

        try:
            stat_result = path.stat()
        except OSError as exc:
            skipped.append(ScanSkipped(path, f"读取文件状态失败：{exc}"))
            continue

        if COMPRESSED_NAME_MARKER in path.name:
            skipped.append(ScanSkipped(path, "文件名包含“已压缩”"))
            continue

        if any(_is_under(path, excluded_dir) for excluded_dir in excluded_dirs):
            skipped.append(ScanSkipped(path, "位于输出目录或待删除目录"))
            continue

        if stat_result.st_size < config.min_size_bytes:
            skipped.append(ScanSkipped(path, "文件小于最小处理大小"))
            continue

        age_seconds = now - stat_result.st_mtime
        if age_seconds < config.stable_wait_seconds:
            skipped.append(ScanSkipped(path, "最近刚修改，可能仍在写入"))
            continue

        if records and records.has_success_for_file(path, stat_result.st_size):
            skipped.append(ScanSkipped(path, "历史记录显示同路径同大小已成功处理"))
            continue

        candidates.append(
            ScanCandidate(
                path=path,
                size_bytes=stat_result.st_size,
                modified_at=_modified_time_text(stat_result.st_mtime),
            )
        )

    candidates.sort(key=lambda candidate: candidate.size_bytes, reverse=True)
    skipped.sort(key=lambda item: str(item.path).lower())
    return ScanResult(candidates=candidates, skipped=skipped)
