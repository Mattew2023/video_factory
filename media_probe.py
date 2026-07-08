# -*- coding: utf-8 -*-

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class MediaInfo:
    source_path: str
    size_bytes: int
    duration_seconds: float
    width: int
    height: int
    frame_rate: float
    total_bitrate_kbps: int
    video_bitrate_kbps: int
    audio_bitrate_kbps: int
    video_codec: str
    audio_codec: str

    def to_record_fields(self):
        return asdict(self)


def _parse_float(value, default=0.0):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _parse_int(value, default=0):
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _parse_frame_rate(value):
    if not value or value == "0/0":
        return 0.0
    if "/" not in value:
        return _parse_float(value)
    numerator, denominator = value.split("/", 1)
    denominator_value = _parse_float(denominator)
    if denominator_value <= 0:
        return 0.0
    return _parse_float(numerator) / denominator_value


def _first_stream(streams, codec_type):
    for stream in streams:
        if stream.get("codec_type") == codec_type:
            return stream
    return {}


def probe_media(source_path, ffprobe_path, creationflags=0, timeout=60):
    source_path = Path(source_path)
    command = [
        str(ffprobe_path),
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(source_path),
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=creationflags,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("未检测到 ffprobe，无法读取视频元信息。") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("ffprobe 读取视频元信息超时。") from exc

    if result.returncode != 0:
        error_message = result.stderr.strip() or "未返回具体错误信息。"
        raise RuntimeError(f"ffprobe 读取视频元信息失败：{error_message}")

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("ffprobe 返回的 JSON 无法解析。") from exc

    streams = payload.get("streams") or []
    format_info = payload.get("format") or {}
    video_stream = _first_stream(streams, "video")
    audio_stream = _first_stream(streams, "audio")

    stat_result = source_path.stat()
    duration_seconds = _parse_float(
        format_info.get("duration") or video_stream.get("duration")
    )
    if duration_seconds <= 0:
        raise RuntimeError("ffprobe 未返回有效视频时长。")

    total_bitrate_kbps = _parse_int(format_info.get("bit_rate")) // 1000
    if total_bitrate_kbps <= 0:
        total_bitrate_kbps = int(stat_result.st_size * 8 / duration_seconds / 1000)

    video_bitrate_kbps = _parse_int(video_stream.get("bit_rate")) // 1000
    audio_bitrate_kbps = _parse_int(audio_stream.get("bit_rate")) // 1000

    return MediaInfo(
        source_path=str(source_path),
        size_bytes=stat_result.st_size,
        duration_seconds=duration_seconds,
        width=_parse_int(video_stream.get("width")),
        height=_parse_int(video_stream.get("height")),
        frame_rate=_parse_frame_rate(
            video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate")
        ),
        total_bitrate_kbps=total_bitrate_kbps,
        video_bitrate_kbps=video_bitrate_kbps,
        audio_bitrate_kbps=audio_bitrate_kbps,
        video_codec=video_stream.get("codec_name") or "",
        audio_codec=audio_stream.get("codec_name") or "",
    )
