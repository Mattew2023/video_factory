# -*- coding: utf-8 -*-

from dataclasses import asdict, dataclass
from pathlib import Path

from auto_scan_config import COMPRESSED_NAME_MARKER


ONE_GB_BYTES = 1024 * 1024 * 1024
MIN_TARGET_VIDEO_BITRATE_KBPS = 300
LOW_VIDEO_BITRATE_SKIP_KBPS = 800
DEFAULT_AUDIO_BITRATE_KBPS = 96
LOW_AUDIO_BITRATE_KBPS = 64


@dataclass(frozen=True)
class CompressionDecision:
    decision: str
    reason: str
    target_size_mb: float = 0
    target_total_bitrate_kbps: int = 0
    target_video_bitrate_kbps: int = 0
    audio_bitrate_kbps: int = DEFAULT_AUDIO_BITRATE_KBPS
    video_encoder: str = "libx264"
    output_extension: str = ".mp4"
    preset: str = "medium"

    def to_record_fields(self):
        return asdict(self)

    def to_compression_options(self):
        return {
            "label": "自动扫描智能压缩",
            "target_size_mb": self.target_size_mb,
            "audio_bitrate_kbps": self.audio_bitrate_kbps,
            "target_video_bitrate_kbps": self.target_video_bitrate_kbps,
            "strategy": self.reason,
        }


def _resolution_video_cap(height):
    if height >= 1080:
        return 3000
    if height >= 720:
        return 1800
    return 1200


def _source_video_bitrate(media_info):
    if media_info.video_bitrate_kbps > 0:
        return media_info.video_bitrate_kbps
    estimated_video = media_info.total_bitrate_kbps - media_info.audio_bitrate_kbps
    return max(0, estimated_video)


def _target_size_mb(media_info, config):
    source_mb = media_info.size_bytes / 1024 / 1024
    configured_target_mb = max(100, float(config.target_size_mb))
    if media_info.size_bytes >= ONE_GB_BYTES:
        return min(configured_target_mb, 950)
    return max(100, min(configured_target_mb, source_mb * 0.70))


def decide_compression(media_info, config):
    if media_info.duration_seconds <= 0:
        return CompressionDecision(decision="skip", reason="视频时长无效")

    source_video_kbps = _source_video_bitrate(media_info)
    source_total_kbps = media_info.total_bitrate_kbps
    if max(source_video_kbps, source_total_kbps) < LOW_VIDEO_BITRATE_SKIP_KBPS:
        return CompressionDecision(decision="skip", reason="原始视频码率已经较低")

    target_size_mb = _target_size_mb(media_info, config)
    audio_bitrate_kbps = int(
        min(
            max(LOW_AUDIO_BITRATE_KBPS, config.target_audio_bitrate_kbps),
            media_info.audio_bitrate_kbps or DEFAULT_AUDIO_BITRATE_KBPS,
            DEFAULT_AUDIO_BITRATE_KBPS,
        )
    )
    target_total_kbps = int(target_size_mb * 8192 / media_info.duration_seconds)
    target_video_kbps = target_total_kbps - audio_bitrate_kbps
    target_video_kbps = min(target_video_kbps, _resolution_video_cap(media_info.height))

    if target_video_kbps < MIN_TARGET_VIDEO_BITRATE_KBPS:
        return CompressionDecision(
            decision="skip",
            reason="目标视频码率低于 300k，画质风险过高",
            target_size_mb=target_size_mb,
            target_total_bitrate_kbps=target_total_kbps,
            target_video_bitrate_kbps=max(0, target_video_kbps),
            audio_bitrate_kbps=audio_bitrate_kbps,
        )

    if source_video_kbps and target_video_kbps >= source_video_kbps * 0.90:
        return CompressionDecision(
            decision="skip",
            reason="预计节省空间较少",
            target_size_mb=target_size_mb,
            target_total_bitrate_kbps=target_total_kbps,
            target_video_bitrate_kbps=target_video_kbps,
            audio_bitrate_kbps=audio_bitrate_kbps,
        )

    reason = "H.264 兼容压缩"
    if media_info.size_bytes >= 3 * ONE_GB_BYTES:
        reason = "大文件优先压到 950MB 以下，MVP 保持 H.264 兼容"

    return CompressionDecision(
        decision="compress",
        reason=reason,
        target_size_mb=target_size_mb,
        target_total_bitrate_kbps=target_total_kbps,
        target_video_bitrate_kbps=max(MIN_TARGET_VIDEO_BITRATE_KBPS, int(target_video_kbps)),
        audio_bitrate_kbps=audio_bitrate_kbps,
    )


def build_compressed_output_path(source_path, output_dir, extension=".mp4"):
    source_path = Path(source_path)
    output_dir = Path(output_dir)
    stem = source_path.stem
    if COMPRESSED_NAME_MARKER not in stem:
        stem = f"{stem}_{COMPRESSED_NAME_MARKER}"

    output_path = output_dir / f"{stem}{extension}"
    index = 1
    while output_path.exists():
        output_path = output_dir / f"{stem}_{index}{extension}"
        index += 1
    return output_path
