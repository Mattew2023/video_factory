# -*- coding: utf-8 -*-

import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
import math
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from auto_scan_config import (
    COMPRESSED_NAME_MARKER,
    load_auto_scan_config,
    save_auto_scan_config,
)
from compression_policy import build_compressed_output_path, decide_compression
from compression_records import CompressionRecords, build_task_id
from compression_runner import verify_compressed_output
from file_drop_support import create_tk_root, enable_file_drop
from media_probe import probe_media
from video_scanner import scan_recording_directory


SUPPORTED_EXTENSIONS = {".mp4", ".ts", ".mkv", ".mov", ".avi"}
VIDEO_FILETYPES = [
    ("支持的视频文件", "*.mp4 *.ts *.mkv *.mov *.avi"),
    ("MP4 文件", "*.mp4"),
    ("TS 文件", "*.ts"),
    ("MKV 文件", "*.mkv"),
    ("MOV 文件", "*.mov"),
    ("AVI 文件", "*.avi"),
    ("所有文件", "*.*"),
]
TASK_FINISHED_MESSAGE = "__TASK_FINISHED__"
OPEN_OUTPUT_DIR_MESSAGE = "__OPEN_OUTPUT_DIR__"
PROGRESS_MESSAGE = "__PROGRESS__"
AUTO_SCAN_RESULT_MESSAGE = "__AUTO_SCAN_RESULT__"
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
COMPRESSION_PRESETS = (
    ("接近 1GB（950 MB）", DEFAULT_TARGET_SIZE_MB, DEFAULT_AUDIO_BITRATE_KBPS),
    ("更小（750 MB）", 750, DEFAULT_AUDIO_BITRATE_KBPS),
    ("极小（500 MB）", 500, LOW_AUDIO_BITRATE_KBPS),
)
COMPRESSION_PRESET_LABELS = tuple(preset[0] for preset in COMPRESSION_PRESETS) + (
    CUSTOM_COMPRESSION_PRESET_LABEL,
)
AUDIO_BITRATE_OPTIONS_KBPS = (DEFAULT_AUDIO_BITRATE_KBPS, 80, LOW_AUDIO_BITRATE_KBPS)
MISSING_FFMPEG_MESSAGE = (
    "未检测到 ffmpeg，请把 ffmpeg.exe 和 ffprobe.exe "
    "放到软件目录下的 ffmpeg\\bin 文件夹中，或安装到系统 PATH。"
)
MISSING_FFPROBE_MESSAGE = (
    "未检测到 ffprobe，无法自动计算目标大小。请确认 ffmpeg 安装包中包含 ffprobe。"
)


def program_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def find_command_path(command_names):
    for command_name in command_names:
        found_path = shutil.which(command_name)
        if found_path:
            return Path(found_path)
    return None


def find_local_ffmpeg_path():
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


