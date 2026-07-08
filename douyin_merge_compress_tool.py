# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import math
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from file_drop_support import create_tk_root, enable_file_drop


MISSING_FFMPEG_MESSAGE = (
    "未检测到 ffmpeg，请把 ffmpeg.exe 和 ffprobe.exe "
    "放到软件目录下的 ffmpeg\\bin 文件夹中，或安装到系统 PATH。"
)
MISSING_FFPROBE_MESSAGE = (
    "未检测到 ffprobe，无法自动计算目标大小。请确认 ffmpeg 安装包中包含 ffprobe。"
)
DEFAULT_DOWNLOAD_DIR = Path.home() / "Downloads" / "Video"
MERGED_SUFFIX = "_合并后"
STITCH_SUFFIX = "_拼接后"
SUPPORTED_EXTENSIONS = {".mp4", ".ts", ".mkv", ".mov"}
VIDEO_FILETYPES = [
    ("支持的视频文件", "*.mp4 *.ts *.mkv *.mov"),
    ("MP4 文件", "*.mp4"),
    ("TS 文件", "*.ts"),
    ("MKV 文件", "*.mkv"),
    ("MOV 文件", "*.mov"),
    ("所有文件", "*.*"),
]
DEFAULT_TARGET_SIZE_MB = 950
ONE_GB_BYTES = 1024 * 1024 * 1024
DEFAULT_VIDEO_BITRATE_KBPS = 900
DEFAULT_AUDIO_BITRATE_KBPS = 96
LOW_AUDIO_BITRATE_KBPS = 64
LOW_VIDEO_BITRATE_THRESHOLD_KBPS = 500
QUALITY_WARNING_VIDEO_BITRATE_KBPS = 300
MIN_TARGET_SIZE_MB = 100
MAX_TARGET_SIZE_MB = 4096
CUSTOM_COMPRESSION_PRESET_LABEL = "自定义"


@dataclass(frozen=True)
class CompressionPreset:
    label: str
    target_size_mb: float
    audio_bitrate_kbps: int


@dataclass(frozen=True)
class CompressionOptions:
    label: str
    target_size_mb: float
    audio_bitrate_kbps: int


COMPRESSION_PRESETS = (
    CompressionPreset("接近 1GB（950 MB）", DEFAULT_TARGET_SIZE_MB, DEFAULT_AUDIO_BITRATE_KBPS),
    CompressionPreset("更小（750 MB）", 750, DEFAULT_AUDIO_BITRATE_KBPS),
    CompressionPreset("极小（500 MB）", 500, LOW_AUDIO_BITRATE_KBPS),
)
COMPRESSION_PRESET_LABELS = tuple(preset.label for preset in COMPRESSION_PRESETS) + (
    CUSTOM_COMPRESSION_PRESET_LABEL,
)
AUDIO_BITRATE_OPTIONS_KBPS = (DEFAULT_AUDIO_BITRATE_KBPS, 80, LOW_AUDIO_BITRATE_KBPS)


@dataclass
class MediaFile:
    path: Path
    has_video: bool = False
    has_audio: bool = False
    error: str = ""

    @property
    def label(self) -> str:
        if self.error:
            return "分析失败"
        if self.has_video and self.has_audio:
            return "包含视频和音频"
        if self.has_video:
            return "视频文件"
        if self.has_audio:
            return "音频文件"
        return "未发现音视频流"


@dataclass(frozen=True)
class VideoDimensions:
    width: int
    height: int

    @property
    def label(self) -> str:
        return f"{self.width}x{self.height}"


def creation_flags() -> int:
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


def program_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def find_command_path(command_names: tuple[str, ...]) -> Path | None:
    for command_name in command_names:
        found_path = shutil.which(command_name)
        if found_path:
            return Path(found_path)
    return None


def find_local_ffmpeg_path() -> tuple[Path | None, str]:
    bundled_candidates = (
        program_dir() / "ffmpeg" / "bin" / "ffmpeg.exe",
        program_dir() / "ffmpeg" / "ffmpeg.exe",
    )
    for candidate in bundled_candidates:
        if candidate.exists():
            return candidate, "自带 ffmpeg"

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        winget_packages = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        for pattern in ("Gyan.FFmpeg_*/*/bin/ffmpeg.exe", "*FFmpeg*/*/bin/ffmpeg.exe"):
            matches = sorted(winget_packages.glob(pattern), reverse=True)
            if matches:
                return matches[0], "WinGet ffmpeg"

    return None, ""


def run_text_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    kwargs = {
        "capture_output": True,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["creationflags"] = creation_flags()
    return subprocess.run(command, **kwargs)


def normalize_group_key(path: Path) -> str:
    stem = path.stem.strip()
    stem = re.sub(rf"{re.escape(MERGED_SUFFIX)}$", "", stem)
    stem = re.sub(r"(?:_\d+|\s*\(\d+\))+$", "", stem).strip()
    return stem or path.stem


def is_existing_output(path: Path) -> bool:
    return path.suffix.lower() == ".mp4" and path.stem.endswith(MERGED_SUFFIX)


def probe_media(path: Path, ffprobe: Path) -> MediaFile:
    result = run_text_command(
        [
            str(ffprobe),
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_streams",
            str(path),
        ]
    )

    if result.returncode != 0:
        message = (result.stderr or result.stdout or "ffprobe 未返回错误信息").strip()
        return MediaFile(path=path, error=message)

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return MediaFile(path=path, error=f"无法解析 ffprobe 输出：{exc}")

    stream_types = {
        stream.get("codec_type") for stream in data.get("streams", []) if stream
    }
    return MediaFile(
        path=path,
        has_video="video" in stream_types,
        has_audio="audio" in stream_types,
    )


def probe_video_dimensions(path: Path, ffprobe: Path) -> tuple[VideoDimensions | None, str]:
    result = run_text_command(
        [
            str(ffprobe),
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(path),
        ]
    )
    if result.returncode != 0:
        message = (result.stderr or result.stdout or "ffprobe 未返回错误信息").strip()
        return None, message

    try:
        data = json.loads(result.stdout)
        stream = next(iter(data.get("streams", [])), {})
        width = int(stream.get("width") or 0)
        height = int(stream.get("height") or 0)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        return None, f"无法解析视频尺寸：{exc}"

    if width <= 0 or height <= 0:
        return None, "无法读取视频画面尺寸。"
    return VideoDimensions(width, height), ""


def quote_ffconcat_path(path: Path) -> str:
    safe_path = str(path.resolve()).replace("\\", "/").replace("'", "\\'")
    return f"'{safe_path}'"


def choose_one_pair(group: list[MediaFile]) -> tuple[MediaFile | None, MediaFile | None, str]:
    video_candidates = [item for item in group if item.has_video and not item.has_audio]
    if not video_candidates:
        video_candidates = [item for item in group if item.has_video]

    audio_candidates = [item for item in group if item.has_audio and not item.has_video]
    if not audio_candidates:
        audio_candidates = [item for item in group if item.has_audio]

    if not video_candidates:
        return None, None, "未找到可配对的视频文件"
    if not audio_candidates:
        return None, None, "未找到可配对的音频文件"

    possible_pairs = [
        (video, audio)
        for video in video_candidates
        for audio in audio_candidates
        if video.path != audio.path
    ]
    if not possible_pairs:
        return None, None, "同一文件不能同时作为视频源和音频源，已跳过"
    if len(possible_pairs) > 1:
        return None, None, "找到多个可能配对，无法安全判断，已跳过"

    return possible_pairs[0][0], possible_pairs[0][1], ""


def parse_ffmpeg_time(value: str) -> float:
    try:
        hours, minutes, seconds = value.split(":")
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except (ValueError, AttributeError):
        return 0.0


def format_seconds(seconds: float | None) -> str:
    if seconds is None:
        return "--:--:--"

    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, second = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{second:02d}"


def format_file_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.2f} {unit}"
        value /= 1024


def short_error_message(message: object, max_length: int = 300) -> str:
    one_line_message = " ".join(str(message).split())
    if len(one_line_message) <= max_length:
        return one_line_message
    return one_line_message[:max_length] + "..."


def format_target_size_mb(target_size_mb: float) -> str:
    if float(target_size_mb).is_integer():
        return str(int(target_size_mb))
    return f"{target_size_mb:.1f}".rstrip("0").rstrip(".")


def target_size_bytes(target_size_mb: float) -> int:
    return int(target_size_mb * 1024 * 1024)


def calculate_target_bitrates(
    duration_seconds: float,
    compression_options: CompressionOptions,
) -> tuple[int, int, str]:
    target_total_bitrate_kbps = compression_options.target_size_mb * 8192 / duration_seconds
    audio_bitrate_kbps = compression_options.audio_bitrate_kbps
    target_video_bitrate_kbps = target_total_bitrate_kbps - audio_bitrate_kbps

    audio_reduced = False
    if target_video_bitrate_kbps < LOW_VIDEO_BITRATE_THRESHOLD_KBPS:
        lowered_audio_bitrate_kbps = min(audio_bitrate_kbps, LOW_AUDIO_BITRATE_KBPS)
        audio_reduced = lowered_audio_bitrate_kbps < audio_bitrate_kbps
        audio_bitrate_kbps = lowered_audio_bitrate_kbps
        target_video_bitrate_kbps = target_total_bitrate_kbps - audio_bitrate_kbps

    video_bitrate_kbps = min(
        DEFAULT_VIDEO_BITRATE_KBPS,
        max(1, int(target_video_bitrate_kbps)),
    )
    if video_bitrate_kbps == DEFAULT_VIDEO_BITRATE_KBPS:
        strategy = "常规压小优先"
    elif audio_reduced:
        strategy = "目标大小兜底（音频降到 64k）"
    else:
        strategy = "目标大小兜底"

    return video_bitrate_kbps, audio_bitrate_kbps, strategy


class UnifiedVideoToolApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("抖音合并与视频压缩工具")
        self.root.geometry("880x620")
        self.root.minsize(760, 540)

        self.log_queue: queue.Queue[object] = queue.Queue()
        self.is_running = False
        self.controls: list[tk.Widget] = []

        self.ffmpeg_path: Path | None = None
        self.ffprobe_path: Path | None = None
        self.ffmpeg_source = ""
        self.current_process: subprocess.Popen[str] | None = None
        self.cancel_requested = False
        self.compress_started_at = 0.0
        self.batch_total_count = 0
        self.batch_completed_count = 0
        self.batch_current_index = 0
        self.merge_dir = DEFAULT_DOWNLOAD_DIR
        self.input_files: list[Path] = []
        self.output_dir: Path | None = None
        self.stitch_files: list[Path] = []
        self.stitch_output_dir: Path | None = None
        self.completed_output_files: list[Path] = []
        self.video_drop_widgets: list[tk.Widget] = []
        self.stitch_drop_widgets: list[tk.Widget] = []
        self.cancel_buttons: list[tk.Widget] = []

        self.ffmpeg_text = tk.StringVar(value="正在检测 ffmpeg...")
        self.merge_dir_text = tk.StringVar(value=str(self.merge_dir))
        self.input_file_text = tk.StringVar(value="未选择")
        self.output_dir_text = tk.StringVar(value="未选择")
        self.stitch_file_text = tk.StringVar(value="未选择")
        self.stitch_output_dir_text = tk.StringVar(value="未选择")
        self.compress_preset_text = tk.StringVar(value=COMPRESSION_PRESETS[0].label)
        self.custom_target_size_text = tk.StringVar(
            value=format_target_size_mb(COMPRESSION_PRESETS[0].target_size_mb)
        )
        self.audio_bitrate_text = tk.StringVar(
            value=f"{COMPRESSION_PRESETS[0].audio_bitrate_kbps}k"
        )
        self.overwrite_merge = tk.BooleanVar(value=False)
        self.overall_progress = tk.DoubleVar(value=0.0)
        self.overall_progress_text = tk.StringVar(value="整体进度：第 0 / 0 个，整体百分比 0%")
        self.compress_progress = tk.DoubleVar(value=0.0)
        self.compress_percent_text = tk.StringVar(value="0%")
        self.current_video_progress_text = tk.StringVar(value="当前视频进度：0%")
        self.compress_status_text = tk.StringVar(value="准备中")
        self.compress_elapsed_text = tk.StringVar(value="已用时间：00:00:00")
        self.compress_remaining_text = tk.StringVar(value="预计剩余：--:--:--")
        self.compress_position_text = tk.StringVar(value="进度：00:00:00 / 00:00:00")

        self.build_ui()
        self.refresh_tools()
        self.root.after(300, self.enable_video_file_drop)
        self.root.after(100, self.process_log_queue)

    def build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.root.rowconfigure(2, weight=1)

        top_frame = ttk.Frame(self.root, padding=(12, 12, 12, 6))
        top_frame.grid(row=0, column=0, sticky="ew")
        top_frame.columnconfigure(1, weight=1)

        ttk.Label(top_frame, text="ffmpeg").grid(row=0, column=0, sticky="w")
        ttk.Label(top_frame, textvariable=self.ffmpeg_text).grid(
            row=0, column=1, sticky="ew", padx=(8, 8)
        )
        refresh_button = ttk.Button(top_frame, text="重新检测", command=self.refresh_tools)
        refresh_button.grid(row=0, column=2, sticky="e")
        self.controls.append(refresh_button)

        notebook = ttk.Notebook(self.root)
        notebook.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))

        merge_tab = ttk.Frame(notebook, padding=12)
        stitch_tab = ttk.Frame(notebook, padding=12)
        compress_tab = ttk.Frame(notebook, padding=12)
        notebook.add(merge_tab, text="抖音音视频合并")
        notebook.add(stitch_tab, text="两段视频拼接")
        notebook.add(compress_tab, text="视频压缩")

        self.build_merge_tab(merge_tab)
        self.build_stitch_tab(stitch_tab)
        self.build_compress_tab(compress_tab)
        self.build_log_panel()

    def build_merge_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)

        ttk.Label(parent, text="扫描目录").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(parent, textvariable=self.merge_dir_text, state="readonly").grid(
            row=0, column=1, sticky="ew", padx=(8, 8), pady=(0, 8)
        )
        choose_button = ttk.Button(parent, text="选择目录", command=self.select_merge_dir)
        choose_button.grid(row=0, column=2, sticky="e", pady=(0, 8))
        self.controls.append(choose_button)

        overwrite_check = ttk.Checkbutton(
            parent,
            text="覆盖已存在的合并结果",
            variable=self.overwrite_merge,
        )
        overwrite_check.grid(row=1, column=1, sticky="w", padx=(8, 8), pady=(0, 12))
        self.controls.append(overwrite_check)

        start_button = ttk.Button(parent, text="开始合并", command=self.start_merge)
        start_button.grid(row=2, column=1, sticky="w", padx=(8, 8))
        self.controls.append(start_button)

    def build_stitch_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)

        ttk.Label(parent, text="两段视频").grid(row=0, column=0, sticky="w", pady=(0, 8))
        file_entry = ttk.Entry(parent, textvariable=self.stitch_file_text, state="readonly")
        file_entry.grid(row=0, column=1, sticky="ew", padx=(8, 8), pady=(0, 8))
        file_button = ttk.Button(
            parent,
            text="选择两段视频",
            command=self.select_stitch_files,
        )
        file_button.grid(row=0, column=2, sticky="e", pady=(0, 8))
        self.controls.append(file_button)
        self.stitch_drop_widgets.extend([parent, file_entry, file_button])

        ttk.Label(parent, text="输出目录").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(parent, textvariable=self.stitch_output_dir_text, state="readonly").grid(
            row=1, column=1, sticky="ew", padx=(8, 8), pady=(0, 8)
        )
        dir_button = ttk.Button(
            parent,
            text="选择目录",
            command=self.select_stitch_output_dir,
        )
        dir_button.grid(row=1, column=2, sticky="e", pady=(0, 8))
        self.controls.append(dir_button)

        open_dir_button = ttk.Button(
            parent,
            text="打开输出目录",
            command=self.open_stitch_output_dir,
        )
        open_dir_button.grid(row=1, column=3, sticky="e", pady=(0, 8), padx=(8, 0))
        self.controls.append(open_dir_button)

        start_button = ttk.Button(parent, text="开始拼接", command=self.start_stitch)
        start_button.grid(row=2, column=1, sticky="w", padx=(8, 8), pady=(4, 0))
        self.controls.append(start_button)

        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(14, 0))
        progress_frame.columnconfigure(0, weight=1)

        ttk.Label(progress_frame, textvariable=self.compress_status_text).grid(
            row=0, column=0, sticky="w", pady=(0, 4)
        )
        progress_line = ttk.Frame(progress_frame)
        progress_line.grid(row=1, column=0, sticky="ew")
        progress_line.columnconfigure(0, weight=1)

        ttk.Progressbar(
            progress_line,
            maximum=100,
            variable=self.compress_progress,
            mode="determinate",
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(
            progress_line,
            textvariable=self.compress_percent_text,
            width=7,
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=(8, 0))
        ttk.Label(progress_frame, textvariable=self.compress_elapsed_text).grid(
            row=2, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Label(progress_frame, textvariable=self.compress_position_text).grid(
            row=3, column=0, sticky="w", pady=(4, 0)
        )

        cancel_button = ttk.Button(
            progress_frame,
            text="取消拼接",
            command=self.cancel_compress,
            state=tk.DISABLED,
        )
        cancel_button.grid(row=4, column=0, sticky="w", pady=(8, 0))
        self.cancel_buttons.append(cancel_button)

    def build_compress_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)

        ttk.Label(parent, text="视频文件").grid(row=0, column=0, sticky="w", pady=(0, 8))
        file_entry = ttk.Entry(parent, textvariable=self.input_file_text, state="readonly")
        file_entry.grid(
            row=0, column=1, sticky="ew", padx=(8, 8), pady=(0, 8)
        )
        file_button = ttk.Button(parent, text="选择视频文件", command=self.select_video_file)
        file_button.grid(row=0, column=2, sticky="e", pady=(0, 8))
        self.controls.append(file_button)

        multi_file_button = ttk.Button(
            parent,
            text="选择多个视频文件",
            command=self.select_video_files,
        )
        multi_file_button.grid(row=0, column=3, sticky="e", pady=(0, 8), padx=(8, 0))
        self.controls.append(multi_file_button)
        self.video_drop_widgets.extend([parent, file_entry, file_button, multi_file_button])

        ttk.Label(parent, text="输出目录").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(parent, textvariable=self.output_dir_text, state="readonly").grid(
            row=1, column=1, sticky="ew", padx=(8, 8), pady=(0, 8)
        )
        dir_button = ttk.Button(parent, text="选择目录", command=self.select_output_dir)
        dir_button.grid(row=1, column=2, sticky="e", pady=(0, 8))
        self.controls.append(dir_button)

        open_dir_button = ttk.Button(
            parent,
            text="打开输出目录",
            command=self.open_selected_output_dir,
        )
        open_dir_button.grid(row=1, column=3, sticky="e", pady=(0, 8), padx=(8, 0))
        self.controls.append(open_dir_button)

        options_frame = ttk.LabelFrame(parent, text="压缩选项", padding=(8, 6))
        options_frame.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        options_frame.columnconfigure(1, weight=1)

        ttk.Label(options_frame, text="目标大小").grid(
            row=0, column=0, sticky="w", pady=(0, 6)
        )
        preset_combo = ttk.Combobox(
            options_frame,
            textvariable=self.compress_preset_text,
            values=COMPRESSION_PRESET_LABELS,
            state="readonly",
            width=20,
        )
        preset_combo.grid(row=0, column=1, sticky="w", padx=(8, 16), pady=(0, 6))
        preset_combo.bind("<<ComboboxSelected>>", self.on_compress_preset_changed)
        self.controls.append(preset_combo)

        ttk.Label(options_frame, text="自定义 MB").grid(
            row=0, column=2, sticky="w", pady=(0, 6)
        )
        target_size_entry = ttk.Entry(
            options_frame,
            textvariable=self.custom_target_size_text,
            width=10,
        )
        target_size_entry.grid(row=0, column=3, sticky="w", padx=(8, 0), pady=(0, 6))
        target_size_entry.bind("<KeyRelease>", self.on_custom_target_size_changed)
        self.controls.append(target_size_entry)

        ttk.Label(options_frame, text="音频保留").grid(row=1, column=0, sticky="w")
        audio_combo = ttk.Combobox(
            options_frame,
            textvariable=self.audio_bitrate_text,
            values=tuple(f"{kbps}k" for kbps in AUDIO_BITRATE_OPTIONS_KBPS),
            state="readonly",
            width=10,
        )
        audio_combo.grid(row=1, column=1, sticky="w", padx=(8, 16))
        self.controls.append(audio_combo)

        start_button = ttk.Button(parent, text="开始压缩", command=self.start_compress)
        start_button.grid(row=3, column=1, sticky="w", padx=(8, 8), pady=(4, 0))
        self.controls.append(start_button)

        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(14, 0))
        progress_frame.columnconfigure(0, weight=1)

        ttk.Label(progress_frame, textvariable=self.overall_progress_text).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 4),
        )
        ttk.Progressbar(
            progress_frame,
            maximum=100,
            variable=self.overall_progress,
            mode="determinate",
        ).grid(row=1, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(progress_frame, textvariable=self.current_video_progress_text).grid(
            row=2,
            column=0,
            sticky="w",
            pady=(0, 4),
        )
        progress_line = ttk.Frame(progress_frame)
        progress_line.grid(row=3, column=0, sticky="ew")
        progress_line.columnconfigure(0, weight=1)

        ttk.Progressbar(
            progress_line,
            maximum=100,
            variable=self.compress_progress,
            mode="determinate",
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(
            progress_line,
            textvariable=self.compress_percent_text,
            width=7,
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=(8, 0))

        ttk.Label(progress_frame, textvariable=self.compress_status_text).grid(
            row=4, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Label(progress_frame, textvariable=self.compress_elapsed_text).grid(
            row=5, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(progress_frame, textvariable=self.compress_remaining_text).grid(
            row=6, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(progress_frame, textvariable=self.compress_position_text).grid(
            row=7, column=0, sticky="w", pady=(4, 0)
        )

        self.cancel_compress_button = ttk.Button(
            progress_frame,
            text="取消压缩",
            command=self.cancel_compress,
            state=tk.DISABLED,
        )
        self.cancel_compress_button.grid(row=8, column=0, sticky="w", pady=(8, 0))
        self.cancel_buttons.append(self.cancel_compress_button)

    def build_log_panel(self) -> None:
        log_frame = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        log_frame.grid(row=2, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(1, weight=1)

        header = ttk.Frame(log_frame)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="日志").grid(row=0, column=0, sticky="w")
        clear_button = ttk.Button(header, text="清空", command=self.clear_log)
        clear_button.grid(row=0, column=1, sticky="e")
        self.controls.append(clear_button)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            height=14,
            font=("Microsoft YaHei UI", 10),
        )
        self.log_text.grid(row=1, column=0, sticky="nsew")

    def enable_video_file_drop(self) -> None:
        enabled = False
        if enable_file_drop(
            self.root,
            self.video_drop_widgets,
            self.accept_dropped_video_files,
            log=self.write_log,
        ):
            enabled = True
        if enable_file_drop(
            self.root,
            self.stitch_drop_widgets,
            self.accept_dropped_stitch_files,
            log=self.write_log,
        ):
            enabled = True

        if enabled:
            self.write_log("可将一个或多个视频文件拖入窗口自动录入。")
        else:
            self.write_log("当前环境未启用拖拽；仍可使用“选择视频文件/选择多个视频文件”。")

    def accept_dropped_video_files(self, dropped_paths: list[Path]) -> None:
        if self.is_running:
            messagebox.showinfo("正在执行", "当前已有任务在执行，请完成后再拖入视频。")
            return
        self.accept_video_files(dropped_paths, source="拖入")

    def accept_dropped_stitch_files(self, dropped_paths: list[Path]) -> None:
        if self.is_running:
            messagebox.showinfo("正在执行", "当前已有任务在执行，请完成后再拖入视频。")
            return
        self.accept_stitch_files(dropped_paths, source="拖入")

    def find_compression_preset(self, label: str) -> CompressionPreset | None:
        for preset in COMPRESSION_PRESETS:
            if preset.label == label:
                return preset
        return None

    def on_compress_preset_changed(self, _event: object | None = None) -> None:
        preset = self.find_compression_preset(self.compress_preset_text.get())
        if not preset:
            return

        self.custom_target_size_text.set(format_target_size_mb(preset.target_size_mb))
        self.audio_bitrate_text.set(f"{preset.audio_bitrate_kbps}k")

    def on_custom_target_size_changed(self, _event: object | None = None) -> None:
        if self.compress_preset_text.get() != CUSTOM_COMPRESSION_PRESET_LABEL:
            self.compress_preset_text.set(CUSTOM_COMPRESSION_PRESET_LABEL)

    def get_compression_options(self) -> CompressionOptions | None:
        preset_label = self.compress_preset_text.get()
        preset = self.find_compression_preset(preset_label)
        if preset:
            target_size_mb = preset.target_size_mb
            label = preset.label
        else:
            label = CUSTOM_COMPRESSION_PRESET_LABEL
            target_size_text = self.custom_target_size_text.get().strip()
            try:
                target_size_mb = float(target_size_text)
            except ValueError:
                messagebox.showwarning("目标大小无效", "请输入有效的目标大小 MB。")
                return None

        if (
            not math.isfinite(target_size_mb)
            or target_size_mb < MIN_TARGET_SIZE_MB
            or target_size_mb > MAX_TARGET_SIZE_MB
        ):
            messagebox.showwarning(
                "目标大小超出范围",
                f"目标大小请输入 {MIN_TARGET_SIZE_MB} 到 {MAX_TARGET_SIZE_MB} MB。",
            )
            return None

        audio_bitrate_text = self.audio_bitrate_text.get().strip().lower().rstrip("k")
        try:
            audio_bitrate_kbps = int(audio_bitrate_text)
        except ValueError:
            messagebox.showwarning("音频码率无效", "请选择有效的音频码率。")
            return None

        if audio_bitrate_kbps not in AUDIO_BITRATE_OPTIONS_KBPS:
            messagebox.showwarning("音频码率无效", "请选择有效的音频码率。")
            return None

        return CompressionOptions(
            label=label,
            target_size_mb=target_size_mb,
            audio_bitrate_kbps=audio_bitrate_kbps,
        )

    def refresh_tools(self) -> None:
        self.ffmpeg_path, self.ffprobe_path, self.ffmpeg_source = self.find_ffmpeg_tools()

        if self.ffmpeg_path and self.ffprobe_path:
            self.ffmpeg_text.set(f"当前使用：{self.ffmpeg_source} | {self.ffmpeg_path}")
            self.write_log(f"已检测到 ffmpeg：{self.ffmpeg_path}")
            self.write_log(f"已检测到 ffprobe：{self.ffprobe_path}")
        elif self.ffmpeg_path:
            self.ffmpeg_text.set("未检测到 ffprobe")
            self.write_log(MISSING_FFPROBE_MESSAGE)
            messagebox.showerror("未检测到 ffprobe", MISSING_FFPROBE_MESSAGE)
        else:
            self.ffmpeg_text.set("未检测到 ffmpeg")
            self.write_log(MISSING_FFMPEG_MESSAGE)
            messagebox.showerror("未检测到 ffmpeg", MISSING_FFMPEG_MESSAGE)

    def find_ffmpeg_tools(self) -> tuple[Path | None, Path | None, str]:
        ffmpeg_path, ffmpeg_source = find_local_ffmpeg_path()
        if not ffmpeg_path:
            ffmpeg_path = find_command_path(("ffmpeg.exe", "ffmpeg"))
            ffmpeg_source = "系统 PATH" if ffmpeg_path else ""

        if not ffmpeg_path:
            return None, None, ""

        same_dir_ffprobe = ffmpeg_path.parent / "ffprobe.exe"
        if same_dir_ffprobe.exists():
            return ffmpeg_path, same_dir_ffprobe, ffmpeg_source

        path_ffprobe = find_command_path(("ffprobe.exe", "ffprobe"))
        if path_ffprobe:
            return ffmpeg_path, path_ffprobe, f"{ffmpeg_source} + PATH ffprobe"

        return ffmpeg_path, None, ffmpeg_source

    def ensure_ffmpeg_tools_available(self) -> bool:
        if self.ffmpeg_path and self.ffprobe_path:
            return True
        self.refresh_tools()
        if self.ffmpeg_path and self.ffprobe_path:
            return True
        return False

    def select_merge_dir(self) -> None:
        dir_path = filedialog.askdirectory(
            title="选择抖音下载目录",
            initialdir=str(self.merge_dir) if self.merge_dir.exists() else str(Path.home()),
        )
        if not dir_path:
            return
        self.merge_dir = Path(dir_path)
        self.merge_dir_text.set(str(self.merge_dir))
        self.write_log(f"已选择扫描目录：{self.merge_dir}")

    def select_video_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=VIDEO_FILETYPES,
        )
        if not file_path:
            return

        self.accept_video_files([Path(file_path)], source="选择")

    def select_video_files(self) -> None:
        file_paths = filedialog.askopenfilenames(
            title="选择多个视频文件",
            filetypes=VIDEO_FILETYPES,
        )
        if not file_paths:
            return

        self.accept_video_files([Path(file_path) for file_path in file_paths], source="选择")

    def accept_video_files(self, selected_files: list[Path], source: str) -> bool:
        unique_files: list[Path] = []
        seen: set[Path] = set()
        for input_file in selected_files:
            normalized_file = input_file.expanduser()
            if normalized_file in seen:
                continue
            seen.add(normalized_file)
            unique_files.append(normalized_file)

        supported_files = [
            input_file
            for input_file in unique_files
            if input_file.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        unsupported_files = [
            input_file
            for input_file in unique_files
            if input_file.suffix.lower() not in SUPPORTED_EXTENSIONS
        ]

        if unsupported_files:
            unsupported_names = "\n".join(
                input_file.name for input_file in unsupported_files[:10]
            )
            if len(unsupported_files) > 10:
                unsupported_names += f"\n……以及另外 {len(unsupported_files) - 10} 个文件"
            messagebox.showwarning(
                "格式不支持",
                "以下文件已忽略：\n"
                f"{unsupported_names}\n\n"
                "暂时只支持 .mp4 / .ts / .mkv / .mov 文件。",
            )

        if not supported_files:
            return False

        self.input_files = supported_files
        if len(supported_files) == 1:
            self.input_file_text.set(str(supported_files[0]))
        else:
            self.input_file_text.set(f"已{source} {len(supported_files)} 个视频")

        self.write_log("")
        self.write_log(f"已{source} {len(self.input_files)} 个视频。")
        for index, input_file in enumerate(self.input_files, start=1):
            self.write_log(f"{index}. {input_file}")
        return True

    def select_stitch_files(self) -> None:
        file_paths = filedialog.askopenfilenames(
            title="选择两段视频文件",
            filetypes=VIDEO_FILETYPES,
        )
        if not file_paths:
            return

        self.accept_stitch_files([Path(file_path) for file_path in file_paths], source="选择")

    def accept_stitch_files(self, selected_files: list[Path], source: str) -> bool:
        unique_files: list[Path] = []
        seen: set[Path] = set()
        for input_file in selected_files:
            normalized_file = input_file.expanduser()
            if normalized_file in seen:
                continue
            seen.add(normalized_file)
            unique_files.append(normalized_file)

        supported_files = [
            input_file
            for input_file in unique_files
            if input_file.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        unsupported_files = [
            input_file
            for input_file in unique_files
            if input_file.suffix.lower() not in SUPPORTED_EXTENSIONS
        ]

        if unsupported_files:
            unsupported_names = "\n".join(
                input_file.name for input_file in unsupported_files[:10]
            )
            if len(unsupported_files) > 10:
                unsupported_names += f"\n……以及另外 {len(unsupported_files) - 10} 个文件"
            messagebox.showwarning(
                "格式不支持",
                "以下文件已忽略：\n"
                f"{unsupported_names}\n\n"
                "暂时只支持 .mp4 / .ts / .mkv / .mov 文件。",
            )

        if len(supported_files) != 2:
            messagebox.showwarning(
                "数量不正确",
                f"请一次选择 2 个视频文件。当前识别到 {len(supported_files)} 个。",
            )
            return False

        self.stitch_files = supported_files
        self.stitch_file_text.set("已选择 2 个视频")

        self.write_log("")
        self.write_log(f"已{source} 2 个待拼接视频。")
        for index, input_file in enumerate(self.stitch_files, start=1):
            self.write_log(f"{index}. {input_file}")
        return True

    def select_output_dir(self) -> None:
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if not dir_path:
            return

        self.output_dir = Path(dir_path)
        self.output_dir_text.set(str(self.output_dir))
        self.completed_output_files = []
        self.write_log(f"已选择输出目录：{self.output_dir}")

    def select_stitch_output_dir(self) -> None:
        dir_path = filedialog.askdirectory(title="选择拼接输出目录")
        if not dir_path:
            return

        self.stitch_output_dir = Path(dir_path)
        self.stitch_output_dir_text.set(str(self.stitch_output_dir))
        self.completed_output_files = []
        self.write_log(f"已选择拼接输出目录：{self.stitch_output_dir}")

    def open_selected_output_dir(self) -> None:
        if not self.output_dir:
            messagebox.showwarning("缺少输出目录", "请先点击“选择目录”。")
            return

        last_output_file = self.get_last_completed_output_file()
        if last_output_file:
            self.open_output_folder(last_output_file)
            return

        self.open_directory(self.output_dir)

    def open_stitch_output_dir(self) -> None:
        if not self.stitch_output_dir:
            messagebox.showwarning("缺少输出目录", "请先点击“选择目录”。")
            return

        last_output_file = self.get_last_completed_output_file()
        if last_output_file:
            self.open_output_folder(last_output_file)
            return

        self.open_directory(self.stitch_output_dir)

    def start_merge(self) -> None:
        if not self.ensure_idle():
            return
        if not self.ensure_ffmpeg_tools_available():
            return
        if not self.merge_dir.exists():
            messagebox.showerror("目录不存在", "选择的扫描目录不存在，请重新选择。")
            return

        self.start_worker(
            self.run_merge_folder,
            self.merge_dir,
            self.ffmpeg_path,
            self.ffprobe_path,
            self.overwrite_merge.get(),
        )

    def run_merge_folder(
        self,
        download_dir: Path,
        ffmpeg: Path,
        ffprobe: Path,
        overwrite: bool,
    ) -> None:
        self.log("")
        self.log(f"扫描目录：{download_dir}")

        mp4_files = sorted(
            path
            for path in download_dir.glob("*.mp4")
            if path.is_file() and not is_existing_output(path)
        )
        if not mp4_files:
            self.log(f"目录里没有找到待处理的 MP4 文件：{download_dir}")
            return

        self.log(f"发现 MP4 文件：{len(mp4_files)} 个")
        groups: dict[str, list[MediaFile]] = {}

        for path in mp4_files:
            media = probe_media(path, ffprobe)
            groups.setdefault(normalize_group_key(path), []).append(media)
            self.log(f"已分析：{path.name} -> {media.label}")
            if media.error:
                self.log(f"  {media.error}")

        merged_count = 0
        skipped_count = 0

        for group_key in sorted(groups):
            group = groups[group_key]
            if len(group) < 2:
                skipped_count += 1
                self.log("")
                self.log(f"跳过：{group[0].path.name}")
                self.log(self.reason_for_single_file(group[0]))
                continue

            video, audio, reason = choose_one_pair(group)
            if not video or not audio:
                skipped_count += 1
                self.log("")
                self.log(f"跳过文件组：{group_key}")
                self.log(reason)
                for item in group:
                    self.log(f"  - {item.path.name} -> {item.label}")
                continue

            output = download_dir / f"{group_key}{MERGED_SUFFIX}.mp4"
            self.log("")
            self.log(f"正在处理文件组：{group_key}")
            self.log(f"视频源：{video.path.name}")
            self.log(f"音频源：{audio.path.name}")

            if output.exists() and not overwrite:
                skipped_count += 1
                self.log(f"输出文件已存在，已跳过：{output}")
                continue

            if self.merge_pair(video, audio, output, ffmpeg, overwrite):
                merged_count += 1
            else:
                skipped_count += 1

        self.log("")
        self.log("合并处理完成")
        self.log(f"成功合并：{merged_count} 组")
        self.log(f"跳过/失败：{skipped_count} 组")

    def reason_for_single_file(self, media: MediaFile) -> str:
        if media.has_video and not media.has_audio:
            return "未找到可配对的音频文件"
        if media.has_audio and not media.has_video:
            return "未找到可配对的视频文件"
        return "未找到可配对的另一个文件"

    def merge_pair(
        self,
        video: MediaFile,
        audio: MediaFile,
        output: Path,
        ffmpeg: Path,
        overwrite: bool,
    ) -> bool:
        result = run_text_command(
            [
                str(ffmpeg),
                "-hide_banner",
                "-loglevel",
                "error",
                "-y" if overwrite else "-n",
                "-i",
                str(video.path),
                "-i",
                str(audio.path),
                "-c",
                "copy",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                str(output),
            ]
        )
        if result.returncode == 0:
            self.log(f"合并成功：{output}")
            return True

        message = (result.stderr or result.stdout or "ffmpeg 未返回错误信息").strip()
        self.log("合并失败")
        self.log(message)
        return False

    def start_stitch(self) -> None:
        if not self.ensure_idle():
            return
        if not self.ensure_ffmpeg_tools_available():
            return
        if len(self.stitch_files) != 2:
            messagebox.showwarning("缺少视频文件", "请先选择 2 个要拼接的视频文件。")
            return
        if not self.stitch_output_dir:
            messagebox.showwarning("缺少输出目录", "请先点击“选择目录”。")
            return
        if any(not input_file.exists() for input_file in self.stitch_files):
            messagebox.showerror("文件不存在", "选择的视频文件不存在，请重新选择。")
            return
        if not self.stitch_output_dir.exists():
            messagebox.showerror("目录不存在", "选择的输出目录不存在，请重新选择。")
            return

        input_files = list(self.stitch_files)
        output_file = self.build_unique_stitch_output_path(
            input_files[0],
            self.stitch_output_dir,
        )
        self.completed_output_files = []
        self.reset_compress_progress("准备拼接", 1)
        self.cancel_requested = False
        self.start_worker(
            self.run_stitch_videos,
            input_files,
            output_file,
            self.ffmpeg_path,
            self.ffprobe_path,
        )
        self.set_cancel_buttons_state(tk.NORMAL)

    def build_unique_stitch_output_path(self, first_file: Path, output_dir: Path) -> Path:
        output_file = output_dir / f"{first_file.stem}{STITCH_SUFFIX}.mp4"
        index = 1
        while output_file.exists():
            output_file = output_dir / f"{first_file.stem}{STITCH_SUFFIX}_{index}.mp4"
            index += 1
        return output_file

    def run_stitch_videos(
        self,
        input_files: list[Path],
        output_file: Path,
        ffmpeg: Path,
        ffprobe: Path,
    ) -> None:
        self.log("")
        self.log("开始拼接两段视频...")
        for index, input_file in enumerate(input_files, start=1):
            self.log(f"第 {index} 段：{input_file}")
        self.log(f"输出文件：{output_file}")

        dimensions: list[VideoDimensions] = []
        for input_file in input_files:
            dimension, error = probe_video_dimensions(input_file, ffprobe)
            if dimension is None:
                message = f"无法读取视频尺寸，已停止拼接：{input_file.name}\n{error}"
                self.log(message)
                self.post_compress_progress(status="拼接失败")
                self.post_compress_result("拼接失败", message, is_error=True)
                return
            dimensions.append(dimension)
            self.log(f"{input_file.name} 画面尺寸：{dimension.label}")

        if dimensions[0] != dimensions[1]:
            message = (
                "两段视频画面尺寸不一致，无法在不改变原视频大小的情况下无损拼接。\n\n"
                f"第 1 段：{dimensions[0].label}\n"
                f"第 2 段：{dimensions[1].label}\n\n"
                "请先把两段视频处理成相同尺寸后再拼接。"
            )
            self.log(message)
            self.post_compress_progress(status="拼接失败")
            self.post_compress_result("拼接失败", message, is_error=True)
            return

        durations = [self.probe_video_duration(input_file, ffprobe) for input_file in input_files]
        total_duration = sum(duration for duration in durations if duration > 0)
        original_total_size = sum(input_file.stat().st_size for input_file in input_files)
        self.log(f"拼接后画面尺寸保持：{dimensions[0].label}")
        self.log(f"两段原文件总大小：{format_file_size(original_total_size)}")
        if total_duration > 0:
            self.log(f"两段总时长：{format_seconds(total_duration)}")

        concat_list_path = self.create_concat_list_file(input_files)
        self.compress_started_at = time.monotonic()
        self.post_compress_progress(
            status="正在拼接",
            percent=0,
            elapsed=0,
            current=0,
            total=total_duration if total_duration > 0 else None,
        )

        command = [
            str(ffmpeg),
            "-hide_banner",
            "-nostats",
            "-progress",
            "pipe:1",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output_file),
        ]

        self.log("ffmpeg 已启动，正在无重新编码拼接...")
        error_lines: list[str] = []
        return_code = -1

        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=creation_flags(),
            )
            self.current_process = process

            stderr_thread = threading.Thread(
                target=self.collect_stderr,
                args=(process, error_lines),
                daemon=True,
            )
            stderr_thread.start()

            try:
                assert process.stdout is not None
                for raw_line in process.stdout:
                    line = raw_line.strip()
                    if not line or "=" not in line:
                        continue

                    key, value = line.split("=", 1)
                    if total_duration > 0 and key in {"out_time_ms", "out_time_us"}:
                        current_seconds = self.parse_progress_microseconds(value)
                        self.update_compress_progress_from_time(current_seconds, total_duration)
                    elif total_duration > 0 and key == "out_time":
                        current_seconds = parse_ffmpeg_time(value)
                        self.update_compress_progress_from_time(current_seconds, total_duration)
                    elif key == "progress" and value == "end":
                        self.post_compress_progress(
                            status="正在拼接",
                            percent=100,
                            current=total_duration if total_duration > 0 else None,
                            total=total_duration if total_duration > 0 else None,
                        )

                return_code = process.wait()
            finally:
                self.current_process = None
                stderr_thread.join(timeout=1)
        finally:
            try:
                concat_list_path.unlink()
            except FileNotFoundError:
                pass
            except OSError as exc:
                self.log(f"临时拼接清单删除失败：{exc}")

        if self.cancel_requested:
            self.log("用户取消拼接。")
            self.post_compress_progress(status="用户取消")
            return

        if return_code == 0:
            output_size = output_file.stat().st_size if output_file.exists() else 0
            elapsed = time.monotonic() - self.compress_started_at
            self.completed_output_files = [output_file]
            summary = self.build_stitch_success_summary(
                output_file,
                dimensions[0],
                original_total_size,
                output_size,
                elapsed,
            )
            self.log("拼接完成")
            self.log(summary)
            self.post_compress_progress(
                status="拼接完成",
                percent=100,
                current=total_duration if total_duration > 0 else None,
                total=total_duration if total_duration > 0 else None,
                remaining=0,
            )
            self.post_compress_result("拼接完成", summary, output_path=output_file)
            self.post_open_output_dir(output_file.parent, output_file)
            return

        error_text = self.build_error_summary(return_code, error_lines)
        message = (
            "拼接失败。两段视频需要有兼容的编码、帧率、音轨等参数，才能在不重新编码的情况下保持大小不变。\n\n"
            f"{error_text}"
        )
        self.log(message)
        self.post_compress_progress(status="拼接失败")
        self.post_compress_result("拼接失败", message, is_error=True)

    def create_concat_list_file(self, input_files: list[Path]) -> Path:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".ffconcat",
            delete=False,
        ) as concat_file:
            concat_file.write("ffconcat version 1.0\n")
            for input_file in input_files:
                concat_file.write(f"file {quote_ffconcat_path(input_file)}\n")
            return Path(concat_file.name)

    def build_stitch_success_summary(
        self,
        output_file: Path,
        dimensions: VideoDimensions,
        original_total_size: int,
        output_size: int,
        elapsed: float,
    ) -> str:
        delta = output_size - original_total_size
        if original_total_size > 0:
            delta_percent = delta / original_total_size * 100
        else:
            delta_percent = 0.0
        if delta == 0:
            delta_text = "0 B (0.0%)"
        else:
            sign = "+" if delta > 0 else "-"
            delta_text = f"{sign}{format_file_size(abs(delta))} ({delta_percent:+.1f}%)"

        return "\n".join(
            [
                f"输出文件：{output_file}",
                "拼接方式：无重新编码",
                f"画面尺寸：{dimensions.label}",
                f"两段原文件总大小：{format_file_size(original_total_size)}",
                f"拼接后文件大小：{format_file_size(output_size)}",
                f"大小差异：{delta_text}",
                f"总耗时：{format_seconds(elapsed)}",
            ]
        )

    def start_compress(self) -> None:
        if not self.ensure_idle():
            return
        if not self.ensure_ffmpeg_tools_available():
            return
        if not self.input_files:
            messagebox.showwarning(
                "缺少视频文件",
                "请先点击“选择视频文件”或“选择多个视频文件”。",
            )
            return
        if not self.output_dir:
            messagebox.showwarning("缺少输出目录", "请先点击“选择目录”。")
            return
        if len(self.input_files) == 1 and not self.input_files[0].exists():
            messagebox.showerror("文件不存在", "选择的视频文件不存在，请重新选择。")
            return
        if not self.output_dir.exists():
            messagebox.showerror("目录不存在", "选择的输出目录不存在，请重新选择。")
            return

        compression_options = self.get_compression_options()
        if not compression_options:
            return

        input_files = list(self.input_files)
        self.completed_output_files = []
        self.reset_compress_progress("准备中", len(input_files))
        self.cancel_requested = False
        self.start_worker(
            self.run_batch_compress,
            input_files,
            self.output_dir,
            self.ffmpeg_path,
            self.ffprobe_path,
            compression_options,
        )
        self.set_cancel_buttons_state(tk.NORMAL)

    def build_unique_output_path(self, input_file: Path, output_dir: Path) -> Path:
        output_file = output_dir / f"{input_file.stem}_压缩后.mp4"
        index = 1
        while output_file.exists():
            output_file = output_dir / f"{input_file.stem}_压缩后_{index}.mp4"
            index += 1
        return output_file

    def run_batch_compress(
        self,
        input_files: list[Path],
        output_dir: Path,
        ffmpeg: Path,
        ffprobe: Path,
        compression_options: CompressionOptions,
    ) -> None:
        total_count = len(input_files)
        success_count = 0
        completed_output_files: list[Path] = []
        failed_items: list[tuple[Path, str]] = []

        self.log("")
        self.log("开始压缩...")
        self.log(f"共选择 {total_count} 个视频。")
        self.log(f"输出目录：{output_dir}")
        self.log(f"压缩档位：{compression_options.label}")
        self.log(f"目标大小：{format_target_size_mb(compression_options.target_size_mb)} MB")
        self.log(f"音频保留码率：{compression_options.audio_bitrate_kbps}k")
        self.post_overall_progress(0, total_count, 0, 0)

        for index, input_file in enumerate(input_files, start=1):
            if self.cancel_requested:
                self.log("用户取消压缩，已停止后续队列。")
                self.post_compress_progress(status="用户取消")
                break

            output_file = self.build_unique_output_path(input_file, output_dir)
            completed_count = index - 1
            self.batch_total_count = total_count
            self.batch_completed_count = completed_count
            self.batch_current_index = index
            self.log("")
            self.log(f"当前正在压缩第 {index} / {total_count} 个")
            self.log(f"当前输入文件名：{input_file.name}")
            self.log(f"当前输入文件路径：{input_file}")
            self.log(f"当前输出文件路径：{output_file}")
            self.post_overall_progress(completed_count, total_count, 0, index)
            self.post_compress_progress(
                status=f"第 {index}/{total_count} 个：准备中",
                percent=0,
                elapsed=0,
                remaining=None,
                current=0,
                total=None,
            )

            try:
                result = self.run_compress(
                    input_file,
                    output_file,
                    ffmpeg,
                    ffprobe,
                    compression_options,
                    show_result=False,
                )
            except Exception as exc:
                result = {"success": False, "error": f"发生异常：{exc}"}
                self.log(result["error"])

            if result.get("cancelled"):
                self.log("用户取消压缩，已停止后续队列。")
                break

            if result.get("success"):
                success_count += 1
                result_output_file = result.get("output_file")
                if result_output_file:
                    completed_output_files.append(Path(result_output_file))
                compressed_size = int(result.get("compressed_size", 0))
                under_target = "是" if compressed_size <= target_size_bytes(
                    compression_options.target_size_mb
                ) else "否"
                under_one_gb = "是" if compressed_size < ONE_GB_BYTES else "否"
                self.post_overall_progress(completed_count, total_count, 1.0, index)
                self.log(f"当前视频压缩完成后的大小：{format_file_size(compressed_size)}")
                self.log(f"是否小于目标大小：{under_target}")
                self.log(f"是否小于 1GB：{under_one_gb}")
            else:
                error_message = str(result.get("error") or "未知错误")
                failed_items.append((input_file, error_message))
                self.post_overall_progress(completed_count, total_count, 1.0, index)
                self.log(f"本视频压缩失败：{short_error_message(error_message)}")

        self.log("")
        self.log("批量压缩完成。")
        self.log(f"最后汇总：成功 {success_count} 个，失败 {len(failed_items)} 个。")
        if completed_output_files:
            self.completed_output_files = completed_output_files
            self.log("完成文件：")
            for output_file in completed_output_files:
                self.log(f"- {output_file}")
        if failed_items:
            self.log("失败列表：")
            for input_file, error_message in failed_items:
                self.log(f"- {input_file.name}：{short_error_message(error_message)}")

        summary_lines = [
            f"共选择 {total_count} 个视频。",
            f"成功 {success_count} 个，失败 {len(failed_items)} 个。",
            f"输出目录：{output_dir}",
            f"压缩档位：{compression_options.label}",
            f"目标大小：{format_target_size_mb(compression_options.target_size_mb)} MB",
            f"音频保留码率：{compression_options.audio_bitrate_kbps}k",
        ]
        if completed_output_files:
            summary_lines.append("")
            summary_lines.append("完成文件：")
            for output_file in completed_output_files[:10]:
                summary_lines.append(f"- {output_file}")
            if len(completed_output_files) > 10:
                summary_lines.append(f"……以及另外 {len(completed_output_files) - 10} 个文件")
        if failed_items:
            summary_lines.append("")
            summary_lines.append("失败列表：")
            for input_file, error_message in failed_items:
                summary_lines.append(
                    f"- {input_file.name}：{short_error_message(error_message)}"
                )

        self.post_compress_progress(
            status="批量压缩完成",
            percent=100,
            remaining=0,
        )
        self.post_overall_progress(total_count, total_count, 0, total_count)
        self.post_compress_result("批量压缩完成", "\n".join(summary_lines))
        self.post_open_output_dir(
            output_dir,
            completed_output_files[-1] if completed_output_files else None,
        )

    def run_compress(
        self,
        input_file: Path,
        output_file: Path,
        ffmpeg: Path,
        ffprobe: Path,
        compression_options: CompressionOptions,
        show_result: bool = True,
    ) -> dict[str, object]:
        self.log("")
        self.log("准备压缩")
        self.log(f"输入文件：{input_file}")
        self.log(f"输出文件：{output_file}")

        if not input_file.exists():
            message = "视频文件不存在，请重新选择。"
            self.log(message)
            self.post_compress_progress(status="压缩失败")
            if show_result:
                self.post_compress_result("压缩失败", message, is_error=True)
            return {"success": False, "error": message}

        if input_file.suffix.lower() not in SUPPORTED_EXTENSIONS:
            message = "格式不支持，暂时只支持 .mp4 / .ts / .mkv / .mov 文件。"
            self.log(message)
            self.post_compress_progress(status="压缩失败")
            if show_result:
                self.post_compress_result("压缩失败", message, is_error=True)
            return {"success": False, "error": message}

        original_size = input_file.stat().st_size
        self.compress_started_at = time.monotonic()
        self.post_compress_progress(status="正在分析视频时长")

        duration = self.probe_video_duration(input_file, ffprobe)
        if duration <= 0:
            message = "无法获取视频总时长，已停止压缩。"
            self.log(message)
            self.post_compress_progress(status="压缩失败")
            if show_result:
                self.post_compress_result("压缩失败", message, is_error=True)
            return {"success": False, "error": message}
        if self.cancel_requested:
            self.log("用户取消压缩。")
            self.post_compress_progress(status="用户取消")
            return {"success": False, "cancelled": True, "error": "用户取消压缩。"}

        video_bitrate_kbps, audio_bitrate_kbps, strategy = calculate_target_bitrates(
            duration,
            compression_options,
        )
        bufsize_kbps = video_bitrate_kbps * 2

        self.log(f"视频总时长：{format_seconds(duration)}")
        self.log(f"压缩档位：{compression_options.label}")
        self.log(f"目标大小：{format_target_size_mb(compression_options.target_size_mb)} MB")
        self.log(f"原文件大小：{format_file_size(original_size)}")
        self.log(f"压缩策略：{strategy}")
        self.log(f"自动计算的视频码率：{video_bitrate_kbps}k")
        self.log(f"音频码率：{audio_bitrate_kbps}k")
        if video_bitrate_kbps < QUALITY_WARNING_VIDEO_BITRATE_KBPS:
            self.log("视频时长过长，压到目标大小会明显损失画质。")
        self.post_compress_progress(
            status="正在压缩",
            percent=0,
            elapsed=0,
            current=0,
            total=duration,
        )

        command = [
            str(ffmpeg),
            "-hide_banner",
            "-nostats",
            "-progress",
            "pipe:1",
            "-i",
            str(input_file),
            "-c:v",
            "libx264",
            "-b:v",
            f"{video_bitrate_kbps}k",
            "-maxrate",
            f"{video_bitrate_kbps}k",
            "-bufsize",
            f"{bufsize_kbps}k",
            "-c:a",
            "aac",
            "-b:a",
            f"{audio_bitrate_kbps}k",
            str(output_file),
        ]

        self.log("ffmpeg 已启动，正在读取实时进度...")
        error_lines: list[str] = []

        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creation_flags(),
        )
        self.current_process = process

        stderr_thread = threading.Thread(
            target=self.collect_stderr,
            args=(process, error_lines),
            daemon=True,
        )
        stderr_thread.start()

        try:
            assert process.stdout is not None
            for raw_line in process.stdout:
                line = raw_line.strip()
                if not line or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                if key in {"out_time_ms", "out_time_us"}:
                    current_seconds = self.parse_progress_microseconds(value)
                    self.update_compress_progress_from_time(current_seconds, duration)
                elif key == "out_time":
                    current_seconds = parse_ffmpeg_time(value)
                    self.update_compress_progress_from_time(current_seconds, duration)
                elif key == "progress" and value == "end":
                    self.post_compress_progress(
                        status="正在压缩",
                        percent=100,
                        current=duration,
                        total=duration,
                    )
                    if self.batch_total_count > 0:
                        self.post_overall_progress(
                            self.batch_completed_count,
                            self.batch_total_count,
                            1.0,
                            self.batch_current_index,
                        )

            return_code = process.wait()
        finally:
            self.current_process = None
            stderr_thread.join(timeout=1)

        if self.cancel_requested:
            self.log("用户取消压缩。")
            self.post_compress_progress(status="用户取消")
            return {"success": False, "cancelled": True, "error": "用户取消压缩。"}

        if return_code == 0:
            compressed_size = output_file.stat().st_size if output_file.exists() else 0
            elapsed = time.monotonic() - self.compress_started_at
            summary = self.build_success_summary(
                output_file,
                original_size,
                compressed_size,
                elapsed,
                compression_options,
                video_bitrate_kbps,
                audio_bitrate_kbps,
                strategy,
            )
            self.log("压缩完成")
            self.log(summary)
            self.post_compress_progress(
                status="已完成",
                percent=100,
                current=duration,
                total=duration,
                remaining=0,
            )
            if show_result:
                self.post_compress_result("压缩完成", summary, output_path=output_file)
            return {
                "success": True,
                "output_file": output_file,
                "compressed_size": compressed_size,
                "summary": summary,
            }

        error_text = self.build_error_summary(return_code, error_lines)
        self.log("压缩失败")
        self.log(error_text)
        self.post_compress_progress(status="压缩失败")
        if show_result:
            self.post_compress_result("压缩失败", error_text, is_error=True)
        return {"success": False, "error": error_text}

    def probe_video_duration(self, input_file: Path, ffprobe: Path) -> float:
        result = run_text_command(
            [
                str(ffprobe),
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(input_file),
            ]
        )
        if result.returncode != 0:
            self.log((result.stderr or result.stdout or "ffprobe 未返回错误信息").strip())
            return 0.0

        try:
            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration", 0) or 0)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self.log(f"无法解析视频时长：{exc}")
            return 0.0

    def collect_stderr(
        self,
        process: subprocess.Popen[str],
        error_lines: list[str],
    ) -> None:
        if process.stderr is None:
            return

        for raw_line in process.stderr:
            line = raw_line.strip()
            if not line:
                continue
            error_lines.append(line)
            if len(error_lines) > 80:
                del error_lines[:20]

    def parse_progress_microseconds(self, value: str) -> float:
        try:
            return max(0.0, int(value) / 1_000_000)
        except ValueError:
            return 0.0

    def update_compress_progress_from_time(self, current: float, total: float) -> None:
        current = min(max(current, 0.0), total)
        percent = min(100.0, (current / total) * 100) if total > 0 else 0.0
        elapsed = time.monotonic() - self.compress_started_at
        remaining = None
        if percent > 0:
            remaining = max(0.0, elapsed * (100.0 - percent) / percent)

        self.post_compress_progress(
            status=f"正在压缩：{percent:.0f}%",
            percent=percent,
            elapsed=elapsed,
            remaining=remaining,
            current=current,
            total=total,
        )
        if self.batch_total_count > 0:
            self.post_overall_progress(
                self.batch_completed_count,
                self.batch_total_count,
                percent / 100,
                self.batch_current_index,
            )

    def reset_compress_progress(self, status: str, total_count: int = 0) -> None:
        self.batch_total_count = total_count
        self.batch_completed_count = 0
        self.batch_current_index = 0
        self.overall_progress.set(0)
        self.overall_progress_text.set(
            f"整体进度：第 0 / {total_count} 个，整体百分比 0%"
        )
        self.compress_progress.set(0)
        self.compress_percent_text.set("0%")
        self.current_video_progress_text.set("当前视频进度：0%")
        self.compress_status_text.set(status)
        self.compress_elapsed_text.set("已用时间：00:00:00")
        self.compress_remaining_text.set("预计剩余：--:--:--")
        self.compress_position_text.set("进度：00:00:00 / 00:00:00")

    def post_overall_progress(
        self,
        completed_count: int,
        total_count: int,
        current_file_progress: float,
        current_index: int,
    ) -> None:
        if total_count <= 0:
            overall_progress = 0.0
        else:
            overall_progress = (completed_count + current_file_progress) / total_count

        self.log_queue.put(
            {
                "type": "overall_progress",
                "completed_count": completed_count,
                "total_count": total_count,
                "current_file_progress": current_file_progress,
                "current_index": current_index,
                "overall_progress": overall_progress,
            }
        )

    def post_compress_progress(
        self,
        status: str | None = None,
        percent: float | None = None,
        elapsed: float | None = None,
        remaining: float | None = None,
        current: float | None = None,
        total: float | None = None,
    ) -> None:
        self.log_queue.put(
            {
                "type": "compress_progress",
                "status": status,
                "percent": percent,
                "elapsed": elapsed,
                "remaining": remaining,
                "current": current,
                "total": total,
            }
        )

    def apply_compress_progress(self, event: dict) -> None:
        status = event.get("status")
        percent = event.get("percent")
        elapsed = event.get("elapsed")
        remaining = event.get("remaining")
        current = event.get("current")
        total = event.get("total")

        if status:
            self.compress_status_text.set(status)
        if percent is not None:
            percent = min(max(float(percent), 0.0), 100.0)
            self.compress_progress.set(percent)
            self.compress_percent_text.set(f"{percent:.0f}%")
            self.current_video_progress_text.set(f"当前视频进度：{percent:.0f}%")
        if elapsed is not None:
            self.compress_elapsed_text.set(f"已用时间：{format_seconds(elapsed)}")
        if remaining is not None:
            self.compress_remaining_text.set(f"预计剩余：{format_seconds(remaining)}")
        elif percent == 0:
            self.compress_remaining_text.set("预计剩余：--:--:--")
        if current is not None and total is not None:
            self.compress_position_text.set(
                f"进度：{format_seconds(current)} / {format_seconds(total)}"
            )

    def apply_overall_progress(self, event: dict) -> None:
        total_count = int(event.get("total_count") or 0)
        completed_count = int(event.get("completed_count") or 0)
        current_index = int(event.get("current_index") or 0)
        current_file_progress = float(event.get("current_file_progress") or 0)
        overall_progress = float(event.get("overall_progress") or 0)

        if total_count > 0 and completed_count >= total_count:
            current_index = total_count
            overall_progress = 1.0

        current_file_progress = min(max(current_file_progress, 0.0), 1.0)
        overall_progress = min(max(overall_progress, 0.0), 1.0)
        overall_percent = overall_progress * 100

        if total_count > 0 and current_index == 0 and completed_count == 0:
            display_index = 0
        else:
            display_index = min(max(current_index, 0), total_count)

        self.overall_progress.set(overall_percent)
        self.overall_progress_text.set(
            f"整体进度：第 {display_index} / {total_count} 个，整体百分比 {overall_percent:.0f}%"
        )

    def post_compress_result(
        self,
        title: str,
        message: str,
        is_error: bool = False,
        output_path: Path | None = None,
    ) -> None:
        self.log_queue.put(
            {
                "type": "compress_result",
                "title": title,
                "message": message,
                "is_error": is_error,
                "output_path": str(output_path) if output_path else None,
            }
        )

    def post_open_output_dir(
        self,
        output_dir: Path,
        selected_path: Path | None = None,
    ) -> None:
        self.log_queue.put(
            {
                "type": "open_output_dir",
                "output_dir": str(output_dir),
                "selected_path": str(selected_path) if selected_path else None,
            }
        )

    def show_compress_result(self, event: dict) -> None:
        if event.get("is_error"):
            messagebox.showerror(event["title"], event["message"])
        elif event.get("output_path"):
            self.show_compress_success_dialog(
                event["title"],
                event["message"],
                Path(event["output_path"]),
            )
        else:
            messagebox.showinfo(event["title"], event["message"])

    def show_compress_success_dialog(
        self,
        title: str,
        message: str,
        output_path: Path,
    ) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.resizable(False, False)

        container = ttk.Frame(dialog, padding=16)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)

        ttk.Label(
            container,
            text=message,
            justify=tk.LEFT,
            anchor="w",
            wraplength=680,
        ).grid(row=0, column=0, sticky="ew")

        button_frame = ttk.Frame(container)
        button_frame.grid(row=1, column=0, sticky="e", pady=(16, 0))

        ttk.Button(
            button_frame,
            text="打开输出文件夹",
            command=lambda: self.open_output_folder(output_path),
        ).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(
            button_frame,
            text="打开视频文件",
            command=lambda: self.open_video_file(output_path),
        ).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(
            button_frame,
            text="关闭",
            command=dialog.destroy,
        ).grid(row=0, column=2)

        dialog.update_idletasks()
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_w = self.root.winfo_width()
        parent_h = self.root.winfo_height()
        dialog_w = dialog.winfo_width()
        dialog_h = dialog.winfo_height()
        x = parent_x + max(0, (parent_w - dialog_w) // 2)
        y = parent_y + max(0, (parent_h - dialog_h) // 2)
        dialog.geometry(f"+{x}+{y}")
        dialog.grab_set()
        dialog.focus_set()

    def get_last_completed_output_file(self) -> Path | None:
        for output_file in reversed(self.completed_output_files):
            if output_file.exists():
                return output_file
        return None

    def open_directory(self, output_dir: Path, show_error: bool = True) -> None:
        try:
            if not output_dir.exists():
                raise FileNotFoundError(output_dir)
            if os.name == "nt":
                os.startfile(str(output_dir))
            else:
                subprocess.Popen(["xdg-open", str(output_dir)])
        except Exception as exc:
            message = f"打开输出目录失败：{output_dir}\n{exc}"
            self.log(message)
            if show_error:
                messagebox.showerror("打开输出目录失败", message)

    def open_output_folder(self, output_path: Path, show_error: bool = True) -> None:
        try:
            if not output_path.exists():
                raise FileNotFoundError(output_path)
            selected_path = output_path.resolve(strict=True)
            if os.name == "nt":
                self.select_file_in_windows_explorer(selected_path)
            else:
                subprocess.Popen(["xdg-open", str(selected_path.parent)])
        except Exception as exc:
            if show_error:
                self.show_open_error("打开输出文件夹失败", output_path, exc)
            else:
                self.log(f"打开输出文件夹失败：{output_path}\n{exc}")

    def select_file_in_windows_explorer(self, selected_path: Path) -> None:
        import ctypes

        params = f'/select,"{selected_path}"'
        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "open",
            "explorer.exe",
            params,
            str(selected_path.parent),
            1,
        )
        if result <= 32:
            self.log(f"Explorer 选中文件失败，改为打开目录：{selected_path.parent}")
            os.startfile(str(selected_path.parent))

    def open_video_file(self, output_path: Path) -> None:
        try:
            if not output_path.exists():
                raise FileNotFoundError(output_path)
            if os.name == "nt":
                os.startfile(str(output_path))
            else:
                subprocess.Popen(["xdg-open", str(output_path)])
        except Exception as exc:
            self.show_open_error("打开视频文件失败", output_path, exc)

    def show_open_error(self, title: str, path: Path, exc: Exception) -> None:
        message = f"{title}：{path}\n{exc}"
        self.log(message)
        messagebox.showerror(title, message)

    def cancel_compress(self) -> None:
        process = self.current_process
        if not process or process.poll() is not None:
            if self.is_running:
                self.cancel_requested = True
                self.set_cancel_buttons_state(tk.DISABLED)
                self.compress_status_text.set("用户取消")
                self.log("收到取消请求，任务将在 ffmpeg 启动前停止。")
            return

        self.cancel_requested = True
        self.set_cancel_buttons_state(tk.DISABLED)
        self.compress_status_text.set("用户取消")
        self.log("收到取消请求，正在终止 ffmpeg...")

        try:
            process.terminate()
        except Exception as exc:
            self.log(f"终止 ffmpeg 失败：{exc}")
            return

        threading.Thread(
            target=self.force_stop_process,
            args=(process,),
            daemon=True,
        ).start()

    def force_stop_process(self, process: subprocess.Popen[str]) -> None:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
                self.log("ffmpeg 未及时退出，已强制结束。")
            except Exception as exc:
                self.log(f"强制结束 ffmpeg 失败：{exc}")

    def build_success_summary(
        self,
        output_file: Path,
        original_size: int,
        compressed_size: int,
        elapsed: float,
        compression_options: CompressionOptions,
        video_bitrate_kbps: int,
        audio_bitrate_kbps: int,
        strategy: str,
    ) -> str:
        ratio = 0.0
        if original_size > 0:
            ratio = (1 - compressed_size / original_size) * 100
        under_target = "是" if compressed_size <= target_size_bytes(
            compression_options.target_size_mb
        ) else "否"
        under_one_gb = "是" if compressed_size < ONE_GB_BYTES else "否"

        return "\n".join(
            [
                f"输出文件：{output_file}",
                f"压缩档位：{compression_options.label}",
                f"目标大小：{format_target_size_mb(compression_options.target_size_mb)} MB",
                f"原文件大小：{format_file_size(original_size)}",
                f"压缩后文件大小：{format_file_size(compressed_size)}",
                f"是否小于目标大小：{under_target}",
                f"是否小于 1GB：{under_one_gb}",
                f"压缩策略：{strategy}",
                f"视频码率：{video_bitrate_kbps}k",
                f"音频码率：{audio_bitrate_kbps}k",
                f"压缩率：{ratio:.1f}%",
                f"总耗时：{format_seconds(elapsed)}",
            ]
        )

    def build_error_summary(self, return_code: int, error_lines: list[str]) -> str:
        key_log = "\n".join(error_lines[-12:]).strip()
        if not key_log:
            key_log = "ffmpeg 未返回具体错误信息。"
        return f"失败原因：ffmpeg 退出代码 {return_code}\n\n关键错误日志：\n{key_log}"

    def ensure_idle(self) -> bool:
        if self.is_running:
            messagebox.showinfo("正在执行", "当前已有任务在执行，请稍等。")
            return False
        return True

    def start_worker(self, target, *args) -> None:
        self.is_running = True
        self.set_controls_state(tk.DISABLED)
        worker = threading.Thread(target=self.worker_wrapper, args=(target, args), daemon=True)
        worker.start()

    def worker_wrapper(self, target, args) -> None:
        try:
            target(*args)
        except FileNotFoundError as exc:
            self.log(f"找不到外部程序或文件：{exc}")
            target_name = getattr(target, "__name__", "")
            if target_name in {"run_compress", "run_batch_compress", "run_stitch_videos"}:
                title = "拼接失败" if target_name == "run_stitch_videos" else "压缩失败"
                self.post_compress_progress(status=title)
                self.post_compress_result(title, f"找不到外部程序或文件：{exc}", is_error=True)
        except Exception as exc:
            self.log(f"发生异常：{exc}")
            target_name = getattr(target, "__name__", "")
            if target_name in {"run_compress", "run_batch_compress", "run_stitch_videos"}:
                title = "拼接失败" if target_name == "run_stitch_videos" else "压缩失败"
                self.post_compress_progress(status=title)
                self.post_compress_result(title, f"发生异常：{exc}", is_error=True)
        finally:
            self.log_queue.put("__TASK_FINISHED__")

    def process_log_queue(self) -> None:
        try:
            while True:
                message = self.log_queue.get_nowait()
                if isinstance(message, dict):
                    message_type = message.get("type")
                    if message_type == "compress_progress":
                        self.apply_compress_progress(message)
                    elif message_type == "overall_progress":
                        self.apply_overall_progress(message)
                    elif message_type == "compress_result":
                        self.show_compress_result(message)
                    elif message_type == "open_output_dir":
                        selected_path = message.get("selected_path")
                        if selected_path:
                            self.open_output_folder(Path(selected_path), show_error=False)
                        else:
                            self.open_directory(Path(message["output_dir"]), show_error=False)
                elif message == "__TASK_FINISHED__":
                    self.is_running = False
                    self.current_process = None
                    self.set_cancel_buttons_state(tk.DISABLED)
                    self.set_controls_state(tk.NORMAL)
                else:
                    self.write_log(message)
        except queue.Empty:
            pass

        self.root.after(100, self.process_log_queue)

    def set_controls_state(self, state: str) -> None:
        for control in self.controls:
            control.configure(state=state)

    def set_cancel_buttons_state(self, state: str) -> None:
        for button in self.cancel_buttons:
            button.configure(state=state)

    def log(self, message: str) -> None:
        self.log_queue.put(message)

    def write_log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def clear_log(self) -> None:
        self.log_text.delete("1.0", tk.END)


def main() -> None:
    root = create_tk_root()
    UnifiedVideoToolApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
