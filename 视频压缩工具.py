# -*- coding: utf-8 -*-

import os
import queue
import shutil
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext


SUPPORTED_EXTENSIONS = {".mp4", ".ts", ".mkv", ".mov"}
DEFAULT_FFMPEG = Path(
    r"C:\Users\27110\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"
)


class VideoCompressorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("视频压缩工具 MVP")
        self.root.geometry("720x460")
        self.root.minsize(640, 420)

        self.input_file = None
        self.output_dir = None
        self.is_running = False
        self.ffmpeg_path = None

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
        self.select_file_button.pack(side=tk.LEFT, padx=(0, 8))

        self.select_output_button = tk.Button(
            top_frame,
            text="选择输出目录",
            width=16,
            command=self.select_output_dir,
        )
        self.select_output_button.pack(side=tk.LEFT, padx=(0, 8))

        self.start_button = tk.Button(
            top_frame,
            text="开始压缩",
            width=16,
            command=self.start_compress,
        )
        self.start_button.pack(side=tk.LEFT)

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
                "未检测到 ffmpeg",
                "未检测到 ffmpeg，请先安装或配置 PATH",
            )
            self.write_log("未检测到 ffmpeg，请先安装或配置 PATH。")
            self.start_button.config(state=tk.DISABLED)
        else:
            self.write_log(f"已检测到 ffmpeg：{self.ffmpeg_path}")

    def is_ffmpeg_available(self):
        return self.find_ffmpeg_path() is not None

    def find_ffmpeg_path(self):
        # 先找当前脚本同级目录下的 ffmpeg\bin\ffmpeg.exe。
        # 这样后续如果你把 ffmpeg 放到工具旁边，即使 GUI 程序拿到的 PATH 不完整也能找到。
        script_dir = Path(__file__).resolve().parent
        local_ffmpeg = script_dir / "ffmpeg" / "bin" / "ffmpeg.exe"
        if local_ffmpeg.exists():
            self.ffmpeg_path = str(local_ffmpeg)
            return self.ffmpeg_path

        if DEFAULT_FFMPEG.exists():
            self.ffmpeg_path = str(DEFAULT_FFMPEG)
            return self.ffmpeg_path

        # shutil.which 会在当前 Python 进程拿到的 PATH 里查找可执行程序。
        # Windows 上优先查 ffmpeg.exe，再查 ffmpeg，兼容不同环境里的命令名。
        for command_name in ("ffmpeg.exe", "ffmpeg"):
            found_path = shutil.which(command_name)
            if found_path:
                self.ffmpeg_path = found_path
                return self.ffmpeg_path

        self.ffmpeg_path = None
        return None

    def select_video_file(self):
        # filedialog.askopenfilename 会弹出“选择文件”窗口。
        # 这样你不需要手动复制视频路径，选中文件后 Python 会拿到完整路径。
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

        suffix = Path(file_path).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            messagebox.showwarning(
                "格式不支持",
                "暂时只支持 .mp4 / .ts / .mkv / .mov 文件。",
            )
            return

        self.input_file = Path(file_path)
        self.write_log("")
        self.write_log(f"已选择视频文件：{self.input_file}")

    def select_output_dir(self):
        # filedialog.askdirectory 会弹出“选择文件夹”窗口。
        # 本工具要求你必须选择输出目录，避免误把文件写回正在恢复数据的磁盘目录。
        dir_path = filedialog.askdirectory(title="选择输出目录")

        if not dir_path:
            return

        self.output_dir = Path(dir_path)
        self.write_log(f"已选择输出目录：{self.output_dir}")

    def start_compress(self):
        if self.is_running:
            messagebox.showinfo("正在压缩", "当前已有压缩任务在执行，请稍等。")
            return

        if not self.is_ffmpeg_available():
            messagebox.showerror(
                "未检测到 ffmpeg",
                "未检测到 ffmpeg，请先安装或配置 PATH",
            )
            self.write_log("未检测到 ffmpeg，请先安装或配置 PATH。")
            return

        if not self.input_file:
            messagebox.showwarning("缺少视频文件", "请先点击“选择视频文件”。")
            return

        if not self.output_dir:
            messagebox.showwarning("缺少输出目录", "请先点击“选择输出目录”。")
            return

        if not self.input_file.exists():
            messagebox.showerror("文件不存在", "选择的视频文件不存在，请重新选择。")
            return

        if not self.output_dir.exists():
            messagebox.showerror("目录不存在", "选择的输出目录不存在，请重新选择。")
            return

        output_file = self.build_unique_output_path(self.input_file, self.output_dir)

        self.is_running = True
        self.set_buttons_state(tk.DISABLED)
        self.write_log("")
        self.write_log("开始压缩...")
        self.write_log(f"输入文件：{self.input_file}")
        self.write_log(f"输出文件：{output_file}")

        # threading.Thread 用来把耗时的压缩任务放到后台线程执行。
        # 如果直接在按钮回调里运行 ffmpeg，Tkinter 主界面会卡住，窗口像“未响应”。
        worker = threading.Thread(
            target=self.run_ffmpeg,
            args=(self.input_file, output_file),
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

    def run_ffmpeg(self, input_file, output_file):
        # subprocess 负责从 Python 调用外部命令。
        # 这里调用的就是你在终端里可以直接运行的 ffmpeg。
        #
        # 注意：这里没有把命令写成一个长字符串，而是写成列表。
        # 列表形式可以更安全地处理路径里的空格和中文，不需要自己手写引号。
        command = [
            self.ffmpeg_path,
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

        self.log_queue.put("正在执行 ffmpeg，请等待...")

        try:
            # Windows 下这个参数可以避免弹出额外的黑色命令行窗口。
            creation_flags = 0
            if os.name == "nt":
                creation_flags = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creation_flags,
            )

            if result.returncode == 0:
                self.log_queue.put("压缩完成！")
                self.log_queue.put(f"生成文件：{output_file}")
            else:
                self.log_queue.put("压缩失败。")
                self.log_queue.put("ffmpeg 错误信息：")
                self.log_queue.put(result.stderr.strip() or "未返回具体错误信息。")

        except FileNotFoundError:
            self.log_queue.put("未检测到 ffmpeg，请先安装或配置 PATH")
        except Exception as exc:
            self.log_queue.put(f"发生异常：{exc}")
        finally:
            self.log_queue.put("__TASK_FINISHED__")

    def process_log_queue(self):
        try:
            while True:
                message = self.log_queue.get_nowait()

                if message == "__TASK_FINISHED__":
                    self.is_running = False
                    self.set_buttons_state(tk.NORMAL)
                else:
                    self.write_log(message)

        except queue.Empty:
            pass

        self.root.after(100, self.process_log_queue)

    def set_buttons_state(self, state):
        self.select_file_button.config(state=state)
        self.select_output_button.config(state=state)
        self.start_button.config(state=state)

    def write_log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)


def main():
    root = tk.Tk()
    app = VideoCompressorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
