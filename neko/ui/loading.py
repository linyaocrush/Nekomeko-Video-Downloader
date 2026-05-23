import queue
import threading
import time
import logging
import urllib.request
import json
import subprocess
import os
import shutil

import customtkinter as ctk
from tkinter import messagebox

logger = logging.getLogger(__name__)


class LoadingScreen(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("猫娘视频下载器 - 加载中...")
        self.configure(fg_color="#FFF0F5")
        self.overrideredirect(True)

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 300) // 2
        self.geometry(f"400x300+{x}+{y}")

        self.loading_queue = queue.Queue()
        self.is_loading = True
        self.after_ids = []

        self.protocol("WM_DELETE_WINDOW", self.close)
        self.setup_ui()

    def setup_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=30, pady=30)

        title_label = ctk.CTkLabel(
            main_frame, text="🐾 猫娘视频下载器",
            font=("微软雅黑", 24, "bold"), text_color="#FF69B4",
        )
        title_label.pack(pady=(20, 10))

        subtitle_label = ctk.CTkLabel(
            main_frame, text="正在初始化...",
            font=("微软雅黑", 12), text_color="#666666",
        )
        subtitle_label.pack(pady=(0, 30))

        self.progress = ctk.CTkProgressBar(main_frame, width=300, height=8)
        self.progress.pack(pady=(0, 20))
        self.progress.set(0)

        self.status_label = ctk.CTkLabel(
            main_frame, text="正在检查缓存...",
            font=("微软雅黑", 10), text_color="#888888",
        )
        self.status_label.pack()

        self.neko_frames = ["🐱", "😸", "😺", "🐈", "😻"]
        self.neko_label = ctk.CTkLabel(main_frame, text=self.neko_frames[0], font=("Arial", 32))
        self.neko_label.pack(pady=(20, 0))

        self.animate_neko()

    def safe_after(self, ms, func):
        try:
            if self and self.winfo_exists():
                after_id = self.after(ms, func)
                self.after_ids.append(after_id)
                return after_id
        except Exception as e:
            logger.error(f"safe_after错误: {e}")
        return None

    def cancel_all_after(self):
        try:
            for after_id in self.after_ids:
                if self and self.winfo_exists():
                    self.after_cancel(after_id)
            self.after_ids.clear()
        except Exception as e:
            logger.error(f"取消after回调错误: {e}")

    def animate_neko(self):
        try:
            if not self.is_loading or not self or not self.winfo_exists():
                return
            current_frame = self.neko_frames[0]
            self.neko_frames = self.neko_frames[1:] + [current_frame]
            self.neko_label.configure(text=current_frame)
            self.safe_after(500, self.animate_neko)
        except Exception as e:
            logger.error(f"动画执行错误: {e}")

    def update_progress(self, value, status=""):
        try:
            if self.is_loading and self and self.winfo_exists():
                self.loading_queue.put((value, status))
        except Exception as e:
            logger.error(f"更新进度错误: {e}")

    def process_updates(self):
        try:
            if not self.is_loading or not self or not self.winfo_exists():
                return
            try:
                while True:
                    value, status = self.loading_queue.get_nowait()
                    self.progress.set(value)
                    if status:
                        self.status_label.configure(text=status)
            except queue.Empty:
                pass
            if self.is_loading and self and self.winfo_exists():
                self.safe_after(100, self.process_updates)
        except Exception as e:
            logger.error(f"处理更新错误: {e}")

    def close(self):
        self.is_loading = False
        try:
            self.cancel_all_after()
            self.withdraw()
            self.quit()
            self.destroy()
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"彻底关闭加载屏时发生意外: {e}")


