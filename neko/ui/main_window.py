import json
import os
import time
import threading
import logging
import webbrowser

import customtkinter as ctk
import tkinter as tk

from ..core.constants import (
    FONT_N, FONT_B, FONT_T, FONT_S, FONT_LOG,
    CFG_FILE,
)
from ..data.database import NekoDB
from ..data.mood import NekoMoodManager
from ..core.cache import CacheManager
from ..core.theme import ThemeManager
from ..core import constants as _c
from .mixins import DownloadMixin, QueueMixin, ResumeMixin, UIHelpersMixin

logger = logging.getLogger(__name__)


class NekoDownloader(DownloadMixin, QueueMixin, ResumeMixin, UIHelpersMixin, ctk.CTk):

    def __init__(self, cached_data=None):
        super().__init__()

        import tkinter as tk_mod
        tk_mod._default_root = self
        self.update_idletasks()

        self.title("🐾 猫娘视频下载器")
        self.geometry("1150x900")
        self.configure(fg_color=_c.CURRENT_THEME["main_bg"])
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        if cached_data:
            self.restore_from_cache(cached_data)

        self.db = NekoDB()
        self.mood_manager = NekoMoodManager(self.db)

        self.video_infos = {}
        self.video_opts = {}
        self.audio_opts = {}
        self.current_meta = None
        self.current_thumb_img = None
        self.last_analyzed_url = ""
        self.queue_items = []
        self.cfg = self.load_cfg()
        self.max_concurrent = 2
        self.current_sponsor_cats = self.cfg.get("sponsor_cats", ["all"])
        self.sb_cn_map = {
            "all": "全部", "sponsor": "广告", "selfpromo": "自推",
            "intro": "片头", "outro": "片尾", "intermission": "中场",
            "preview": "预告", "filler": "废话", "music_offtopic": "乱奏",
        }

        ThemeManager()
        self.setup_ui()
        self.refresh_cookies()
        self.start_thread(self.startup_maintenance)
        self.start_thread(self.check_mood_loop)

    # ── Lifecycle ───────────────────────────────────────────────

    def restore_from_cache(self, cached_data):
        try:
            if 'cfg' in cached_data:
                self.cfg = cached_data['cfg']
            if 'sponsor_cats' in cached_data:
                self.current_sponsor_cats = cached_data['sponsor_cats']
            logger.info("从缓存恢复状态成功")
        except Exception as e:
            logger.error(f"从缓存恢复状态失败: {e}")

    def get_cache_data(self):
        try:
            return {
                'cfg': self.cfg,
                'sponsor_cats': self.current_sponsor_cats,
                'timestamp': time.time(),
            }
        except Exception as e:
            logger.error(f"获取缓存数据失败: {e}")
            return None

    def start_thread(self, target, *args, **kwargs):
        thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return thread

    def load_cfg(self):
        d = {
            "dir": os.path.join(os.path.expanduser("~"), "Videos"), "proxy": "", "proxy_on": False,
            "mode": "最佳喵 (Auto)", "embed": False, "cookie": "🚫 No Cookie", "playlist": False,
            "sponsor_action": "🙈 Off", "sponsor_cats": ["all"],
            "tmpl_on": False, "tmpl_str": "%(title)s", "ytdlp_path": "", "ffmpeg_path": "",
            "chat_mode": "full", "chat_filters": ["author", "message", "timestamp"],
            "time_range_on": False, "start_h": "00", "start_m": "00", "start_s": "00",
            "end_h": "00", "end_m": "00", "end_s": "00",
        }
        if os.path.exists(CFG_FILE):
            try:
                with open(CFG_FILE, "r", encoding="utf-8") as f:
                    return {**d, **json.load(f)}
            except Exception:
                pass
        return d

    def on_close(self):
        try:
            cache_data = self.get_cache_data()
            if cache_data:
                cache_manager = CacheManager()
                cache_manager.save_cache(cache_data)
                logger.info("缓存保存成功")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")

        pv = f"{self.e_proxy_ip.get().strip()}:{self.e_proxy_port.get().strip()}" if self.e_proxy_ip.get().strip() else ""
        d = {
            "dir": self.e_dir.get(), "proxy": pv, "proxy_on": self.sw_proxy.get(),
            "mode": self.seg_mode.get(), "embed": self.sw_embed.get(), "cookie": self.c_cookie.get(),
            "playlist": self.sw_list.get(), "sponsor_action": self.c_sponsor_action.get(),
            "sponsor_cats": self.current_sponsor_cats,
            "tmpl_on": self.cfg["tmpl_on"], "tmpl_str": self.cfg["tmpl_str"],
            "ytdlp_path": self.cfg.get("ytdlp_path", ""), "ffmpeg_path": self.cfg.get("ffmpeg_path", ""),
            "chat_mode": self.chat_mode_var.get(),
            "chat_filters": self.chat_filters,
            "time_range_on": self.switch_time.get(),
            "start_h": self.e_start_h.get(), "start_m": self.e_start_m.get(), "start_s": self.e_start_s.get(),
            "end_h": self.e_end_h.get(), "end_m": self.e_end_m.get(), "end_s": self.e_end_s.get(),
        }
        with open(CFG_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=4)
        self.destroy()

    # ── Thread-safe execution ───────────────────────────────────

    def run_safe(self, func, *args, **kwargs):
        if threading.current_thread() is threading.main_thread():
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"主线程执行函数错误: {e}")
                return None

        try:
            if not hasattr(self, 'winfo_exists'):
                return func(*args, **kwargs)
            try:
                if not self.winfo_exists():
                    return func(*args, **kwargs)
            except RuntimeError as e:
                if "main thread is not in main loop" in str(e):
                    return func(*args, **kwargs)
                else:
                    raise

            evt = threading.Event()
            res = [None]

            def w():
                try:
                    res[0] = func(*args, **kwargs)
                except Exception as e:
                    logger.error(f"执行函数错误: {e}")
                finally:
                    evt.set()

            try:
                self.after(0, w)
                if not evt.wait(timeout=10):
                    logger.error("执行函数超时")
                    return None
                return res[0]
            except Exception as e:
                logger.error(f"使用after执行函数错误: {e}")
                return None
        except Exception as e:
            logger.error(f"run_safe 错误: {e}")
            return None

    # ── Mood ────────────────────────────────────────────────────

    def on_interact(self):
        self.mood_manager.interact()
        self.update_mood_display()

    def check_mood_loop(self):
        while True:
            time.sleep(30)
            try:
                self.mood_manager.update_logic()

                def update_display():
                    try:
                        self.update_mood_display()
                    except Exception as e:
                        logger.error(f"更新心情显示错误: {e}")

                self.run_safe(update_display)
            except Exception as e:
                logger.error(f"心情循环错误: {e}")

    def update_mood_display(self):
        msg = self.mood_manager.get_greeting()
        self.header_tip.configure(text=msg)

    # ── UI helpers ──────────────────────────────────────────────

    # ── UI Layout ───────────────────────────────────────────────

    def setup_ui(self):
        # ── Header ────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", pady=(15, 0))
        tb = ctk.CTkFrame(top, fg_color="transparent")
        tb.pack()
        ba = ctk.CTkFrame(tb, fg_color="transparent")
        ba.pack(side="left", padx=(0, 10))
        ctk.CTkButton(ba, text="⚙️", width=40, height=30, fg_color=_c.CURRENT_THEME["surface_variant"], command=lambda: [self.on_interact(), self.open_settings_window()]).pack(side="left", padx=2)
        ctk.CTkButton(ba, text="🎨", width=40, height=30, fg_color=_c.CURRENT_THEME["accent"], command=lambda: [self.on_interact(), self.open_theme_editor()]).pack(side="left", padx=2)
        ctk.CTkLabel(tb, text="🐾 猫娘下载器", font=FONT_T, text_color=_c.CURRENT_THEME["accent"]).pack(side="left", padx=10)
        ctk.CTkButton(tb, text="📊 记忆仓库", width=120, height=30, fg_color=_c.CURRENT_THEME["secondary_container"], text_color=_c.CURRENT_THEME["on_secondary_container"], command=lambda: [self.on_interact(), self.open_stats_window()]).pack(side="left", padx=10)

        self.l_version = ctk.CTkLabel(top, text="Checking...", font=FONT_S, text_color=_c.CURRENT_THEME["on_surface_variant"])
        self.l_version.pack(pady=(0, 5))
        self.header_tip = ctk.CTkLabel(self, text="主人喵~ 正在把小窝收拾得漂漂亮亮…", font=FONT_N, text_color=_c.CURRENT_THEME["on_surface_variant"])
        self.header_tip.pack(pady=(0, 2))
        self.credit_label = ctk.CTkLabel(self, text="本软件为个人学习交流用途喵~ 请勿用于商业用途。", font=("微软雅黑", 10), text_color=_c.CURRENT_THEME["error"], cursor="hand2")
        self.credit_label.pack(pady=(0, 8))
        self.credit_label.bind("<Button-1>", lambda e: webbrowser.open("https://space.bilibili.com/387715606"))

        # ── Main split ────────────────────────────────────────────
        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=_c.CURRENT_THEME["main_bg"], sashwidth=6, sashrelief=tk.RAISED)
        self.paned.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.left_panel = ctk.CTkFrame(self.paned, fg_color=_c.CURRENT_THEME["secondary"], corner_radius=15)
        self.paned.add(self.left_panel, minsize=400, stretch="always")

        # ── 1. URL input ──────────────────────────────────────────
        inp = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        inp.pack(fill="x", padx=20, pady=(20, 5))
        self.e_url = ctk.CTkEntry(inp, placeholder_text="🔗 把链接丢给猫娘喵…", height=45, font=FONT_N, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        self.e_url.pack(fill="x", pady=(0, 10))
        self.e_url.bind("<Return>", lambda e: self.start_thread(self.smart_add_flow))
        bg = ctk.CTkFrame(inp, fg_color="transparent")
        bg.pack(fill="x")
        ctk.CTkButton(bg, text="🐾 先闻一闻", height=40, font=FONT_B, fg_color=_c.CURRENT_THEME["primary_container"], text_color=_c.CURRENT_THEME["on_primary_container"], command=lambda: [self.on_interact(), self.start_thread(self.analyze_ui_wrapper)]).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(bg, text="📚 批量喂食", height=40, font=FONT_B, fg_color=_c.CURRENT_THEME["tertiary_container"], text_color=_c.CURRENT_THEME["on_tertiary_container"], command=lambda: [self.on_interact(), self.open_batch_window()]).pack(side="left", fill="x", expand=True, padx=(5, 0))

        # ── 2. Preview ────────────────────────────────────────────
        self.preview_frame = ctk.CTkFrame(self.left_panel, fg_color=_c.CURRENT_THEME["panel_bg"], corner_radius=15)
        self.preview_frame.pack(fill="x", padx=20, pady=5)
        self.l_thumb = ctk.CTkLabel(self.preview_frame, text="[猫猫待机]", width=160, height=90, fg_color=_c.CURRENT_THEME["surface_variant"], corner_radius=10)
        self.l_thumb.pack(side="left", padx=15, pady=15)
        self.l_info = ctk.CTkLabel(self.preview_frame, text="等待任务...", font=FONT_N, justify="left", anchor="w", text_color=_c.CURRENT_THEME["text"])
        self.l_info.pack(side="left", fill="both", expand=True, padx=10)
        self.preview_frame.bind("<Configure>", lambda e: self.l_info.configure(wraplength=e.width - 200))

        # ── 3. Mode selector ──────────────────────────────────────
        self.seg_mode = ctk.CTkSegmentedButton(
            self.left_panel,
            values=["最佳喵 (Auto)", "手动挑选 (Manual)", "直播蹲守 (Live)", "只要声音 (MP3)", "只要小纸条 (字幕)", "只抓聊天室 (Chat)"],
            font=FONT_B, height=35, selected_color=_c.CURRENT_THEME["accent"], command=self.upd_ui, text_color=_c.CURRENT_THEME["text"],
        )
        self.seg_mode.pack(fill="x", padx=20, pady=(10, 5))
        self.seg_mode.set(self.cfg["mode"])

        # ── 4. Dynamic frames (format / chat) ─────────────────────
        self.fmt_frame = ctk.CTkFrame(self.left_panel, fg_color=_c.CURRENT_THEME["main_bg"], corner_radius=10)
        ctk.CTkLabel(self.fmt_frame, text="✨ 定制流媒体", font=FONT_B, text_color=_c.CURRENT_THEME["accent"]).pack(anchor="w", padx=10, pady=5)
        self.c_video = ctk.CTkComboBox(self.fmt_frame, values=["请解析"], font=FONT_N, height=32, command=self.on_main_video_select)
        self.c_video.pack(fill="x", padx=10, pady=5)
        self.c_audio = ctk.CTkComboBox(self.fmt_frame, values=["请解析"], font=FONT_N, height=32)
        self.c_audio.pack(fill="x", padx=10, pady=5)
        self.c_subtitle_manual = ctk.CTkComboBox(self.fmt_frame, values=["不下载字幕"], font=FONT_N, height=32)
        self.c_subtitle_only = ctk.CTkComboBox(self.fmt_frame, values=["下载所有字幕"], font=FONT_N, height=32)

        self.chat_frame = ctk.CTkFrame(self.left_panel, fg_color=_c.CURRENT_THEME["main_bg"], corner_radius=10)
        ctk.CTkLabel(self.chat_frame, text="主人喵~ 想抓哪些聊天碎片？", font=FONT_S, text_color=_c.CURRENT_THEME["text"]).pack(anchor="w", padx=10, pady=(5, 0))
        self.chat_mode_var = ctk.StringVar(value=self.cfg.get("chat_mode", "full"))
        ctk.CTkRadioButton(self.chat_frame, text="全部完整记录 (Raw JSON)", variable=self.chat_mode_var, value="full", font=FONT_N, text_color=_c.CURRENT_THEME["text"], fg_color=_c.CURRENT_THEME["accent"], command=self.upd_chat_ui).pack(anchor="w", padx=10, pady=5)
        ctk.CTkRadioButton(self.chat_frame, text="精简筛选 (Filter JSON)", variable=self.chat_mode_var, value="filter", font=FONT_N, text_color=_c.CURRENT_THEME["text"], fg_color=_c.CURRENT_THEME["accent"], command=self.upd_chat_ui).pack(anchor="w", padx=10, pady=5)
        self.btn_chat_filter = ctk.CTkButton(self.chat_frame, text="⚙️ 选择保留项...", width=150, fg_color=_c.CURRENT_THEME["secondary_container"], text_color=_c.CURRENT_THEME["on_secondary_container"], command=self.open_filter_selector)
        self.chat_filters = self.cfg.get("chat_filters", ["author", "message", "timestamp"])

        # ── 5. Action buttons ─────────────────────────────────────
        bb = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        bb.pack(fill="x", padx=20, pady=10)
        bb.columnconfigure(0, weight=1)
        bb.columnconfigure(1, weight=1)
        bb.columnconfigure(2, weight=1)
        bb.columnconfigure(3, weight=1)
        self.btn_add = ctk.CTkButton(bb, text="📥 放进篮子", height=50, font=FONT_B, fg_color=_c.CURRENT_THEME["btn_add_bg"], text_color=_c.CURRENT_THEME["btn_add_fg"], hover_color=_c.CURRENT_THEME["btn_add_bg"], command=lambda: [self.on_interact(), self.start_thread(self.smart_add_flow)])
        self.btn_add.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        self.btn_now = ctk.CTkButton(bb, text="⚡ 立即抓取", height=50, font=FONT_B, fg_color=_c.CURRENT_THEME["btn_now_bg"], text_color=_c.CURRENT_THEME["btn_now_fg"], hover_color=_c.CURRENT_THEME["btn_now_bg"], command=lambda: [self.on_interact(), self.start_thread(self.download_now_flow)])
        self.btn_now.grid(row=0, column=1, padx=5, sticky="ew")
        self.btn_start = ctk.CTkButton(bb, text="🚀 叼回窝里", height=50, font=FONT_B, fg_color=_c.CURRENT_THEME["btn_start_bg"], text_color=_c.CURRENT_THEME["btn_start_fg"], hover_color=_c.CURRENT_THEME["btn_start_bg"], command=lambda: [self.on_interact(), self.start_thread(self.process_queue)])
        self.btn_start.grid(row=0, column=2, padx=5, sticky="ew")
        self.btn_cancel_queue = ctk.CTkButton(bb, text="🛑 取消队列", height=50, font=FONT_B, fg_color=_c.CURRENT_THEME["error_container"], text_color=_c.CURRENT_THEME["on_error_container"], hover_color=_c.CURRENT_THEME["error_container"], command=lambda: [self.on_interact(), self.cancel_queue()])
        self.btn_cancel_queue.grid(row=0, column=3, padx=(5, 0), sticky="ew")
        self.btn_cancel_queue.configure(state="disabled")

        # ── 6. Status + progress ──────────────────────────────────
        self.l_status = ctk.CTkLabel(self.left_panel, text="呼噜呼噜… 待命中喵", font=FONT_S, text_color=_c.CURRENT_THEME["on_surface_variant"])
        self.l_status.pack(pady=(0, 2))
        self.prog = ctk.CTkProgressBar(self.left_panel, progress_color=_c.CURRENT_THEME["accent"], height=12)
        self.prog.pack(fill="x", padx=20, pady=(0, 10))
        self.prog.set(0)

        # ── 7. Collapsible advanced settings ───────────────────────
        self._adv_visible = False
        self.btn_adv = ctk.CTkButton(self.left_panel, text="⚙️ 高级设置 ▸", font=FONT_N, height=28, fg_color=_c.CURRENT_THEME["surface_variant"], text_color=_c.CURRENT_THEME["on_surface_variant"], command=self._toggle_advanced)
        self.btn_adv.pack(fill="x", padx=20, pady=(0, 5))

        self.adv_frame = ctk.CTkFrame(self.left_panel, fg_color=_c.CURRENT_THEME["main_bg"], corner_radius=10)

        # Helper: label on left, control on right
        def _adv_row(label_text, parent=None):
            p = parent or self.adv_frame
            row = ctk.CTkFrame(p, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=3)
            ctk.CTkLabel(row, text=label_text, font=FONT_N, width=110, anchor="w", text_color=_c.CURRENT_THEME["text"]).pack(side="left")
            return row

        # Row 1: SponsorBlock | Cookie
        r1 = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        r1.pack(fill="x", padx=10, pady=3)
        r1.columnconfigure(1, weight=1)
        r1.columnconfigure(3, weight=1)
        ctk.CTkLabel(r1, text="😾 广告处理", font=FONT_N, width=90, anchor="w", text_color=_c.CURRENT_THEME["text"]).grid(row=0, column=0, sticky="w")
        self.c_sponsor_action = ctk.CTkComboBox(r1, values=["🙈 Off", "🔖 Mark", "✂️ Remove"], font=FONT_N, command=self.on_sponsor_action_change, text_color=_c.CURRENT_THEME["text"], fg_color=_c.CURRENT_THEME["panel_bg"])
        self.c_sponsor_action.grid(row=0, column=1, sticky="ew", padx=(5, 15))
        # Migrate old config values to new short form
        _sa = self.cfg["sponsor_action"]
        _sa_map = {"🙈 视而不见 (Off)": "🙈 Off", "🔖 做个记号 (Mark)": "🔖 Mark", "✂️ 咬掉扔了 (Remove)": "✂️ Remove"}
        self.c_sponsor_action.set(_sa_map.get(_sa, _sa))
        self.l_sb_cats = ctk.CTkLabel(r1, text="", font=FONT_S, text_color=_c.CURRENT_THEME["accent"])
        self.l_sb_cats.grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(r1, text="🍪 Cookie", font=FONT_N, width=70, anchor="w", text_color=_c.CURRENT_THEME["text"]).grid(row=0, column=2, sticky="w")
        self.c_cookie = ctk.CTkComboBox(r1, values=["🚫 No Cookie"], height=30, font=FONT_N, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        self.c_cookie.grid(row=0, column=3, sticky="ew", padx=(5, 0))
        self.refresh_sb_display()

        # Row 2: Save directory
        r2 = _adv_row("📂 保存目录")
        self.e_dir = ctk.CTkEntry(r2, placeholder_text="位置...", height=32, font=FONT_N, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        self.e_dir.insert(0, self.cfg["dir"])
        self.e_dir.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(r2, text="🏷️", width=40, height=32, font=FONT_B, fg_color=_c.CURRENT_THEME["secondary_container"], text_color=_c.CURRENT_THEME["on_secondary_container"], command=lambda: [self.on_interact(), self.open_template_window()]).pack(side="left", padx=2)
        ctk.CTkButton(r2, text="📂", width=40, height=32, font=FONT_B, fg_color=_c.CURRENT_THEME["accent"], command=self.browse).pack(side="left", padx=2)

        # Row 3: Simple switches
        r3 = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        r3.pack(fill="x", padx=10, pady=3)
        r3.columnconfigure(0, weight=1)
        r3.columnconfigure(1, weight=1)
        self.sw_list = ctk.CTkSwitch(r3, text="一锅端", font=FONT_N, progress_color=_c.CURRENT_THEME["accent"], text_color=_c.CURRENT_THEME["text"])
        self.sw_list.grid(row=0, column=0, sticky="w", pady=2)
        self.sw_embed = ctk.CTkSwitch(r3, text="硬塞字幕", font=FONT_N, progress_color=_c.CURRENT_THEME["accent"], text_color=_c.CURRENT_THEME["text"])
        self.sw_embed.grid(row=0, column=1, sticky="w", pady=2)
        if self.cfg["playlist"]:
            self.sw_list.select()
        if self.cfg["embed"]:
            self.sw_embed.select()

        # Row 4: Proxy switch + inputs (inline)
        r4 = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        r4.pack(fill="x", padx=10, pady=3)
        self.sw_proxy = ctk.CTkSwitch(r4, text="🌐 代理", font=FONT_N, progress_color=_c.CURRENT_THEME["accent"], text_color=_c.CURRENT_THEME["text"], command=self.upd_ui)
        self.sw_proxy.pack(side="left")
        self.proxy_box = ctk.CTkFrame(r4, fg_color="transparent")
        self.proxy_box.pack(side="left", padx=(8, 0))
        pip, ppt = ("", "")
        if ":" in self.cfg["proxy"]:
            pip, ppt = self.cfg["proxy"].split(":")[:2]
        else:
            pip = self.cfg["proxy"]
        self.e_proxy_ip = ctk.CTkEntry(self.proxy_box, placeholder_text="127.0.0.1", width=120, height=28, font=FONT_N, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        self.e_proxy_ip.insert(0, pip)
        self.e_proxy_ip.pack(side="left")
        ctk.CTkLabel(self.proxy_box, text=":", font=FONT_B, text_color=_c.CURRENT_THEME["text"]).pack(side="left", padx=2)
        self.e_proxy_port = ctk.CTkEntry(self.proxy_box, placeholder_text="7890", width=60, height=28, font=FONT_N, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        self.e_proxy_port.insert(0, ppt)
        self.e_proxy_port.pack(side="left")
        if self.cfg["proxy_on"]:
            self.sw_proxy.select()
        if not self.sw_proxy.get():
            self.proxy_box.pack_forget()

        # Row 5: Time switch + inputs (inline) + Concurrency
        self._adv_r5 = r5 = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        r5.pack(fill="x", padx=10, pady=3)
        self.switch_time = ctk.CTkSwitch(r5, text="✂️ 片段下载", font=FONT_N, progress_color=_c.CURRENT_THEME["accent"], text_color=_c.CURRENT_THEME["text"], command=self.upd_ui)
        self.switch_time.pack(side="left")
        self.cut_box = ctk.CTkFrame(r5, fg_color="transparent")
        self.cut_box.pack(side="left", padx=(8, 0))
        def mk_time_entry(parent, val):
            e = ctk.CTkEntry(parent, width=28, height=24, font=FONT_S, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
            e.insert(0, val)
            return e
        for prefix, keys in [("start", ("start_h", "start_m", "start_s")), ("end", ("end_h", "end_m", "end_s"))]:
            if prefix == "end":
                ctk.CTkLabel(self.cut_box, text="~", font=FONT_S, text_color=_c.CURRENT_THEME["text"]).pack(side="left", padx=4)
            for i, key in enumerate(keys):
                entry = mk_time_entry(self.cut_box, self.cfg.get(key, "00"))
                entry.pack(side="left")
                setattr(self, f"e_{key}", entry)
                if i < 2:
                    ctk.CTkLabel(self.cut_box, text=":", text_color=_c.CURRENT_THEME["text"]).pack(side="left")
        if self.cfg.get("time_range_on"):
            self.switch_time.select()
        if not self.switch_time.get():
            self.cut_box.pack_forget()

        # Concurrency on the right
        ctk.CTkLabel(r5, text="⚡ 并发", font=FONT_N, text_color=_c.CURRENT_THEME["text"]).pack(side="right", padx=(10, 2))
        self.c_concurrent = ctk.CTkComboBox(r5, values=["1", "2", "3", "4", "5"], width=50, state="readonly", command=lambda v: setattr(self, 'max_concurrent', int(v)), fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        self.c_concurrent.set("2")
        self.c_concurrent.pack(side="right")

        # Row 6: Browser cookie
        self.browser_row = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        self.browser_row.pack(fill="x", padx=10, pady=3)
        self.browser_row.pack_forget()  # hidden by default
        self.browser_row.columnconfigure(1, weight=1)
        r6 = self.browser_row
        ctk.CTkLabel(r6, text="🌐 浏览器", font=FONT_N, width=90, anchor="w", text_color=_c.CURRENT_THEME["text"]).grid(row=0, column=0, sticky="w")
        self.browser_frame = ctk.CTkFrame(r6, fg_color="transparent")
        self.browser_frame.grid(row=0, column=1, sticky="ew", padx=5)
        self.c_browser = ctk.CTkComboBox(self.browser_frame, values=["chrome", "firefox", "edge", "safari"], font=FONT_N, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        self.c_browser.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(self.browser_frame, text="Cookie 提取源", font=FONT_S, text_color=_c.CURRENT_THEME["on_surface_variant"]).pack(side="left", padx=8)
        self.c_cookie.configure(command=self.update_browser_selector)

        # Row 7: Resume
        r7 = ctk.CTkFrame(self.adv_frame, fg_color="transparent")
        r7.pack(fill="x", padx=10, pady=(3, 8))
        self.btn_resume_manager = ctk.CTkButton(r7, text="🔄 续传管理", height=28, font=FONT_N, fg_color=_c.CURRENT_THEME["error_container"], text_color=_c.CURRENT_THEME["on_error_container"], command=lambda: [self.on_interact(), self.open_resume_manager()])
        self.btn_resume_manager.pack(side="left")
        self.resume_status_label = ctk.CTkLabel(r7, text="无待续传任务", font=FONT_S, text_color=_c.CURRENT_THEME["on_surface_variant"])
        self.resume_status_label.pack(side="left", padx=10)
        self.after(5000, self.check_resume_status)

        # ── 8. Log box ────────────────────────────────────────────
        self.log_box = ctk.CTkTextbox(self.left_panel, height=100, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"], font=FONT_LOG, state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # ── Right panel (queue) — hidden until first item added ────
        self.right_panel = ctk.CTkFrame(self.paned, fg_color=_c.CURRENT_THEME["secondary"], corner_radius=15)
        ctk.CTkLabel(self.right_panel, text="🛒 篮子里的小老鼠", font=FONT_B, text_color=_c.CURRENT_THEME["accent"]).pack(pady=10)
        self.scroll_q = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent")
        self.scroll_q.pack(fill="both", expand=True, padx=5, pady=(0, 10))
        self.upd_ui()

    def _toggle_advanced(self):
        self._adv_visible = not self._adv_visible
        if self._adv_visible:
            self.adv_frame.pack(fill="x", padx=20, pady=(0, 5), after=self.btn_adv)
            self.btn_adv.configure(text="⚙️ 高级设置 ▾")
        else:
            self.adv_frame.pack_forget()
            self.btn_adv.configure(text="⚙️ 高级设置 ▸")