def format_duration(seconds):
    total_seconds = int(round(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}（{seconds:.1f} 秒）"


def format_file_size(size_bytes):
    size_mb = size_bytes / 1024 / 1024
    if size_mb >= 1024:
        return f"{size_mb / 1024:.2f} GB（{size_mb:.1f} MB）"
    return f"{size_mb:.1f} MB"


def short_error_message(message, max_length=300):
    one_line_message = " ".join(str(message).split())
    if len(one_line_message) <= max_length:
        return one_line_message
    return one_line_message[:max_length] + "..."


def format_target_size_mb(target_size_mb):
    if float(target_size_mb).is_integer():
        return str(int(target_size_mb))
    return f"{target_size_mb:.1f}".rstrip("0").rstrip(".")


def target_size_bytes(target_size_mb):
    return int(target_size_mb * 1024 * 1024)


class VideoCompressorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("视频压缩工具 MVP")
        self.root.geometry("900x680")
        self.root.minsize(820, 560)

        self.input_files = []
        self.output_dir = None
        self.is_running = False
        self.is_auto_scanning = False
        self.is_auto_queue_running = False
        self.ffmpeg_path = None
        self.ffprobe_path = None
        self.ffmpeg_source = ""
        self.completed_output_files = []
        self.video_drop_widgets = []
        self.option_controls = []
        self.auto_controls = []
        self.auto_scan_config = load_auto_scan_config()
        self.auto_records = CompressionRecords(self.auto_scan_config.records_file)
        self.auto_scan_tasks = []
        self.tool_error_title = "未检测到 ffmpeg"
        self.tool_error_message = MISSING_FFMPEG_MESSAGE
        self.ffmpeg_text = tk.StringVar(value="正在检测 ffmpeg...")
        self.compress_preset_text = tk.StringVar(value=COMPRESSION_PRESETS[0][0])
        self.custom_target_size_text = tk.StringVar(
            value=format_target_size_mb(COMPRESSION_PRESETS[0][1])
        )
        self.audio_bitrate_text = tk.StringVar(value=f"{COMPRESSION_PRESETS[0][2]}k")
        self.scan_dir_text = tk.StringVar(
            value=self.format_configured_path(self.auto_scan_config.scan_dir, "未选择扫描目录")
        )
        self.auto_output_dir_text = tk.StringVar(
            value=self.format_configured_path(
                self.auto_scan_config.output_dir,
                "未选择输出目录，将输出到原视频所在目录",
            )
        )
        self.auto_scan_summary_text = tk.StringVar(value="自动扫描：等待配置")
        self.overall_progress_value = tk.DoubleVar(value=0)
        self.current_progress_value = tk.DoubleVar(value=0)
        self.overall_progress_text = tk.StringVar(value="整体进度：第 0 / 0 个，整体百分比 0%")
        self.current_progress_text = tk.StringVar(value="当前视频进度：0%")

        # queue.Queue 用来让后台线程把消息安全地交给主界面。
        # Tkinter 的界面更新必须尽量放在主线程里做，所以后台线程不直接操作文本框。
        self.log_queue = queue.Queue()

        self.build_ui()
        self.check_ffmpeg_on_startup()
        self.root.after(300, self.enable_video_file_drop)
        self.root.after(100, self.process_log_queue)

    def build_ui(self):
        top_frame = tk.Frame(self.root, padx=12, pady=12)
        top_frame.pack(fill=tk.X)

        self.select_file_button = tk.Button(
            top_frame,
            text="选择视频文件",
            width=16,
            command=self.select_video_file,
        )
        self.select_file_button.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 8))

        self.select_multi_files_button = tk.Button(
            top_frame,
            text="选择多个视频文件",
            width=16,
            command=self.select_video_files,
        )
        self.select_multi_files_button.grid(
            row=0,
            column=1,
            sticky="w",
            padx=(0, 8),
            pady=(0, 8),
        )

        self.select_output_button = tk.Button(
            top_frame,
            text="选择输出目录",
            width=14,
            command=self.select_output_dir,
        )
        self.select_output_button.grid(row=1, column=0, sticky="w", padx=(0, 8))

        self.start_button = tk.Button(
            top_frame,
            text="开始压缩",
            width=14,
            command=self.start_compress,
        )
        self.start_button.grid(row=1, column=1, sticky="w", padx=(0, 8))

        self.open_output_button = tk.Button(
            top_frame,
            text="打开输出目录",
            width=14,
            command=self.open_output_dir,
        )
        self.open_output_button.grid(row=1, column=2, sticky="w")
        self.video_drop_widgets.extend(
            [top_frame, self.select_file_button, self.select_multi_files_button]
        )

        ffmpeg_frame = tk.Frame(self.root, padx=12, pady=(0, 8))
        ffmpeg_frame.pack(fill=tk.X)
        tk.Label(ffmpeg_frame, text="ffmpeg").pack(side=tk.LEFT)
        tk.Label(ffmpeg_frame, textvariable=self.ffmpeg_text, anchor="w").pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            padx=(8, 8),
        )
        self.check_ffmpeg_button = tk.Button(
            ffmpeg_frame,
            text="重新检测",
            command=self.check_ffmpeg_on_startup,
        )
        self.check_ffmpeg_button.pack(
            side=tk.RIGHT
        )

        options_frame = tk.LabelFrame(self.root, text="压缩选项", padx=12, pady=8)
        options_frame.pack(fill=tk.X, padx=12, pady=(0, 8))
        options_frame.columnconfigure(1, weight=1)

        tk.Label(options_frame, text="目标大小").grid(
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

        tk.Label(options_frame, text="自定义 MB").grid(
            row=0, column=2, sticky="w", pady=(0, 6)
        )
        target_size_entry = tk.Entry(
            options_frame,
            textvariable=self.custom_target_size_text,
            width=10,
        )
        target_size_entry.grid(row=0, column=3, sticky="w", padx=(8, 0), pady=(0, 6))
        target_size_entry.bind("<KeyRelease>", self.on_custom_target_size_changed)

        tk.Label(options_frame, text="音频保留").grid(row=1, column=0, sticky="w")
        audio_combo = ttk.Combobox(
            options_frame,
            textvariable=self.audio_bitrate_text,
            values=tuple(f"{kbps}k" for kbps in AUDIO_BITRATE_OPTIONS_KBPS),
            state="readonly",
            width=10,
        )
        audio_combo.grid(row=1, column=1, sticky="w", padx=(8, 16))
        self.option_controls.extend(
            [
                (preset_combo, "readonly"),
                (target_size_entry, tk.NORMAL),
                (audio_combo, "readonly"),
            ]
        )

        auto_frame = tk.LabelFrame(self.root, text="自动扫描 MVP", padx=12, pady=8)
        auto_frame.pack(fill=tk.X, padx=12, pady=(0, 8))
        auto_frame.columnconfigure(1, weight=1)

        self.select_scan_dir_button = tk.Button(
            auto_frame,
            text="选择扫描目录",
            width=14,
            command=self.select_auto_scan_dir,
        )
        self.select_scan_dir_button.grid(row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6))
        tk.Label(auto_frame, textvariable=self.scan_dir_text, anchor="w").grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 8),
            pady=(0, 6),
        )
        self.scan_now_button = tk.Button(
            auto_frame,
            text="立即扫描",
            width=12,
            command=self.start_auto_scan,
        )
        self.scan_now_button.grid(row=0, column=2, sticky="e", pady=(0, 6))

        self.select_auto_output_button = tk.Button(
            auto_frame,
            text="选择输出目录",
            width=14,
            command=self.select_auto_output_dir,
        )
        self.select_auto_output_button.grid(
            row=1,
            column=0,
            sticky="w",
            padx=(0, 8),
            pady=(0, 6),
        )
        tk.Label(auto_frame, textvariable=self.auto_output_dir_text, anchor="w").grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 8),
            pady=(0, 6),
        )
        self.start_auto_queue_button = tk.Button(
            auto_frame,
            text="处理扫描队列",
            width=12,
            command=self.start_auto_queue_compress,
        )
        self.start_auto_queue_button.grid(row=1, column=2, sticky="e", pady=(0, 6))
        self.start_auto_queue_button.config(state=tk.DISABLED)

        tk.Label(auto_frame, textvariable=self.auto_scan_summary_text, anchor="w").grid(
            row=2,
            column=0,
            columnspan=3,
            sticky="ew",
        )
        self.auto_controls.extend(
            [
                self.select_scan_dir_button,
                self.select_auto_output_button,
                self.scan_now_button,
                self.start_auto_queue_button,
            ]
        )

        progress_frame = tk.Frame(self.root, padx=12, pady=(0, 8))
        progress_frame.pack(fill=tk.X)
        progress_frame.columnconfigure(1, weight=1)

        tk.Label(progress_frame, textvariable=self.overall_progress_text, anchor="w").grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 4),
        )
        ttk.Progressbar(
            progress_frame,
            variable=self.overall_progress_value,
            maximum=100,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        tk.Label(progress_frame, textvariable=self.current_progress_text, anchor="w").grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 4),
        )
        ttk.Progressbar(
            progress_frame,
            variable=self.current_progress_value,
            maximum=100,
        ).grid(row=3, column=0, columnspan=2, sticky="ew")

        # scrolledtext 是带滚动条的文本区域，用来显示文件路径和执行状态。
        self.log_text = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            font=("Microsoft YaHei UI", 10),
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        self.write_log("请选择视频文件和输出目录。")
        self.write_log("支持格式：.mp4 / .ts / .mkv / .mov / .avi")
        self.write_log("注意：程序不会自动写回原视频所在目录，必须手动选择输出目录。")

    def format_configured_path(self, path_text, empty_text):
        if not path_text:
            return empty_text
        return str(Path(path_text).expanduser())

    def refresh_auto_queue_button(self):
        if (
            self.auto_scan_tasks
            and not self.is_running
            and not self.is_auto_scanning
        ):
            self.start_auto_queue_button.config(state=tk.NORMAL)
        else:
            self.start_auto_queue_button.config(state=tk.DISABLED)

    def save_auto_scan_settings(self):
        save_auto_scan_config(self.auto_scan_config)
        self.auto_records = CompressionRecords(self.auto_scan_config.records_file)

    def select_auto_scan_dir(self):
        if self.is_running or self.is_auto_scanning:
            messagebox.showinfo("正在处理", "当前已有任务在执行，请完成后再修改扫描目录。")
            return

        dir_path = filedialog.askdirectory(parent=self.root, title="选择自动扫描目录")
        if not dir_path:
            return

        self.auto_scan_config.scan_dir = dir_path
        self.scan_dir_text.set(self.format_configured_path(dir_path, "未选择扫描目录"))
        self.save_auto_scan_settings()
        self.write_log(f"自动扫描目录：{dir_path}")

    def select_auto_output_dir(self):
        if self.is_running or self.is_auto_scanning:
            messagebox.showinfo("正在处理", "当前已有任务在执行，请完成后再修改输出目录。")
            return

        dir_path = filedialog.askdirectory(parent=self.root, title="选择自动压缩输出目录")
        if not dir_path:
            return

        self.auto_scan_config.output_dir = dir_path
        self.auto_output_dir_text.set(self.format_configured_path(dir_path, "未选择输出目录"))
        self.save_auto_scan_settings()
        self.write_log(f"自动压缩输出目录：{dir_path}")

    def start_auto_scan(self):
        if self.is_running or self.is_auto_scanning:
            messagebox.showinfo("正在处理", "当前已有任务在执行，请稍等。")
            return

        if not self.auto_scan_config.scan_dir:
            messagebox.showwarning("缺少扫描目录", "请先选择自动扫描目录。")
            return

        if not self.is_ffmpeg_available():
            messagebox.showerror(
                self.tool_error_title,
                self.tool_error_message,
            )
            self.write_log(self.tool_error_message)
            return

        self.auto_scan_tasks = []
        self.refresh_auto_queue_button()
        self.is_auto_scanning = True
        self.set_buttons_state(tk.DISABLED)
        self.auto_scan_summary_text.set("自动扫描：正在扫描和探测视频...")
        self.write_log("")
        self.write_log("开始自动扫描录屏目录...")
        self.write_log(f"扫描目录：{self.auto_scan_config.scan_dir}")
        self.write_log(
            f"任务记录：{self.auto_scan_config.records_file}"
        )

        worker = threading.Thread(
            target=self.run_auto_scan_worker,
            args=(self.auto_scan_config,),
            daemon=True,
        )
        worker.start()

    def run_auto_scan_worker(self, config):
        try:
            records = CompressionRecords(config.records_file)
            scan_result = scan_recording_directory(config, records=records)
            pending_tasks = []
            skipped_details = []
            failed_count = 0
            policy_skipped_count = 0

            for candidate in scan_result.candidates:
                source_path = candidate.path.expanduser().resolve(strict=False)
                task_id = build_task_id(
                    source_path,
                    candidate.size_bytes,
                    candidate.modified_at,
                )
                base_record = {
                    "task_id": task_id,
                    "source_path": str(source_path),
                    "output_path": "",
                    "source_size_bytes": candidate.size_bytes,
                    "output_size_bytes": 0,
                    "status": "probing",
                    "decision": "",
                    "error": "",
                    "modified_at": candidate.modified_at,
                }
                records.append_status(base_record, "probing")

                try:
                    media_info = probe_media(
                        source_path,
                        self.ffprobe_path,
                        creationflags=self.get_creation_flags(),
                    )
                except RuntimeError as exc:
                    failed_count += 1
                    error_message = str(exc)
                    records.append_status(
                        base_record,
                        "skipped",
                        decision="skip",
                        error=error_message,
                    )
                    skipped_details.append(f"{source_path.name}：{short_error_message(error_message)}")
                    continue

                decision = decide_compression(media_info, config)
                record = dict(base_record)
                record.update(
                    {
                        "duration_seconds": media_info.duration_seconds,
                        "width": media_info.width,
                        "height": media_info.height,
                        "frame_rate": media_info.frame_rate,
                        "video_bitrate_kbps": media_info.video_bitrate_kbps,
                        "audio_bitrate_kbps": media_info.audio_bitrate_kbps,
                        "total_bitrate_kbps": media_info.total_bitrate_kbps,
                        "video_codec": media_info.video_codec,
                        "audio_codec": media_info.audio_codec,
                        "target_size_mb": decision.target_size_mb,
                        "target_video_bitrate_kbps": decision.target_video_bitrate_kbps,
                        "target_total_bitrate_kbps": decision.target_total_bitrate_kbps,
                        "target_audio_bitrate_kbps": decision.audio_bitrate_kbps,
                        "video_encoder": decision.video_encoder,
                        "policy_reason": decision.reason,
                        "decision": decision.decision,
                    }
                )

                if decision.decision == "compress":
                    output_dir = config.output_dir_for(source_path)
                    output_path = build_compressed_output_path(
                        source_path,
                        output_dir,
                        decision.output_extension,
                    )
                    record["output_path"] = str(output_path)
                    record["compression_options"] = decision.to_compression_options()
                    records.append_status(record, "pending", error="")
                    pending_tasks.append(record)
                else:
                    policy_skipped_count += 1
                    records.append_status(record, "skipped", error=decision.reason)
                    skipped_details.append(f"{source_path.name}：{decision.reason}")

            self.log_queue.put(
                {
                    "type": AUTO_SCAN_RESULT_MESSAGE,
                    "ok": True,
                    "candidate_count": len(scan_result.candidates),
                    "pre_skipped_count": len(scan_result.skipped),
                    "policy_skipped_count": policy_skipped_count,
                    "failed_count": failed_count,
                    "pending_tasks": pending_tasks,
                    "skipped_details": skipped_details[:20],
                    "records_path": str(config.records_file),
                }
            )
        except Exception as exc:
            self.log_queue.put(
                {
                    "type": AUTO_SCAN_RESULT_MESSAGE,
                    "ok": False,
                    "error": str(exc),
                    "pending_tasks": [],
                }
            )

    def apply_auto_scan_result(self, message):
        self.is_auto_scanning = False
        self.set_buttons_state(tk.NORMAL)

        if not message.get("ok"):
            error_message = message.get("error") or "自动扫描失败。"
            self.auto_scan_summary_text.set(f"自动扫描失败：{short_error_message(error_message, 80)}")
            self.write_log(f"自动扫描失败：{error_message}")
            self.refresh_auto_queue_button()
            return

        self.auto_scan_tasks = list(message.get("pending_tasks") or [])
        pending_count = len(self.auto_scan_tasks)
        candidate_count = message.get("candidate_count", 0)
        pre_skipped_count = message.get("pre_skipped_count", 0)
        policy_skipped_count = message.get("policy_skipped_count", 0)
        failed_count = message.get("failed_count", 0)
        records_path = message.get("records_path", "")

        summary = (
            f"自动扫描完成：候选 {candidate_count} 个，待压缩 {pending_count} 个，"
            f"规则跳过 {pre_skipped_count + policy_skipped_count} 个，探测失败 {failed_count} 个"
        )
        self.auto_scan_summary_text.set(summary)
        self.write_log(summary)
        if records_path:
            self.write_log(f"任务记录已写入：{records_path}")

        if self.auto_scan_tasks:
            self.write_log("待压缩队列：")
            for index, task in enumerate(self.auto_scan_tasks[:20], start=1):
                self.write_log(
                    f"{index}. {Path(task['source_path']).name} | "
                    f"{format_file_size(task['source_size_bytes'])} | "
                    f"{format_duration(task['duration_seconds'])} | "
                    f"目标视频码率 {task['target_video_bitrate_kbps']}k"
                )
            if len(self.auto_scan_tasks) > 20:
                self.write_log(f"……以及另外 {len(self.auto_scan_tasks) - 20} 个待压缩文件")

        skipped_details = message.get("skipped_details") or []
        if skipped_details:
            self.write_log("跳过/失败示例：")
            for detail in skipped_details[:10]:
                self.write_log(f"- {detail}")

        self.refresh_auto_queue_button()

    def compression_options_for_auto_task(self, task):
        options = task.get("compression_options") or {}
        return {
            "label": options.get("label") or "自动扫描智能压缩",
            "target_size_mb": float(options.get("target_size_mb") or task["target_size_mb"]),
            "audio_bitrate_kbps": int(
                options.get("audio_bitrate_kbps")
                or task.get("target_audio_bitrate_kbps")
                or DEFAULT_AUDIO_BITRATE_KBPS
            ),
            "target_video_bitrate_kbps": int(
                options.get("target_video_bitrate_kbps")
                or task["target_video_bitrate_kbps"]
            ),
            "strategy": options.get("strategy") or task.get("policy_reason") or "自动扫描智能压缩",
        }

    def start_auto_queue_compress(self):
        if self.is_running or self.is_auto_scanning:
            messagebox.showinfo("正在处理", "当前已有任务在执行，请稍等。")
            return

        if not self.auto_scan_tasks:
            messagebox.showwarning("没有待处理任务", "请先点击“立即扫描”生成待压缩队列。")
            return

        if not self.is_ffmpeg_available():
            messagebox.showerror(
                self.tool_error_title,
                self.tool_error_message,
            )
            self.write_log(self.tool_error_message)
            return

        tasks = list(self.auto_scan_tasks)
        self.completed_output_files = []
        self.is_running = True
        self.is_auto_queue_running = True
        self.set_buttons_state(tk.DISABLED)
        self.reset_progress(len(tasks))
        self.write_log("")
        self.write_log(f"开始处理自动扫描队列，共 {len(tasks)} 个视频。")

        worker = threading.Thread(
            target=self.run_auto_queue_compress,
            args=(tasks,),
            daemon=True,
        )
        worker.start()

    def run_auto_queue_compress(self, tasks):
        records = CompressionRecords(self.auto_scan_config.records_file)
        total_count = len(tasks)
        success_count = 0
        verified_count = 0
        completed_output_files = []
        failed_items = []

        try:
            for index, task in enumerate(tasks, start=1):
                input_file = Path(task["source_path"])
                output_file = Path(task["output_path"])
                completed_count = index - 1

                self.log_queue.put("")
                self.log_queue.put(f"自动队列：正在处理第 {index} / {total_count} 个")
                self.log_queue.put(f"输入文件：{input_file}")
                self.log_queue.put(f"输出文件：{output_file}")
                self.queue_progress(completed_count, total_count, 0, index)

                try:
                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    records.append_status(task, "compressing", error="")
                    source_info = probe_media(
                        input_file,
                        self.ffprobe_path,
                        creationflags=self.get_creation_flags(),
                    )
                except Exception as exc:
                    error_message = str(exc)
                    records.append_status(task, "failed", error=error_message)
                    failed_items.append((input_file, error_message))
                    self.queue_progress(completed_count, total_count, 1.0, index)
                    continue

                result = self.compress_single_video(
                    input_file,
                    output_file,
                    completed_count,
                    total_count,
                    index,
                    self.compression_options_for_auto_task(task),
                )

                if not result["success"]:
                    error_message = result.get("error") or "压缩失败。"
                    records.append_status(task, "failed", error=error_message)
                    failed_items.append((input_file, error_message))
                    self.queue_progress(completed_count, total_count, 1.0, index)
                    continue

                success_count += 1
                output_size_bytes = result["size_bytes"]
                records.append_status(
                    task,
                    "success",
                    output_size_bytes=output_size_bytes,
                    error="",
                )
                verification = verify_compressed_output(
                    source_info,
                    output_file,
                    self.ffprobe_path,
                    creationflags=self.get_creation_flags(),
                )
                if verification.ok:
                    verified_count += 1
                    completed_output_files.append(output_file)
                    records.append_status(
                        task,
                        "verified",
                        output_size_bytes=output_file.stat().st_size,
                        error="",
                    )
                    self.log_queue.put("输出校验通过，原文件已保留。")
                else:
                    error_message = "校验失败：" + "；".join(verification.errors)
                    records.append_status(task, "failed", error=error_message)
                    failed_items.append((input_file, error_message))
                    self.log_queue.put(error_message)

                self.queue_progress(completed_count, total_count, 1.0, index)

            self.log_queue.put("")
            self.log_queue.put("自动扫描队列处理完成。")
            self.log_queue.put(
                f"最后汇总：压缩成功 {success_count} 个，校验通过 {verified_count} 个，失败 {len(failed_items)} 个。"
            )
            if completed_output_files:
                self.completed_output_files = completed_output_files
                self.log_queue.put("校验通过文件：")
                for output_file in completed_output_files:
                    self.log_queue.put(f"- {output_file}")
            if failed_items:
                self.log_queue.put("失败列表：")
                for input_file, error_message in failed_items:
                    self.log_queue.put(
                        f"- {input_file.name}：{short_error_message(error_message)}"
                    )
            self.queue_progress(total_count, total_count, 0, total_count)
        finally:
            self.log_queue.put(TASK_FINISHED_MESSAGE)
            selected_path = completed_output_files[-1] if completed_output_files else None
            output_dir = selected_path.parent if selected_path else None
            if output_dir:
                self.log_queue.put(
                    (
                        OPEN_OUTPUT_DIR_MESSAGE,
                        str(output_dir),
                        str(selected_path) if selected_path else None,
                    )
                )

    def enable_video_file_drop(self):
        if enable_file_drop(
            self.root,
            self.video_drop_widgets,
            self.accept_dropped_video_files,
            log=self.write_log,
        ):
            self.write_log("可将一个或多个视频文件拖入窗口自动录入。")
        else:
            self.write_log("当前环境未启用拖拽；仍可使用“选择视频文件/选择多个视频文件”。")

    def accept_dropped_video_files(self, dropped_paths):
        if self.is_running or self.is_auto_scanning:
            messagebox.showinfo("正在处理", "当前已有任务在执行，请完成后再拖入视频。")
            return
        self.accept_video_files(dropped_paths, source="拖入")

    def find_compression_preset(self, label):
        for preset in COMPRESSION_PRESETS:
            if preset[0] == label:
                return preset
        return None

    def on_compress_preset_changed(self, _event=None):
        preset = self.find_compression_preset(self.compress_preset_text.get())
        if not preset:
            return

        self.custom_target_size_text.set(format_target_size_mb(preset[1]))
        self.audio_bitrate_text.set(f"{preset[2]}k")

    def on_custom_target_size_changed(self, _event=None):
        if self.compress_preset_text.get() != CUSTOM_COMPRESSION_PRESET_LABEL:
            self.compress_preset_text.set(CUSTOM_COMPRESSION_PRESET_LABEL)

    def get_compression_options(self):
        preset_label = self.compress_preset_text.get()
        preset = self.find_compression_preset(preset_label)
        if preset:
            label = preset[0]
            target_size_mb = preset[1]
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

        return {
            "label": label,
            "target_size_mb": target_size_mb,
            "audio_bitrate_kbps": audio_bitrate_kbps,
        }

    def check_ffmpeg_on_startup(self):
        if not self.is_ffmpeg_available():
            messagebox.showerror(
                self.tool_error_title,
                self.tool_error_message,
            )
            self.write_log(self.tool_error_message)
            self.start_button.config(state=tk.DISABLED)
        else:
            self.write_log(f"已检测到 ffmpeg：{self.ffmpeg_path}")
            self.write_log(f"已检测到 ffprobe：{self.ffprobe_path}")
            if not self.is_running:
                self.start_button.config(state=tk.NORMAL)

    def is_ffmpeg_available(self):
        self.ffmpeg_path, self.ffprobe_path, self.ffmpeg_source = self.find_ffmpeg_tools()
        if self.ffmpeg_path and self.ffprobe_path:
            self.ffmpeg_text.set(f"当前使用：{self.ffmpeg_source} | {self.ffmpeg_path}")
            return True

        if self.ffmpeg_path:
            self.tool_error_title = "未检测到 ffprobe"
            self.tool_error_message = MISSING_FFPROBE_MESSAGE
            self.ffmpeg_text.set("未检测到 ffprobe")
        else:
            self.tool_error_title = "未检测到 ffmpeg"
            self.tool_error_message = MISSING_FFMPEG_MESSAGE
            self.ffmpeg_text.set("未检测到 ffmpeg")
        return False

    def find_ffmpeg_tools(self):
        ffmpeg_path, ffmpeg_source = find_local_ffmpeg_path()
        if not ffmpeg_path:
            ffmpeg_path = find_command_path(("ffmpeg.exe", "ffmpeg"))
            ffmpeg_source = "系统 PATH" if ffmpeg_path else ""

        if not ffmpeg_path:
            return None, None, ""

        same_dir_ffprobe = ffmpeg_path.parent / "ffprobe.exe"
        if same_dir_ffprobe.exists():
            return str(ffmpeg_path), str(same_dir_ffprobe), ffmpeg_source

        path_ffprobe = find_command_path(("ffprobe.exe", "ffprobe"))
        if path_ffprobe:
            return str(ffmpeg_path), str(path_ffprobe), f"{ffmpeg_source} + PATH ffprobe"

        return str(ffmpeg_path), None, ffmpeg_source

    def select_video_file(self):
        # filedialog.askopenfilename 会弹出“选择文件”窗口。
        # 这样你不需要手动复制视频路径，选中文件后 Python 会拿到完整路径。
        file_path = filedialog.askopenfilename(
            parent=self.root,
            title="选择视频文件",
            filetypes=VIDEO_FILETYPES,
        )

        if not file_path:
            return

        self.accept_video_files([Path(file_path)], source="选择")

    def select_video_files(self):
        file_paths = filedialog.askopenfilenames(
            parent=self.root,
            title="选择多个视频文件",
            filetypes=VIDEO_FILETYPES,
        )

        if not file_paths:
            return

        self.accept_video_files([Path(file_path) for file_path in file_paths], source="选择")

    def accept_video_files(self, selected_files, source):
        unique_files = []
        seen = set()
        for input_file in selected_files:
            normalized_file = Path(input_file).expanduser()
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
                "暂时只支持 .mp4 / .ts / .mkv / .mov / .avi 文件。",
            )

        if not supported_files:
            return False

        self.input_files = supported_files
        self.write_log("")
        self.write_log(f"已{source} {len(self.input_files)} 个视频。")
        for index, input_file in enumerate(self.input_files, start=1):
            self.write_log(f"{index}. {input_file}")
        return True

    def select_output_dir(self):
        # filedialog.askdirectory 会弹出“选择文件夹”窗口。
        # 本工具要求你必须选择输出目录，避免误把文件写回正在恢复数据的磁盘目录。
        dir_path = filedialog.askdirectory(parent=self.root, title="选择输出目录")

        if not dir_path:
            return

        self.output_dir = Path(dir_path)
        self.completed_output_files = []
        self.write_log(f"已选择输出目录：{self.output_dir}")

    def open_output_dir(self):
        if not self.output_dir:
            messagebox.showwarning("缺少输出目录", "请先点击“选择输出目录”。")
            return

        self.open_output_dir_path(
            self.output_dir,
            show_error=True,
            selected_path=self.get_last_completed_output_file(),
        )

    def open_output_dir_path(self, output_dir, show_error, selected_path=None):
        output_dir = Path(output_dir)
        if not output_dir.exists():
            message = "选择的输出目录不存在，请重新选择。"
            if show_error:
                messagebox.showerror("目录不存在", message)
            else:
                self.write_log(message)
            return

        try:
            selected_path = Path(selected_path) if selected_path else None
            if selected_path and selected_path.exists():
                if os.name == "nt":
                    self.select_file_in_windows_explorer(selected_path.resolve(strict=True))
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", "-R", str(selected_path)])
                else:
                    subprocess.Popen(["xdg-open", str(selected_path.parent)])
                return

            if os.name == "nt":
                os.startfile(output_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(output_dir)])
            else:
                subprocess.Popen(["xdg-open", str(output_dir)])
        except Exception as exc:
            message = f"打开输出目录失败：{exc}"
            if show_error:
                messagebox.showerror("打开失败", message)
            else:
                self.write_log(message)

    def select_file_in_windows_explorer(self, selected_path):
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
            self.write_log(f"Explorer 选中文件失败，改为打开目录：{selected_path.parent}")
            os.startfile(str(selected_path.parent))

    def get_last_completed_output_file(self):
        for output_file in reversed(self.completed_output_files):
            if output_file.exists():
                return output_file
        return None

    def start_compress(self):
        if self.is_running or self.is_auto_scanning:
            messagebox.showinfo("正在处理", "当前已有任务在执行，请稍等。")
            return

        if not self.is_ffmpeg_available():
            messagebox.showerror(
                self.tool_error_title,
                self.tool_error_message,
            )
            self.write_log(self.tool_error_message)
            return

        if not self.input_files:
            messagebox.showwarning(
                "缺少视频文件",
                "请先点击“选择视频文件”或“选择多个视频文件”。",
            )
            return

        if not self.output_dir:
            messagebox.showwarning("缺少输出目录", "请先点击“选择输出目录”。")
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
        self.is_running = True
        self.set_buttons_state(tk.DISABLED)
        self.reset_progress(len(input_files))
        self.write_log("")
        self.write_log("开始压缩...")
        self.write_log(f"共选择 {len(input_files)} 个视频。")
        self.write_log(f"输出目录：{self.output_dir}")
        self.write_log(f"压缩档位：{compression_options['label']}")
        self.write_log(
            f"目标大小：{format_target_size_mb(compression_options['target_size_mb'])} MB"
        )
        self.write_log(f"音频保留码率：{compression_options['audio_bitrate_kbps']}k")

        # threading.Thread 用来把耗时的压缩任务放到后台线程执行。
        # 如果直接在按钮回调里运行 ffmpeg，Tkinter 主界面会卡住，窗口像“未响应”。
        worker = threading.Thread(
            target=self.run_batch_compress,
            args=(input_files, self.output_dir, compression_options),
            daemon=True,
        )
        worker.start()

    def build_unique_output_path(self, input_file, output_dir):
        base_name = input_file.stem
        if COMPRESSED_NAME_MARKER not in base_name:
            base_name = f"{base_name}_{COMPRESSED_NAME_MARKER}"
        output_file = output_dir / f"{base_name}.mp4"

        index = 1
        while output_file.exists():
            output_file = output_dir / f"{base_name}_{index}.mp4"
            index += 1

        return output_file

    def get_creation_flags(self):
        # Windows 下这个参数可以避免弹出额外的黑色命令行窗口。
        if os.name == "nt":
            return subprocess.CREATE_NO_WINDOW
        return 0

    def get_video_duration(self, input_file):
        if not self.ffprobe_path:
            raise RuntimeError(MISSING_FFPROBE_MESSAGE)

        command = [
            self.ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(input_file),
        ]

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=self.get_creation_flags(),
            )
        except FileNotFoundError as exc:
            raise RuntimeError(MISSING_FFPROBE_MESSAGE) from exc

        if result.returncode != 0:
            error_message = result.stderr.strip() or "未返回具体错误信息。"
            raise RuntimeError(f"ffprobe 获取视频时长失败：{error_message}")

        try:
            duration_seconds = float(result.stdout.strip())
        except ValueError as exc:
            raise RuntimeError("ffprobe 返回的视频时长无效，无法自动计算目标大小。") from exc

        if duration_seconds <= 0:
            raise RuntimeError("ffprobe 返回的视频时长无效，无法自动计算目标大小。")

        return duration_seconds

    def calculate_target_bitrates(self, duration_seconds, compression_options):
        requested_video_bitrate_kbps = compression_options.get("target_video_bitrate_kbps")
        if requested_video_bitrate_kbps:
            video_bitrate_kbps = max(1, int(requested_video_bitrate_kbps))
            audio_bitrate_kbps = int(
                compression_options.get("audio_bitrate_kbps")
                or DEFAULT_AUDIO_BITRATE_KBPS
            )
            strategy = compression_options.get("strategy") or "自动扫描智能压缩"
            return video_bitrate_kbps, audio_bitrate_kbps, strategy

        target_total_bitrate_kbps = (
            compression_options["target_size_mb"] * 8192 / duration_seconds
        )
        audio_bitrate_kbps = compression_options["audio_bitrate_kbps"]
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

    def parse_progress_seconds(self, key, value):
        try:
            if key in {"out_time_ms", "out_time_us"}:
                return max(0.0, int(value) / 1_000_000)
            if key == "out_time":
                hours, minutes, seconds = value.split(":")
                return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        except (ValueError, TypeError):
            return None

        return None

    def collect_stderr(self, process, error_lines):
        if process.stderr is None:
            return

        for raw_line in process.stderr:
            line = raw_line.strip()
            if not line:
                continue
            error_lines.append(line)
            if len(error_lines) > 80:
                del error_lines[:20]

    def queue_progress(self, completed_count, total_count, current_file_progress, current_index):
        if total_count <= 0:
            overall_progress = 0
        else:
            overall_progress = (completed_count + current_file_progress) / total_count

        self.log_queue.put(
            {
                "type": PROGRESS_MESSAGE,
                "completed_count": completed_count,
                "total_count": total_count,
                "current_index": current_index,
                "current_file_progress": current_file_progress,
                "overall_progress": overall_progress,
            }
        )

    def run_batch_compress(self, input_files, output_dir, compression_options):
        total_count = len(input_files)
        success_count = 0
        completed_output_files = []
        failed_items = []

        try:
            for index, input_file in enumerate(input_files, start=1):
                output_file = self.build_unique_output_path(input_file, output_dir)
                completed_count = index - 1

                self.log_queue.put("")
                self.log_queue.put(f"当前正在压缩第 {index} / {total_count} 个")
                self.log_queue.put(f"当前输入文件名：{input_file.name}")
                self.log_queue.put(f"当前输入文件路径：{input_file}")
                self.log_queue.put(f"当前输出文件路径：{output_file}")
                self.queue_progress(completed_count, total_count, 0, index)

                result = self.compress_single_video(
                    input_file,
                    output_file,
                    completed_count,
                    total_count,
                    index,
                    compression_options,
                )
                if result["success"]:
                    success_count += 1
                    completed_output_files.append(output_file)
                    compressed_size_bytes = result["size_bytes"]
                    is_under_target = "是" if result["is_under_target"] else "否"
                    is_under_one_gb = "是" if result["is_under_one_gb"] else "否"
                    self.queue_progress(completed_count, total_count, 1.0, index)
                    self.log_queue.put(
                        f"当前视频压缩完成后的大小：{format_file_size(compressed_size_bytes)}"
                    )
                    self.log_queue.put(f"是否小于目标大小：{is_under_target}")
                    self.log_queue.put(f"是否小于 1GB：{is_under_one_gb}")
                else:
                    failed_items.append((input_file, result["error"]))
                    self.queue_progress(completed_count, total_count, 1.0, index)
                    self.log_queue.put(
                        f"本视频压缩失败：{short_error_message(result['error'])}"
                    )

            self.log_queue.put("")
            self.log_queue.put("批量压缩完成。")
            self.log_queue.put(
                f"最后汇总：成功 {success_count} 个，失败 {len(failed_items)} 个。"
            )
            if completed_output_files:
                self.completed_output_files = completed_output_files
                self.log_queue.put("完成文件：")
                for output_file in completed_output_files:
                    self.log_queue.put(f"- {output_file}")
            if failed_items:
                self.log_queue.put("失败列表：")
                for input_file, error_message in failed_items:
                    self.log_queue.put(
                        f"- {input_file.name}：{short_error_message(error_message)}"
                    )
            self.queue_progress(total_count, total_count, 0, total_count)
        finally:
            self.log_queue.put(TASK_FINISHED_MESSAGE)
            selected_path = completed_output_files[-1] if completed_output_files else None
            self.log_queue.put(
                (
                    OPEN_OUTPUT_DIR_MESSAGE,
                    str(output_dir),
                    str(selected_path) if selected_path else None,
                )
            )

    def compress_single_video(
        self,
        input_file,
        output_file,
        completed_count=0,
        total_count=1,
        current_index=1,
        compression_options=None,
    ):
        # subprocess 负责从 Python 调用外部命令。
        # 这里调用的就是你在终端里可以直接运行的 ffmpeg。
        #
        # 注意：这里没有把命令写成一个长字符串，而是写成列表。
        # 列表形式可以更安全地处理路径里的空格和中文，不需要自己手写引号。
        try:
            if not input_file.exists():
                raise RuntimeError("视频文件不存在，请重新选择。")

            if input_file.suffix.lower() not in SUPPORTED_EXTENSIONS:
                raise RuntimeError("格式不支持，暂时只支持 .mp4 / .ts / .mkv / .mov 文件。")

            if compression_options is None:
                compression_options = {
                    "label": COMPRESSION_PRESETS[0][0],
                    "target_size_mb": COMPRESSION_PRESETS[0][1],
                    "audio_bitrate_kbps": COMPRESSION_PRESETS[0][2],
                }

            duration_seconds = self.get_video_duration(input_file)
            video_bitrate_kbps, audio_bitrate_kbps, strategy = self.calculate_target_bitrates(
                duration_seconds,
                compression_options,
            )
            original_size_bytes = input_file.stat().st_size
            bufsize_kbps = video_bitrate_kbps * 2

            self.log_queue.put(f"视频时长：{format_duration(duration_seconds)}")
            self.log_queue.put(f"压缩档位：{compression_options['label']}")
            self.log_queue.put(
                f"目标大小：{format_target_size_mb(compression_options['target_size_mb'])} MB"
            )
            self.log_queue.put(f"原文件大小：{format_file_size(original_size_bytes)}")
            self.log_queue.put(f"压缩策略：{strategy}")
            self.log_queue.put(f"自动计算的视频码率：{video_bitrate_kbps}k")
            self.log_queue.put(f"音频码率：{audio_bitrate_kbps}k")
            if video_bitrate_kbps < QUALITY_WARNING_VIDEO_BITRATE_KBPS:
                self.log_queue.put("视频时长过长，压到目标大小会明显损失画质。")

            command = [
                self.ffmpeg_path,
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

            self.log_queue.put("正在执行 ffmpeg，请等待...")

            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                creationflags=self.get_creation_flags(),
            )

            error_lines = []
            stderr_thread = threading.Thread(
                target=self.collect_stderr,
                args=(process, error_lines),
                daemon=True,
            )
            stderr_thread.start()

            try:
                if process.stdout is not None:
                    for raw_line in process.stdout:
                        line = raw_line.strip()
                        if not line or "=" not in line:
                            continue

                        key, value = line.split("=", 1)
                        current_seconds = self.parse_progress_seconds(key, value)
                        if current_seconds is not None and duration_seconds > 0:
                            current_file_progress = min(
                                1.0,
                                max(0.0, current_seconds / duration_seconds),
                            )
                            self.queue_progress(
                                completed_count,
                                total_count,
                                current_file_progress,
                                current_index,
                            )
                        elif key == "progress" and value == "end":
                            self.queue_progress(
                                completed_count,
                                total_count,
                                1.0,
                                current_index,
                            )

                return_code = process.wait()
            finally:
                stderr_thread.join(timeout=1)

            if return_code == 0:
                compressed_size_bytes = output_file.stat().st_size
                self.log_queue.put("压缩完成！")
                self.log_queue.put(f"生成文件：{output_file}")
                self.log_queue.put(
                    f"目标大小：{format_target_size_mb(compression_options['target_size_mb'])} MB"
                )
                self.log_queue.put(f"压缩后文件大小：{format_file_size(compressed_size_bytes)}")
                self.log_queue.put(
                    "是否小于目标大小："
                    f"{'是' if compressed_size_bytes <= target_size_bytes(compression_options['target_size_mb']) else '否'}"
                )
                return {
                    "success": True,
                    "size_bytes": compressed_size_bytes,
                    "is_under_target": compressed_size_bytes
                    <= target_size_bytes(compression_options["target_size_mb"]),
                    "is_under_one_gb": compressed_size_bytes < ONE_GB_BYTES,
                }

            error_message = "\n".join(error_lines[-12:]).strip() or "未返回具体错误信息。"
            self.log_queue.put("压缩失败。")
            self.log_queue.put("ffmpeg 错误信息：")
            self.log_queue.put(error_message)
            return {"success": False, "error": error_message}

        except RuntimeError as exc:
            error_message = str(exc)
            self.log_queue.put(error_message)
            return {"success": False, "error": error_message}
        except FileNotFoundError:
            self.log_queue.put(MISSING_FFMPEG_MESSAGE)
            return {"success": False, "error": MISSING_FFMPEG_MESSAGE}
        except Exception as exc:
            error_message = f"发生异常：{exc}"
            self.log_queue.put(error_message)
            return {"success": False, "error": error_message}

    def run_ffmpeg(self, input_file, output_file):
        self.compress_single_video(input_file, output_file)
        self.log_queue.put(TASK_FINISHED_MESSAGE)

    def reset_progress(self, total_count):
        self.overall_progress_value.set(0)
        self.current_progress_value.set(0)
        self.overall_progress_text.set(
            f"整体进度：第 0 / {total_count} 个，整体百分比 0%"
        )
        self.current_progress_text.set("当前视频进度：0%")

    def apply_progress_message(self, message):
        total_count = int(message.get("total_count") or 0)
        completed_count = int(message.get("completed_count") or 0)
        current_index = int(message.get("current_index") or 0)
        current_file_progress = float(message.get("current_file_progress") or 0)
        overall_progress = float(message.get("overall_progress") or 0)

        if total_count > 0 and completed_count >= total_count:
            current_index = total_count
            current_file_progress = 1.0
            overall_progress = 1.0

        current_file_progress = min(max(current_file_progress, 0.0), 1.0)
        overall_progress = min(max(overall_progress, 0.0), 1.0)
        current_percent = current_file_progress * 100
        overall_percent = overall_progress * 100

        self.current_progress_value.set(current_percent)
        self.overall_progress_value.set(overall_percent)
        self.current_progress_text.set(f"当前视频进度：{current_percent:.0f}%")
        self.overall_progress_text.set(
            f"整体进度：第 {current_index} / {total_count} 个，整体百分比 {overall_percent:.0f}%"
        )

    def process_log_queue(self):
        try:
            while True:
                message = self.log_queue.get_nowait()

                if isinstance(message, dict) and message.get("type") == PROGRESS_MESSAGE:
                    self.apply_progress_message(message)
                elif isinstance(message, dict) and message.get("type") == AUTO_SCAN_RESULT_MESSAGE:
                    self.apply_auto_scan_result(message)
                elif message == TASK_FINISHED_MESSAGE:
                    self.is_running = False
                    if self.is_auto_queue_running:
                        self.is_auto_queue_running = False
                        self.auto_scan_tasks = []
                        self.auto_scan_summary_text.set(
                            "自动扫描：本次队列已处理完成，可重新扫描生成新队列"
                        )
                    self.set_buttons_state(tk.NORMAL)
                    self.refresh_auto_queue_button()
                elif (
                    isinstance(message, tuple)
                    and len(message) >= 2
                    and message[0] == OPEN_OUTPUT_DIR_MESSAGE
                ):
                    selected_path = message[2] if len(message) > 2 else None
                    self.open_output_dir_path(
                        message[1],
                        show_error=False,
                        selected_path=selected_path,
                    )
                else:
                    self.write_log(message)

        except queue.Empty:
            pass

        self.root.after(100, self.process_log_queue)

    def set_buttons_state(self, state):
        self.select_file_button.config(state=state)
        self.select_multi_files_button.config(state=state)
        self.select_output_button.config(state=state)
        self.start_button.config(state=state)
        self.open_output_button.config(state=state)
        self.check_ffmpeg_button.config(state=state)
        self.select_scan_dir_button.config(state=state)
        self.select_auto_output_button.config(state=state)
        self.scan_now_button.config(state=state)
        if state == tk.DISABLED:
            self.start_auto_queue_button.config(state=tk.DISABLED)
        else:
            self.refresh_auto_queue_button()
        for control, normal_state in self.option_controls:
            control.config(state=tk.DISABLED if state == tk.DISABLED else normal_state)

    def write_log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)


def main():
    root = create_tk_root()
    app = VideoCompressorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
