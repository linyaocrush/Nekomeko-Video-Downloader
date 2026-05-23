import os
import time
import random
import threading
import subprocess
import shutil
import logging

import customtkinter as ctk
from tkinter import messagebox

from ...core.constants import FONT_N, FONT_S, COOKIES_DIR
from ...core.utils import safe_run
from ...core import constants as _c

logger = logging.getLogger(__name__)


class UIHelpersMixin:
    """UI state updates, dialog openers, callbacks, and utility methods."""

    # ── UI state updates ────────────────────────────────────────

    def upd_ui(self, _=None):
        st = "normal" if self.sw_proxy.get() else "disabled"
        self.e_proxy_ip.configure(state=st)
        self.e_proxy_port.configure(state=st)

        if self.switch_time.get():
            self.cut_box.pack(side="left")
        else:
            self.cut_box.pack_forget()

        m = self.seg_mode.get()
        self.sw_embed.configure(state="normal" if "最佳" in m or "手动" in m else "disabled")
        if "手动" in m or "字幕" in m:
            self.fmt_frame.pack(after=self.preview_frame, fill="x", padx=20, pady=10)
            st = "normal" if self.current_meta else "disabled"

            if "字幕" in m:
                self.c_video.pack_forget()
                self.c_audio.pack_forget()
                if hasattr(self, 'c_subtitle_manual'):
                    self.c_subtitle_manual.pack_forget()
                if hasattr(self, 'c_subtitle_only'):
                    self.c_subtitle_only.pack(fill="x", padx=10, pady=5)
                    if hasattr(self, 'subtitle_opts'):
                        if self.subtitle_opts:
                            subtitle_labels = [opt[1] for opt in self.subtitle_opts]
                            self.c_subtitle_only.configure(values=subtitle_labels)
                            self.c_subtitle_only.set(subtitle_labels[0])
                        else:
                            self.c_subtitle_only.configure(values=["下载所有字幕"])
                            self.c_subtitle_only.set("下载所有字幕")
            else:
                if hasattr(self, 'c_video'):
                    self.c_video.pack(fill="x", padx=10, pady=5)
                if hasattr(self, 'c_audio'):
                    self.c_audio.pack(fill="x", padx=10, pady=5)
                if hasattr(self, 'c_subtitle_only'):
                    self.c_subtitle_only.pack_forget()
                if hasattr(self, 'c_subtitle_manual'):
                    self.c_subtitle_manual.pack(fill="x", padx=10, pady=5)
                    if hasattr(self, 'subtitle_opts') and self.subtitle_opts:
                        subtitle_labels = ["不下载字幕", "下载全部字幕"] + [opt[1] for opt in self.subtitle_opts]
                        self.c_subtitle_manual.configure(values=subtitle_labels)
                        self.c_subtitle_manual.set("不下载字幕")
                    else:
                        self.c_subtitle_manual.configure(values=["不下载字幕", "下载全部字幕"])
                        self.c_subtitle_manual.set("不下载字幕")
                self.c_video.configure(state=st)
                self.c_audio.configure(state=st)
        else:
            self.fmt_frame.pack_forget()
        if "聊天室" in m:
            self.chat_frame.pack(after=self.preview_frame, fill="x", padx=20, pady=10)
            self.upd_chat_ui()
        else:
            self.chat_frame.pack_forget()

    def on_main_video_select(self, choice):
        info = self.video_infos.get(choice)
        if info and info['has_audio']:
            self.c_audio.configure(state="disabled")
            self.l_status.configure(text="主人喵~ 这个视频自带声音，就不用再挑音轨啦~")
        else:
            self.c_audio.configure(state="normal")
            self.l_status.configure(text="待命中喵")

    def log(self, msg, mood="happy"):
        def _log():
            try:
                if hasattr(self, 'log_box') and self.log_box:
                    emo = {"happy": ["✨", "🎵", "✅"], "working": ["🐾", "🔍", "💭"], "sad": ["😿", "🥀", "⚠️"], "done": ["🎉", "💖", "😽"]}.get(mood, [""])
                    self.log_box.configure(state="normal")
                    self.log_box.insert("end", f"{msg} {random.choice(emo)}\n")
                    self.log_box.see("end")
                    self.log_box.configure(state="disabled")
                else:
                    print(f"[LOG] {msg}")
            except Exception as e:
                logger.error(f"日志记录错误: {e}")

        try:
            self.run_safe(_log)
        except Exception as e:
            logger.error(f"run_safe执行日志失败: {e}")
            _log()

    def browse(self):
        p = ctk.filedialog.askdirectory()
        if p:
            self.e_dir.delete(0, "end")
            self.e_dir.insert(0, p)

    def refresh_cookies(self):
        fs = ["🚫 No Cookie", "🔄 使用内置提取器"] + ([f for f in os.listdir(COOKIES_DIR) if f.endswith('.txt')] if os.path.exists(COOKIES_DIR) else [])
        self.c_cookie.configure(values=fs)
        self.c_cookie.set(self.cfg["cookie"] if self.cfg["cookie"] in fs else "🚫 No Cookie")
        self.update_browser_selector()

    def update_browser_selector(self, *args):
        if self.c_cookie.get() == "🔄 使用内置提取器":
            self.browser_frame.pack(fill="x", padx=20, pady=5, after=self.net)
        else:
            self.browser_frame.pack_forget()

    # ── Chat filter ─────────────────────────────────────────────

    def get_filter_text(self):
        if not self.chat_filters:
            return "⚙️ 选择保留项..."
        display = ", ".join([f.capitalize() for f in self.chat_filters])
        if len(display) > 20:
            display = display[:20] + "..."
        return f"⚙️ 选择保留项... ({display})"

    def upd_chat_ui(self):
        if self.chat_mode_var.get() == "filter":
            self.btn_chat_filter.configure(text=self.get_filter_text())
            self.btn_chat_filter.pack(pady=5, padx=30, anchor="w")
        else:
            self.btn_chat_filter.pack_forget()

    def open_filter_selector(self):
        from ..dialogs import ChatFilterSelector
        ChatFilterSelector(self, self.chat_filters, self.set_filters)

    def set_filters(self, filters):
        self.chat_filters = filters
        self.upd_chat_ui()

    # ── SponsorBlock ────────────────────────────────────────────

    def on_sponsor_action_change(self, choice):
        self.upd_ui()
        self.refresh_sb_display()
        if "Off" not in choice:
            from ..dialogs import SponsorSelectWindow
            SponsorSelectWindow(self, self.current_sponsor_cats, self.update_sponsor_cats)

    def update_sponsor_cats(self, cats):
        self.current_sponsor_cats = cats
        self.refresh_sb_display()

    def refresh_sb_display(self):
        if self.c_sponsor_action.get().startswith("🙈"):
            self.l_sb_cats.configure(text="")
        else:
            cn = [self.sb_cn_map.get(k, k) for k in self.current_sponsor_cats]
            txt = "、".join(cn)
            self.l_sb_cats.configure(text=f"[{txt[:12]}...]" if len(txt) > 15 else f"[{txt}]")

    # ── Dialog openers ──────────────────────────────────────────

    def open_theme_editor(self):
        try:
            self.update()
            from ..dialogs import ThemeEditorWindow
            ThemeEditorWindow(self)
        except Exception as e:
            logger.error(f"无法打开主题编辑器: {e}")

    def open_batch_window(self):
        from ..dialogs import BatchUrlWindow
        BatchUrlWindow(self, self.run_batch_add)

    def open_stats_window(self):
        from ..stats import StatsWindow
        StatsWindow(self, self.db)

    def open_template_window(self):
        from ..dialogs import TemplateEditorWindow
        TemplateEditorWindow(self, self.cfg["tmpl_on"], self.cfg["tmpl_str"], self.update_template_cfg)

    def open_settings_window(self):
        from ..dialogs import SettingsWindow
        SettingsWindow(self, self.update_paths_cfg)

    # ── Config callbacks ────────────────────────────────────────

    def update_template_cfg(self, e, s):
        self.cfg["tmpl_on"] = e
        self.cfg["tmpl_str"] = s
        self.log("Naming template updated.", "happy")

    def update_paths_cfg(self, y, f):
        self.cfg['ytdlp_path'] = y
        self.cfg['ffmpeg_path'] = f
        self.log("Paths updated!", "happy")

    # ── Batch operations ────────────────────────────────────────

    def run_batch_add(self, urls):
        self.log(f"Batch processing {len(urls)} urls...", "working")
        threading.Thread(target=self.batch_process_logic, args=(urls,), daemon=True).start()

    @safe_run
    def batch_process_logic(self, urls):
        c = 0
        for u in urls:
            u = u.strip()
            if not u:
                continue
            self.log(f"Sniffing: {u}", "working")
            self.perform_analysis(u)
            self.add_to_queue_internal()
            c += 1
            time.sleep(0.5)
        self.log(f"Batch done! Added {c} tasks.", "done")

    # ── Startup ─────────────────────────────────────────────────

    def startup_maintenance(self):
        y_ok, f_ok = False, False
        exe = self.cfg.get('ytdlp_path', '') or shutil.which("yt-dlp") or "yt-dlp"
        if shutil.which("yt-dlp") or os.path.exists(exe):
            y_ok = True
        if shutil.which("ffmpeg"):
            f_ok = True
        elif self.cfg.get('ffmpeg_path', '') and os.path.exists(self.cfg['ffmpeg_path']):
            f_ok = True

        try:
            subprocess.run([exe, "--rm-cache-dir"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            cache_cleared = True
        except Exception:
            cache_cleared = False

        version_info = None
        try:
            res = subprocess.run([exe, "--version"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            version_info = res.stdout.strip()
        except Exception:
            version_info = None

        def update_ui():
            try:
                self.log("Init environment...", "working")
                if cache_cleared:
                    self.log("Cache cleared.", "happy")
                if not y_ok or not f_ok:
                    msg = []
                    if not y_ok:
                        msg.append("yt-dlp")
                    if not f_ok:
                        msg.append("ffmpeg")
                    self.log(f"Missing core: {', '.join(msg)}", "sad")
                    if hasattr(self, 'l_version'):
                        self.l_version.configure(text="Core Missing", text_color="red")
                    self.after(0, lambda: [messagebox.showwarning("Missing", f"Missing: {', '.join(msg)}"), self.open_settings_window()])
                    return
                if hasattr(self, 'l_version'):
                    if version_info:
                        self.l_version.configure(text=f"Core: {version_info}", text_color=_c.CURRENT_THEME["accent"])
                    else:
                        self.l_version.configure(text="Unknown Ver", text_color="gray")
                self.mood_manager.update_logic()
                if hasattr(self, 'update_mood_display'):
                    self.update_mood_display()
            except Exception as e:
                logger.error(f"更新UI错误: {e}")

        try:
            self.run_safe(update_ui)
        except Exception as e:
            logger.error(f"执行UI更新错误: {e}")
