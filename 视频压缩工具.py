# -*- coding: utf-8 -*-

import os
import queue
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk


SUPPORTED_EXTENSIONS = {".mp4", ".ts", ".mkv", ".mov"}
VIDEO_FILETYPES = [
    ("支持的视频文件", "*.mp4 *.ts *.mkv *.mov"),
    ("MP4 文件", "*.mp4"),
    ("TS 文件", "*.ts"),
    ("MKV 文件", "*.mkv"),
    ("MOV 文件", "*.mov"),
    ("所有文件", "*.*"),
]
TASK_FINISHED_MESSAGE = "__TASK_FINISHED__"
OPEN_OUTPUT_DIR_MESSAGE = "__OPEN_OUTPUT_DIR__"
PROGRESS_MESSAGE = "__PROGRESS__"
TARGET_SIZE_MB = 950
ONE_GB_BYTES = 1024 * 1024 * 1024
DEFAULT_VIDEO_BITRATE_KBPS = 900
DEFAULT_AUDIO_BITRATE_KBPS = 96
LOW_AUDIO_BITRATE_KBPS = 64
LOW_VIDEO_BITRATE_THRESHOLD_KBPS = 500
QUALITY_WARNING_VIDEO_BITRATE_KBPS = 300
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


class VideoCompressorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("视频压缩工具 MVP")
        self.root.geometry("820x500")
        self.root.minsize(740, 440)

        self.input_files = []
        self.output_dir = None
        self.is_running = False
        self.ffmpeg_path = None
        self.ffprobe_path = None
        self.ffmpeg_source = ""
        self.tool_error_title = "未检测到 ffmpeg"
        self.tool_error_message = MISSING_FFMPEG_MESSAGE
        self.ffmpeg_text = tk.StringVar(value="正在检测 ffmpeg...")
        self.overall_progress_value = tk.DoubleVar(value=0)
        self.current_progress_value = tk.DoubleVar(value=0)
        self.overall_progress_text = tk.StringVar(value="整体进度：第 0 / 0 个，整体百分比 0%")
        self.current_progress_text = tk.StringVar(value="当前视频进度：0%")

        # queue.Queue 用来让后台线程把消息安全地交给主界面。
        # Tkinter 的界面更新必须尽量放在主线程里做，所以后台线程不直接操作文本框。
        self.log_queue = queue.Queue()

        self.build_ui()
        self.check_ffmpeg_on_startup()
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
        self.write_log("支持格式：.mp4 / .ts / .mkv / .mov")
        self.write_log("注意：程序不会自动写回原视频所在目录，必须手动选择输出目录。")

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

        suffix = Path(file_path).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            messagebox.showwarning(
                "格式不支持",
                "暂时只支持 .mp4 / .ts / .mkv / .mov 文件。",
            )
            return

        self.input_files = [Path(file_path)]
        self.write_log("")
        self.write_log(f"已选择视频文件：{self.input_files[0]}")
        self.write_log("共选择 1 个视频。")

    def select_video_files(self):
        file_paths = filedialog.askopenfilenames(
            parent=self.root,
            title="选择多个视频文件",
            filetypes=VIDEO_FILETYPES,
        )

        if not file_paths:
            return

        selected_files = [Path(file_path) for file_path in file_paths]
        supported_files = [
            input_file
            for input_file in selected_files
            if input_file.suffix.lower() in SUPPORTED_EXTENSIONS
        ]
        unsupported_files = [
            input_file
            for input_file in selected_files
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
            return

        self.input_files = supported_files
        self.write_log("")
        self.write_log(f"共选择 {len(self.input_files)} 个视频。")
        for index, input_file in enumerate(self.input_files, start=1):
            self.write_log(f"{index}. {input_file}")

    def select_output_dir(self):
        # filedialog.askdirectory 会弹出“选择文件夹”窗口。
        # 本工具要求你必须选择输出目录，避免误把文件写回正在恢复数据的磁盘目录。
        dir_path = filedialog.askdirectory(parent=self.root, title="选择输出目录")

        if not dir_path:
            return

        self.output_dir = Path(dir_path)
        self.write_log(f"已选择输出目录：{self.output_dir}")

    def open_output_dir(self):
        if not self.output_dir:
            messagebox.showwarning("缺少输出目录", "请先点击“选择输出目录”。")
            return

        self.open_output_dir_path(self.output_dir, show_error=True)

    def open_output_dir_path(self, output_dir, show_error):
        output_dir = Path(output_dir)
        if not output_dir.exists():
            message = "选择的输出目录不存在，请重新选择。"
            if show_error:
                messagebox.showerror("目录不存在", message)
            else:
                self.write_log(message)
            return

        try:
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

    def start_compress(self):
        if self.is_running:
            messagebox.showinfo("正在压缩", "当前已有压缩任务在执行，请稍等。")
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

        input_files = list(self.input_files)
        self.is_running = True
        self.set_buttons_state(tk.DISABLED)
        self.reset_progress(len(input_files))
        self.write_log("")
        self.write_log("开始压缩...")
        self.write_log(f"共选择 {len(input_files)} 个视频。")
        self.write_log(f"输出目录：{self.output_dir}")

        # threading.Thread 用来把耗时的压缩任务放到后台线程执行。
        # 如果直接在按钮回调里运行 ffmpeg，Tkinter 主界面会卡住，窗口像“未响应”。
        worker = threading.Thread(
            target=self.run_batch_compress,
            args=(input_files, self.output_dir),
            daemon=True,
        )
        worker.start()

    def build_unique_output_path(self, input_file, output_dir):
        base_name = input_file.stem
        output_file = output_dir / f"{base_name}_压缩后.mp4"

        index = 1
        while output_file.exists():
            output_file = output_dir / f"{base_name}_压缩后_{index}.mp4"
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

    def calculate_target_bitrates(self, duration_seconds):
        target_total_bitrate_kbps = TARGET_SIZE_MB * 8192 / duration_seconds
        audio_bitrate_kbps = DEFAULT_AUDIO_BITRATE_KBPS
        target_video_bitrate_kbps = target_total_bitrate_kbps - audio_bitrate_kbps

        if target_video_bitrate_kbps < LOW_VIDEO_BITRATE_THRESHOLD_KBPS:
            audio_bitrate_kbps = LOW_AUDIO_BITRATE_KBPS
            target_video_bitrate_kbps = target_total_bitrate_kbps - audio_bitrate_kbps

        video_bitrate_kbps = min(
            DEFAULT_VIDEO_BITRATE_KBPS,
            max(1, int(target_video_bitrate_kbps)),
        )
        strategy = "常规压小优先" if video_bitrate_kbps == DEFAULT_VIDEO_BITRATE_KBPS else "目标大小兜底"

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

    def run_batch_compress(self, input_files, output_dir):
        total_count = len(input_files)
        success_count = 0
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
                )
                if result["success"]:
                    success_count += 1
                    compressed_size_bytes = result["size_bytes"]
                    is_under_one_gb = "是" if result["is_under_one_gb"] else "否"
                    self.queue_progress(completed_count, total_count, 1.0, index)
                    self.log_queue.put(
                        f"当前视频压缩完成后的大小：{format_file_size(compressed_size_bytes)}"
                    )
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
            if failed_items:
                self.log_queue.put("失败列表：")
                for input_file, error_message in failed_items:
                    self.log_queue.put(
                        f"- {input_file.name}：{short_error_message(error_message)}"
                    )
            self.queue_progress(total_count, total_count, 0, total_count)
        finally:
            self.log_queue.put(TASK_FINISHED_MESSAGE)
            self.log_queue.put((OPEN_OUTPUT_DIR_MESSAGE, str(output_dir)))

    def compress_single_video(
        self,
        input_file,
        output_file,
        completed_count=0,
        total_count=1,
        current_index=1,
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

            duration_seconds = self.get_video_duration(input_file)
            video_bitrate_kbps, audio_bitrate_kbps, strategy = self.calculate_target_bitrates(
                duration_seconds
            )
            original_size_bytes = input_file.stat().st_size
            bufsize_kbps = video_bitrate_kbps * 2

            self.log_queue.put(f"视频时长：{format_duration(duration_seconds)}")
            self.log_queue.put(f"目标大小：{TARGET_SIZE_MB} MB")
            self.log_queue.put(f"原文件大小：{format_file_size(original_size_bytes)}")
            self.log_queue.put(f"压缩策略：{strategy}")
            self.log_queue.put(f"自动计算的视频码率：{video_bitrate_kbps}k")
            self.log_queue.put(f"音频码率：{audio_bitrate_kbps}k")
            if video_bitrate_kbps < QUALITY_WARNING_VIDEO_BITRATE_KBPS:
                self.log_queue.put("视频时长过长，压到 1GB 以下会明显损失画质。")

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
                return {
                    "success": True,
                    "size_bytes": compressed_size_bytes,
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
                elif message == TASK_FINISHED_MESSAGE:
                    self.is_running = False
                    self.set_buttons_state(tk.NORMAL)
                elif (
                    isinstance(message, tuple)
                    and len(message) == 2
                    and message[0] == OPEN_OUTPUT_DIR_MESSAGE
                ):
                    self.open_output_dir_path(message[1], show_error=False)
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

    def write_log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)


def main():
    root = tk.Tk()
    app = VideoCompressorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
