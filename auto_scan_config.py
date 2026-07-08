# -*- coding: utf-8 -*-

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path


CONFIG_FILE_NAME = "auto_scan_config.json"
RECORDS_FILE_NAME = "auto_scan_records.jsonl"
COMPRESSED_NAME_MARKER = "已压缩"
SUPPORTED_VIDEO_EXTENSIONS = (".mp4", ".ts", ".mkv", ".mov", ".avi")


def default_config_path():
    return Path(__file__).resolve().parent / CONFIG_FILE_NAME


def default_records_path():
    return Path(__file__).resolve().parent / RECORDS_FILE_NAME


@dataclass
class AutoScanConfig:
    scan_dir: str = ""
    output_dir: str = ""
    pending_delete_dir: str = ""
    daily_scan_time: str = "02:30"
    min_size_mb: int = 500
    stable_wait_minutes: int = 10
    target_size_mb: int = 950
    target_audio_bitrate_kbps: int = 96
    source_action: str = "keep"
    auto_scan_enabled: bool = False
    records_path: str = ""
    supported_extensions: list[str] = field(
        default_factory=lambda: list(SUPPORTED_VIDEO_EXTENSIONS)
    )

    @property
    def min_size_bytes(self):
        return max(0, int(self.min_size_mb)) * 1024 * 1024

    @property
    def stable_wait_seconds(self):
        return max(0, int(self.stable_wait_minutes)) * 60

    @property
    def records_file(self):
        if self.records_path:
            return Path(self.records_path).expanduser()
        return default_records_path()

    @property
    def normalized_extensions(self):
        extensions = []
        for extension in self.supported_extensions:
            extension = str(extension).strip().lower()
            if not extension:
                continue
            if not extension.startswith("."):
                extension = "." + extension
            extensions.append(extension)
        return tuple(dict.fromkeys(extensions))

    def output_dir_for(self, source_path):
        if self.output_dir:
            return Path(self.output_dir).expanduser()
        return Path(source_path).expanduser().parent


def _coerce_config(data):
    defaults = asdict(AutoScanConfig())
    defaults.update({key: value for key, value in data.items() if key in defaults})
    return AutoScanConfig(**defaults)


def load_auto_scan_config(config_path=None):
    config_path = Path(config_path) if config_path else default_config_path()
    if not config_path.exists():
        config = AutoScanConfig()
        save_auto_scan_config(config, config_path)
        return config

    with config_path.open("r", encoding="utf-8") as config_file:
        data = json.load(config_file)
    return _coerce_config(data if isinstance(data, dict) else {})


def save_auto_scan_config(config, config_path=None):
    config_path = Path(config_path) if config_path else default_config_path()
    with config_path.open("w", encoding="utf-8") as config_file:
        json.dump(asdict(config), config_file, ensure_ascii=False, indent=2)
        config_file.write("\n")