class UILoader:
    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.loading_screen = None
        self.main_app = None
        self.load_thread = None
        self.loading_completed = False
        self.error_message = None

    def start_loading(self):
        temp_root = ctk.CTk()
        temp_root.withdraw()

        self.loading_screen = LoadingScreen(temp_root)

        threading.Thread(target=self._prepare_app, daemon=True).start()

        self.loading_screen.process_updates()
        self.check_loading_status()

        self.loading_screen.mainloop()

        try:
            temp_root.destroy()
        except Exception:
            pass

        if self.error_message:
            self.show_error_and_exit(self.error_message)
            return

        import tkinter as tk
        tk._default_root = None

        try:
            from .main_window import NekoDownloader
            self.main_app = NekoDownloader(cached_data=self.cached_data_ref)
            self.main_app.mainloop()
        except Exception as e:
            self.show_error_and_exit(f"主程序启动崩溃: {e}")

    def check_loading_status(self):
        if self.loading_completed:
            self.loading_screen.close()
        else:
            if self.loading_screen.winfo_exists():
                self.loading_screen.after(100, self.check_loading_status)

    def _prepare_app(self):
        try:
            self.update_progress_safe(0.2, "检查 ytdlp 版本...")
            if not self.check_and_update_ytdlp():
                self.error_message = "ytdlp 更新失败"
                self.loading_completed = True
                return

            self.update_progress_safe(0.7, "加载缓存数据...")
            self.cached_data_ref = self.cache_manager.load_cache()

            self.update_progress_safe(0.9, "完成初始化...")
            time.sleep(0.2)
            self.loading_completed = True
        except Exception as e:
            self.error_message = str(e)
            self.loading_completed = True

    def check_and_update_ytdlp(self):
        try:
            ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
            current_version = None

            try:
                result = subprocess.run(
                    [ytdlp_path, "--version"], capture_output=True, text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                )
                if result.returncode == 0:
                    current_version = result.stdout.strip()
                    logger.info(f"当前 ytdlp 版本: {current_version}")
                else:
                    logger.warning("无法获取当前 ytdlp 版本")
            except Exception as e:
                logger.error(f"检查 ytdlp 版本失败: {e}")
                return True

            self.update_progress_safe(0.3, "获取最新版本信息...")
            try:
                url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
                with urllib.request.urlopen(url, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    latest_version = data.get("tag_name", "").lstrip("v")
                    logger.info(f"最新 ytdlp 版本: {latest_version}")
            except Exception as e:
                logger.error(f"获取最新版本信息失败: {e}")
                return True

            if current_version and latest_version and current_version != latest_version:
                logger.info(f"需要更新 ytdlp: {current_version} -> {latest_version}")
                self.update_progress_safe(0.4, f"更新 ytdlp 到 v{latest_version}...")

                try:
                    update_cmd = [ytdlp_path, "--update"]
                    result = subprocess.run(
                        update_cmd, capture_output=True, text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                    )
                    if result.returncode == 0:
                        logger.info("ytdlp 更新成功")
                        self.update_progress_safe(0.6, "ytdlp 更新成功")
                    else:
                        logger.error(f"ytdlp 更新失败: {result.stderr}")
                        if os.name == 'nt':
                            self.update_progress_safe(0.5, "尝试手动下载...")
                            try:
                                download_url = (
                                    "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
                                )
                                with urllib.request.urlopen(download_url, timeout=30) as resp:
                                    with open("yt-dlp.exe", "wb") as f:
                                        f.write(resp.read())
                                if shutil.which("yt-dlp"):
                                    os.replace("yt-dlp.exe", shutil.which("yt-dlp"))
                                logger.info("ytdlp 手动更新成功")
                                self.update_progress_safe(0.6, "ytdlp 手动更新成功")
                            except Exception as e:
                                logger.error(f"手动下载失败: {e}")
                                return False
                except Exception as e:
                    logger.error(f"执行更新失败: {e}")
                    return False
            else:
                logger.info("ytdlp 已是最新版本")
                self.update_progress_safe(0.6, "ytdlp 已是最新版本")

            return True
        except Exception as e:
            logger.error(f"检查并更新 ytdlp 时发生错误: {e}")
            return True

    def update_progress_safe(self, value, status=""):
        if self.loading_screen:
            try:
                self.loading_screen.update_progress(value, status)
            except Exception:
                pass

    def show_error_and_exit(self, error_msg):
        if self.loading_screen:
            try:
                self.loading_screen.close()
            except Exception as e:
                logger.error(f"关闭加载屏错误: {e}")

        try:
            error_window = ctk.CTk()
            error_window.title("初始化错误")
            error_window.geometry("400x200")

            error_label = ctk.CTkLabel(
                error_window, text=f"初始化失败:\n{error_msg}",
                font=("微软雅黑", 12), text_color="red",
            )
            error_label.pack(expand=True, pady=20)

            ok_button = ctk.CTkButton(
                error_window, text="确定", command=error_window.destroy,
                fg_color="#FF69B4", hover_color="#FF1493",
            )
            ok_button.pack(pady=10)

            error_window.mainloop()
        except Exception as e:
            logger.error(f"显示错误窗口错误: {e}")
