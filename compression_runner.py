# -*- coding: utf-8 -*-

from dataclasses import dataclass
from pathlib import Path

from auto_scan_config import COMPRESSED_NAME_MARKER
from media_probe import probe_media


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    errors: list[str]
    output_info: object = None


def verify_compressed_output(source_info, output_path, ffprobe_path, creationflags=0):
    output_path = Path(output_path)
    errors = []
    output_info = None

    if not output_path.exists():
        errors.append("输出文件不存在")
        return VerificationResult(ok=False, errors=errors, output_info=None)

    output_size = output_path.stat().st_size
    if output_size <= 0:
        errors.append("输出文件大小为 0")

    try:
        output_info = probe_media(output_path, ffprobe_path, creationflags=creationflags)
    except RuntimeError as exc:
        errors.append(str(exc))
        return VerificationResult(ok=False, errors=errors, output_info=None)

    duration_delta = abs(output_info.duration_seconds - source_info.duration_seconds)
    allowed_delta = max(3.0, source_info.duration_seconds * 0.01)
    if duration_delta > allowed_delta:
        errors.append("输出时长与原视频差距过大")

    if output_size >= source_info.size_bytes:
        errors.append("输出文件未小于原文件")

    if COMPRESSED_NAME_MARKER not in output_path.name:
        errors.append("输出文件名不包含“已压缩”")

    return VerificationResult(ok=not errors, errors=errors, output_info=output_info)
