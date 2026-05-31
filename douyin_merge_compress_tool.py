# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk


DEFAULT_FFMPEG = Path(
    r"C:\Users\27110\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
)
DEFAULT_DOWNLOAD_DIR = Path(r"C:\Users\27110\Downloads\Video")
MERGED_SUFFIX = "_合并后"
SUPPORTED_EXTENSIONS = {".mp4", ".ts", ".mkv", ".mov"}


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


def creation_flags() -> int:
    if os.name == "nt":
        return getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return 0


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
        self.current_process: subprocess.Popen[str] | None = None
        self.cancel_requested = False
        self.compress_started_at = 0.0
        self.merge_dir = DEFAULT_DOWNLOAD_DIR
        self.input_file: Path | None = None
        self.output_dir: Path | None = None

        self.ffmpeg_text = tk.StringVar(value="正在检测 ffmpeg...")
        self.merge_dir_text = tk.StringVar(value=str(self.merge_dir))
        self.input_file_text = tk.StringVar(value="未选择")
        self.output_dir_text = tk.StringVar(value="未选择")
        self.overwrite_merge = tk.BooleanVar(value=False)
        self.compress_progress = tk.DoubleVar(value=0.0)
        self.compress_percent_text = tk.StringVar(value="0%")
        self.compress_status_text = tk.StringVar(value="准备中")
        self.compress_elapsed_text = tk.StringVar(value="已用时间：00:00:00")
        self.compress_remaining_text = tk.StringVar(value="预计剩余：--:--:--")
        self.compress_position_text = tk.StringVar(value="进度：00:00:00 / 00:00:00")

        self.build_ui()
        self.refresh_tools()
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
        compress_tab = ttk.Frame(notebook, padding=12)
        notebook.add(merge_tab, text="抖音音视频合并")
        notebook.add(compress_tab, text="视频压缩")

        self.build_merge_tab(merge_tab)
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

    def build_compress_tab(self, parent: ttk.Frame) -> None:
        parent.columnconfigure(1, weight=1)

        ttk.Label(parent, text="视频文件").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(parent, textvariable=self.input_file_text, state="readonly").grid(
            row=0, column=1, sticky="ew", padx=(8, 8), pady=(0, 8)
        )
        file_button = ttk.Button(parent, text="选择文件", command=self.select_video_file)
        file_button.grid(row=0, column=2, sticky="e", pady=(0, 8))
        self.controls.append(file_button)

        ttk.Label(parent, text="输出目录").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(parent, textvariable=self.output_dir_text, state="readonly").grid(
            row=1, column=1, sticky="ew", padx=(8, 8), pady=(0, 8)
        )
        dir_button = ttk.Button(parent, text="选择目录", command=self.select_output_dir)
        dir_button.grid(row=1, column=2, sticky="e", pady=(0, 8))
        self.controls.append(dir_button)

        start_button = ttk.Button(parent, text="开始压缩", command=self.start_compress)
        start_button.grid(row=2, column=1, sticky="w", padx=(8, 8), pady=(4, 0))
        self.controls.append(start_button)

        progress_frame = ttk.Frame(parent)
        progress_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(14, 0))
        progress_frame.columnconfigure(0, weight=1)

        progress_line = ttk.Frame(progress_frame)
        progress_line.grid(row=0, column=0, sticky="ew")
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
            row=1, column=0, sticky="w", pady=(8, 0)
        )
        ttk.Label(progress_frame, textvariable=self.compress_elapsed_text).grid(
            row=2, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(progress_frame, textvariable=self.compress_remaining_text).grid(
            row=3, column=0, sticky="w", pady=(4, 0)
        )
        ttk.Label(progress_frame, textvariable=self.compress_position_text).grid(
            row=4, column=0, sticky="w", pady=(4, 0)
        )

        self.cancel_compress_button = ttk.Button(
            progress_frame,
            text="取消压缩",
            command=self.cancel_compress,
            state=tk.DISABLED,
        )
        self.cancel_compress_button.grid(row=5, column=0, sticky="w", pady=(8, 0))

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

    def refresh_tools(self) -> None:
        self.ffmpeg_path = self.find_ffmpeg_path()
        self.ffprobe_path = self.find_ffprobe_path(self.ffmpeg_path)

        if self.ffmpeg_path:
            if self.ffprobe_path:
                self.ffmpeg_text.set(f"{self.ffmpeg_path}")
                self.write_log(f"已检测到 ffmpeg：{self.ffmpeg_path}")
                self.write_log(f"已检测到 ffprobe：{self.ffprobe_path}")
            else:
                self.ffmpeg_text.set(f"{self.ffmpeg_path}（未找到 ffprobe）")
                self.write_log(f"已检测到 ffmpeg：{self.ffmpeg_path}")
                self.write_log("未检测到 ffprobe，抖音合并功能暂不可用。")
        else:
            self.ffmpeg_text.set("未检测到 ffmpeg")
            self.write_log("未检测到 ffmpeg，请安装 ffmpeg 或把 ffmpeg 放到本工具同级目录的 ffmpeg\\bin 中。")

    def find_ffmpeg_path(self) -> Path | None:
        script_dir = Path(__file__).resolve().parent
        candidates = [
            script_dir / "ffmpeg" / "bin" / "ffmpeg.exe",
            DEFAULT_FFMPEG,
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate

        for command_name in ("ffmpeg.exe", "ffmpeg"):
            found_path = shutil.which(command_name)
            if found_path:
                return Path(found_path)
        return None

    def find_ffprobe_path(self, ffmpeg_path: Path | None) -> Path | None:
        if ffmpeg_path:
            candidate = ffmpeg_path.with_name("ffprobe.exe")
            if candidate.exists():
                return candidate

        for command_name in ("ffprobe.exe", "ffprobe"):
            found_path = shutil.which(command_name)
            if found_path:
                return Path(found_path)
        return None

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
            filetypes=[
                ("支持的视频文件", "*.mp4 *.ts *.mkv *.mov"),
                ("MP4 文件", "*.mp4"),
                ("TS 文件", "*.ts"),
                ("MKV 文件", "*.mkv"),
                ("MOV 文件", "*.mov"),
                ("所有文件", "*.*"),
            ],
        )
        if not file_path:
            return

        input_file = Path(file_path)
        if input_file.suffix.lower() not in SUPPORTED_EXTENSIONS:
            messagebox.showwarning("格式不支持", "暂时只支持 .mp4 / .ts / .mkv / .mov 文件。")
            return

        self.input_file = input_file
        self.input_file_text.set(str(self.input_file))
        self.write_log(f"已选择视频文件：{self.input_file}")

    def select_output_dir(self) -> None:
        dir_path = filedialog.askdirectory(title="选择输出目录")
        if not dir_path:
            return

        self.output_dir = Path(dir_path)
        self.output_dir_text.set(str(self.output_dir))
        self.write_log(f"已选择输出目录：{self.output_dir}")

    def start_merge(self) -> None:
        if not self.ensure_idle():
            return
        if not self.ffmpeg_path:
            messagebox.showerror("未检测到 ffmpeg", "请先安装 ffmpeg 或点击“重新检测”。")
            return
        if not self.ffprobe_path:
            messagebox.showerror("未检测到 ffprobe", "抖音合并需要 ffprobe，请检查 ffmpeg 安装目录。")
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

    def start_compress(self) -> None:
        if not self.ensure_idle():
            return
        if not self.ffmpeg_path:
            messagebox.showerror("未检测到 ffmpeg", "请先安装 ffmpeg 或点击“重新检测”。")
            return
        if not self.ffprobe_path:
            messagebox.showerror("未检测到 ffprobe", "视频压缩需要 ffprobe 获取视频时长。")
            return
        if not self.input_file:
            messagebox.showwarning("缺少视频文件", "请先点击“选择文件”。")
            return
        if not self.output_dir:
            messagebox.showwarning("缺少输出目录", "请先点击“选择目录”。")
            return
        if not self.input_file.exists():
            messagebox.showerror("文件不存在", "选择的视频文件不存在，请重新选择。")
            return
        if not self.output_dir.exists():
            messagebox.showerror("目录不存在", "选择的输出目录不存在，请重新选择。")
            return

        output_file = self.build_unique_output_path(self.input_file, self.output_dir)
        self.reset_compress_progress("准备中")
        self.cancel_requested = False
        self.start_worker(
            self.run_compress,
            self.input_file,
            output_file,
            self.ffmpeg_path,
            self.ffprobe_path,
        )
        self.cancel_compress_button.configure(state=tk.NORMAL)

    def build_unique_output_path(self, input_file: Path, output_dir: Path) -> Path:
        output_file = output_dir / f"{input_file.stem}_压缩后.mp4"
        index = 1
        while output_file.exists():
            output_file = output_dir / f"{input_file.stem}_压缩后_{index}.mp4"
            index += 1
        return output_file

    def run_compress(
        self,
        input_file: Path,
        output_file: Path,
        ffmpeg: Path,
        ffprobe: Path,
    ) -> None:
        self.log("")
        self.log("准备压缩")
        self.log(f"输入文件：{input_file}")
        self.log(f"输出文件：{output_file}")

        original_size = input_file.stat().st_size
        self.compress_started_at = time.monotonic()
        self.post_compress_progress(status="正在分析视频时长")

        duration = self.probe_video_duration(input_file, ffprobe)
        if duration <= 0:
            message = "无法获取视频总时长，已停止压缩。"
            self.log(message)
            self.post_compress_progress(status="压缩失败")
            self.post_compress_result("压缩失败", message, is_error=True)
            return
        if self.cancel_requested:
            self.log("用户取消压缩。")
            self.post_compress_progress(status="用户取消")
            return

        self.log(f"视频总时长：{format_seconds(duration)}")
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
            "900k",
            "-maxrate",
            "900k",
            "-bufsize",
            "1800k",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
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

            return_code = process.wait()
        finally:
            self.current_process = None
            stderr_thread.join(timeout=1)

        if self.cancel_requested:
            self.log("用户取消压缩。")
            self.post_compress_progress(status="用户取消")
            return

        if return_code == 0:
            compressed_size = output_file.stat().st_size if output_file.exists() else 0
            elapsed = time.monotonic() - self.compress_started_at
            summary = self.build_success_summary(
                output_file,
                original_size,
                compressed_size,
                elapsed,
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
            self.post_compress_result("压缩完成", summary, output_path=output_file)
            return

        error_text = self.build_error_summary(return_code, error_lines)
        self.log("压缩失败")
        self.log(error_text)
        self.post_compress_progress(status="压缩失败")
        self.post_compress_result("压缩失败", error_text, is_error=True)

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

    def reset_compress_progress(self, status: str) -> None:
        self.compress_progress.set(0)
        self.compress_percent_text.set("0%")
        self.compress_status_text.set(status)
        self.compress_elapsed_text.set("已用时间：00:00:00")
        self.compress_remaining_text.set("预计剩余：--:--:--")
        self.compress_position_text.set("进度：00:00:00 / 00:00:00")

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

    def open_output_folder(self, output_path: Path) -> None:
        try:
            if not output_path.exists():
                raise FileNotFoundError(output_path)
            selected_path = output_path.resolve(strict=True)
            if os.name == "nt":
                self.select_file_in_windows_explorer(selected_path)
            else:
                subprocess.Popen(["xdg-open", str(selected_path.parent)])
        except Exception as exc:
            self.show_open_error("打开输出文件夹失败", output_path, exc)

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
                self.cancel_compress_button.configure(state=tk.DISABLED)
                self.compress_status_text.set("用户取消")
                self.log("收到取消请求，任务将在 ffmpeg 启动前停止。")
            return

        self.cancel_requested = True
        self.cancel_compress_button.configure(state=tk.DISABLED)
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
    ) -> str:
        ratio = 0.0
        if original_size > 0:
            ratio = (1 - compressed_size / original_size) * 100

        return "\n".join(
            [
                f"输出文件：{output_file}",
                f"原文件大小：{format_file_size(original_size)}",
                f"压缩后文件大小：{format_file_size(compressed_size)}",
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
            if getattr(target, "__name__", "") == "run_compress":
                self.post_compress_progress(status="压缩失败")
                self.post_compress_result("压缩失败", f"找不到外部程序或文件：{exc}", is_error=True)
        except Exception as exc:
            self.log(f"发生异常：{exc}")
            if getattr(target, "__name__", "") == "run_compress":
                self.post_compress_progress(status="压缩失败")
                self.post_compress_result("压缩失败", f"发生异常：{exc}", is_error=True)
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
                    elif message_type == "compress_result":
                        self.show_compress_result(message)
                elif message == "__TASK_FINISHED__":
                    self.is_running = False
                    self.current_process = None
                    self.cancel_compress_button.configure(state=tk.DISABLED)
                    self.set_controls_state(tk.NORMAL)
                else:
                    self.write_log(message)
        except queue.Empty:
            pass

        self.root.after(100, self.process_log_queue)

    def set_controls_state(self, state: str) -> None:
        for control in self.controls:
            control.configure(state=state)

    def log(self, message: str) -> None:
        self.log_queue.put(message)

    def write_log(self, message: str) -> None:
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def clear_log(self) -> None:
        self.log_text.delete("1.0", tk.END)


def main() -> None:
    root = tk.Tk()
    UnifiedVideoToolApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
