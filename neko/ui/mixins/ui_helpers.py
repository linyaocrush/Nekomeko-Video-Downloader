import os
import time
import random
import threading
import shutil
import logging

import webbrowser
import customtkinter as ctk

from ...core.constants import FONT_N, FONT_B, FONT_S, COOKIES_DIR
from ...core.utils import safe_run
from ...core.process import run_text
from ...core import constants as _c

logger = logging.getLogger(__name__)


class UIHelpersMixin:
    """UI state updates, dialog openers, callbacks, and utility methods."""

    # ── UI state updates ────────────────────────────────────────

    def upd_ui(self, _=None):
        if self.sw_proxy.get():
            self.proxy_box.pack(side="left", padx=(8, 0))
        else:
            self.proxy_box.pack_forget()

        if self.switch_time.get():
            self.cut_box.pack(side="left", padx=(8, 0))
        else:
            self.cut_box.pack_forget()

        m = self.seg_mode.get()
        self.sw_embed.configure(state="normal" if "最佳" in m or "手动" in m else "disabled")
        if "手动" in m or "字幕" in m:
            self.fmt_frame.pack(after=self.seg_mode, fill="x", padx=20, pady=10)
            st = "normal" if self.current_meta else "disabled"

            if "字幕" in m:
                self.c_video.pack_forget()
                self.c_audio.pack_forget()
                self.c_subtitle_manual.pack_forget()
                self.c_subtitle_only.pack(fill="x", padx=10, pady=5)
                if getattr(self, 'subtitle_opts', None):
                    sub_labels = [opt[1] for opt in self.subtitle_opts]
                    self.c_subtitle_only.configure(values=sub_labels)
                    self.c_subtitle_only.set(sub_labels[0])
                else:
                    self.c_subtitle_only.configure(values=["下载所有字幕"])
                    self.c_subtitle_only.set("下载所有字幕")
            else:
                self.c_video.pack(fill="x", padx=10, pady=5)
                self.c_audio.pack(fill="x", padx=10, pady=5)
                self.c_subtitle_only.pack_forget()
                self.c_subtitle_manual.pack(fill="x", padx=10, pady=5)
                if getattr(self, 'subtitle_opts', None):
                    sub_labels = ["不下载字幕", "下载全部字幕"] + [opt[1] for opt in self.subtitle_opts]
                    self.c_subtitle_manual.configure(values=sub_labels)
                else:
                    self.c_subtitle_manual.configure(values=["不下载字幕", "下载全部字幕"])
                self.c_subtitle_manual.set("不下载字幕")
                self.c_video.configure(state=st)
                self.c_audio.configure(state=st)
        else:
            self.fmt_frame.pack_forget()
        if "聊天室" in m:
            self.chat_frame.pack(after=self.seg_mode, fill="x", padx=20, pady=10)
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
        saved_browser = self.cfg.get("browser", "chrome")
        if hasattr(self, 'c_browser'):
            self.c_browser.set(saved_browser)
        self.update_browser_selector()

    def update_browser_selector(self, *args):
        if self.c_cookie.get() == "🔄 使用内置提取器":
            self.browser_row.pack(fill="x", padx=10, pady=3, after=self._adv_r5)
        else:
            self.browser_row.pack_forget()

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
            run_text([exe, "--rm-cache-dir"], capture=True)
            cache_cleared = True
        except Exception:
            cache_cleared = False

        version_info = None
        try:
            res = run_text([exe, "--version"])
            version_info = res.stdout.strip()
        except Exception:
            version_info = None

        def update_ui():
            try:
                self.log("Init environment...", "working")
                if cache_cleared:
                    self.log("Cache cleared.", "happy")
                if not y_ok or not f_ok:
                    self.log("未找到核心组件，正在打开提示...", "sad")
                    self.l_version.configure(text="组件缺失", text_color=_c.CURRENT_THEME["error"])
                    self.after(0, lambda: self._show_missing_dialog(y_ok, f_ok))
                    return
                if version_info:
                    self.l_version.configure(text=f"Core: {version_info}", text_color=_c.CURRENT_THEME["accent"])
                else:
                    self.l_version.configure(text="Unknown Ver", text_color=_c.CURRENT_THEME["on_surface_variant"])
                # Check for JS runtime (needed by yt-dlp for YouTube)
                if not shutil.which("node") and not shutil.which("deno"):
                    self.log("⚠️ 未检测到 Node.js/Deno，YouTube 提取可能受限", "sad")
                self.mood_manager.update_logic()
                self.update_mood_display()
            except Exception as e:
                logger.error(f"更新UI错误: {e}")

        try:
            self.run_safe(update_ui)
        except Exception as e:
            logger.error(f"执行UI更新错误: {e}")

    def _show_missing_dialog(self, y_ok, f_ok):
        missing = []
        if not y_ok:
            missing.append(("yt-dlp", "https://github.com/yt-dlp/yt-dlp/releases"))
        if not f_ok:
            missing.append(("ffmpeg", "https://github.com/BtbN/FFmpeg-Builds/releases"))

        names = "、".join(n for n, _ in missing)
        win = ctk.CTkToplevel(self)
        win.title("组件缺失")
        win.geometry("480x260")
        win.transient(self)
        win.grab_set()
        win.configure(fg_color=_c.CURRENT_THEME["main_bg"])

        ctk.CTkLabel(win, text="⚠️ 未找到以下核心组件", font=FONT_B, text_color="red").pack(pady=(20, 5))
        ctk.CTkLabel(win, text=f"猫娘找不到 {names}，无法抓视频小老鼠…", font=FONT_N, text_color=_c.CURRENT_THEME["text"]).pack(pady=(0, 15))

        for name, url in missing:
            row = ctk.CTkFrame(win, fg_color="transparent")
            row.pack(fill="x", padx=30, pady=4)
            ctk.CTkLabel(row, text=f"❌ {name}", font=FONT_N, width=120, anchor="w", text_color=_c.CURRENT_THEME["text"]).pack(side="left")
            ctk.CTkButton(row, text="📥 前往下载", width=100, fg_color=_c.CURRENT_THEME["secondary_container"], text_color=_c.CURRENT_THEME["on_secondary_container"], command=lambda u=url: webbrowser.open(u)).pack(side="right")
            ctk.CTkLabel(row, text="或放入程序根目录", font=FONT_S, text_color="gray").pack(side="right", padx=8)

        ctk.CTkButton(win, text="⚙️ 打开设置手动指定路径", width=200, fg_color=_c.CURRENT_THEME["accent"], command=lambda: [win.destroy(), self.open_settings_window()]).pack(pady=(15, 5))
        ctk.CTkLabel(win, text="💡 也可将 exe 放入程序根目录后重启", font=FONT_S, text_color="gray").pack(pady=(0, 10))
