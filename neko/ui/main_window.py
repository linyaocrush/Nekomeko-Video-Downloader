import json
import os
import time
import threading
import logging
import webbrowser
from concurrent.futures import ThreadPoolExecutor

import customtkinter as ctk
import tkinter as tk

from ..core.constants import (
    FONT_N, FONT_B, FONT_T, FONT_S, FONT_LOG,
    CFG_FILE, COOKIES_DIR,
)
from ..data.database import NekoDB
from ..data.mood import NekoMoodManager
from ..core.cache import CacheManager
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

        self.thread_pool = ThreadPoolExecutor(max_workers=4)

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

        self.setup_ui()
        self.refresh_cookies()
        self.start_thread(self.startup_maintenance)
        self.start_thread(self.check_mood_loop)

        self.last_saved_bytes = 0

        if not cached_data:
            self.post_init_setup()

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

    def post_init_setup(self):
        pass

    def start_thread(self, target, *args, **kwargs):
        thread = threading.Thread(target=target, args=args, kwargs=kwargs, daemon=True)
        thread.start()
        return thread

    def submit_async_task(self, func, *args, **kwargs):
        return self.thread_pool.submit(func, *args, **kwargs)

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
            "chat_mode": self.chat_mode_var.get() if hasattr(self, 'chat_mode_var') else "full",
            "chat_filters": self.chat_filters if hasattr(self, 'chat_filters') else ["author", "message", "timestamp"],
            "time_range_on": self.switch_time.get() if hasattr(self, 'switch_time') else False,
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
                return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"run_safe 错误: {e}")
            try:
                return func(*args, **kwargs)
            except Exception as e2:
                logger.error(f"直接执行函数也失败: {e2}")
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
                        if hasattr(self, 'update_mood_display') and hasattr(self, 'header_tip'):
                            self.update_mood_display()
                    except Exception as e:
                        logger.error(f"更新心情显示错误: {e}")

                self.run_safe(update_display)
            except Exception as e:
                logger.error(f"心情循环错误: {e}")

    def update_mood_display(self):
        msg = self.mood_manager.get_greeting()
        self.header_tip.configure(text=msg)

    # ── UI Layout ───────────────────────────────────────────────

    def setup_ui(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", pady=(15, 0))
        tb = ctk.CTkFrame(top, fg_color="transparent")
        tb.pack()
        ba = ctk.CTkFrame(tb, fg_color="transparent")
        ba.pack(side="left", padx=(0, 10))
        ctk.CTkButton(ba, text="⚙️", width=40, height=30, fg_color="gray", command=lambda: [self.on_interact(), self.open_settings_window()]).pack(side="left", padx=2)
        ctk.CTkButton(ba, text="🎨", width=40, height=30, fg_color=_c.CURRENT_THEME["accent"], command=lambda: [self.on_interact(), self.open_theme_editor()]).pack(side="left", padx=2)
        ctk.CTkLabel(tb, text="🐾 猫娘下载器", font=FONT_T, text_color=_c.CURRENT_THEME["accent"]).pack(side="left", padx=10)
        ctk.CTkButton(tb, text="📊 记忆仓库", width=120, height=30, fg_color="#9370DB", command=lambda: [self.on_interact(), self.open_stats_window()]).pack(side="left", padx=10)

        self.l_version = ctk.CTkLabel(top, text="Checking...", font=FONT_S, text_color="#888")
        self.l_version.pack(pady=(0, 5))
        self.header_tip = ctk.CTkLabel(self, text="主人喵~ 正在把小窝收拾得漂漂亮亮…", font=FONT_N, text_color="gray")
        self.header_tip.pack(pady=(0, 2))

        self.credit_label = ctk.CTkLabel(self, text="本软件为个人学习交流用途喵~ 请勿用于商业用途。", font=("微软雅黑", 10), text_color="red", cursor="hand2")
        self.credit_label.pack(pady=(0, 8))
        self.credit_label.bind("<Button-1>", lambda e: webbrowser.open("https://space.bilibili.com/387715606"))

        self.paned = tk.PanedWindow(self, orient=tk.HORIZONTAL, bg=_c.CURRENT_THEME["main_bg"], sashwidth=6, sashrelief=tk.RAISED)
        self.paned.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        self.left_panel = ctk.CTkFrame(self.paned, fg_color=_c.CURRENT_THEME["secondary"], corner_radius=15)
        self.paned.add(self.left_panel, minsize=500, stretch="always")

        inp = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        inp.pack(fill="x", padx=20, pady=(20, 5))
        self.e_url = ctk.CTkEntry(inp, placeholder_text="🔗 把链接丢给猫娘喵…", height=45, font=FONT_N, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        self.e_url.pack(fill="x", pady=(0, 10))
        self.e_url.bind("<Return>", lambda e: self.start_thread(self.smart_add_flow))

        bg = ctk.CTkFrame(inp, fg_color="transparent")
        bg.pack(fill="x")
        ctk.CTkButton(bg, text="🐾 先闻一闻", height=40, font=FONT_B, fg_color="#D8BFD8", command=lambda: [self.on_interact(), self.start_thread(self.analyze_ui_wrapper)]).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(bg, text="📚 批量喂食", height=40, font=FONT_B, fg_color="#87CEEB", command=lambda: [self.on_interact(), self.open_batch_window()]).pack(side="left", fill="x", expand=True, padx=(5, 0))

        self.preview_frame = ctk.CTkFrame(self.left_panel, fg_color=_c.CURRENT_THEME["panel_bg"], corner_radius=15)
        self.preview_frame.pack(fill="x", padx=20, pady=5)
        self.l_thumb = ctk.CTkLabel(self.preview_frame, text="[猫猫待机]", width=160, height=90, fg_color="#E0E0E0", corner_radius=10)
        self.l_thumb.pack(side="left", padx=15, pady=15)
        self.l_info = ctk.CTkLabel(self.preview_frame, text="等待任务...", font=FONT_N, justify="left", anchor="w", text_color=_c.CURRENT_THEME["text"])
        self.l_info.pack(side="left", fill="both", expand=True, padx=10)
        self.preview_frame.bind("<Configure>", lambda e: self.l_info.configure(wraplength=e.width - 200))

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
        self.btn_chat_filter = ctk.CTkButton(self.chat_frame, text="⚙️ 选择保留项...", width=150, fg_color="#9370DB", command=self.open_filter_selector)
        self.chat_filters = self.cfg.get("chat_filters", ["author", "message", "timestamp"])

        cfg = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        cfg.pack(fill="x", padx=20, pady=10)
        self.seg_mode = ctk.CTkSegmentedButton(
            cfg,
            values=["最佳喵 (Auto)", "手动挑选 (Manual)", "直播蹲守 (Live)", "只要声音 (MP3)", "只要小纸条 (字幕)", "只抓聊天室 (Chat)"],
            font=FONT_B, height=35, selected_color=_c.CURRENT_THEME["accent"], command=self.upd_ui, text_color=_c.CURRENT_THEME["text"],
        )
        self.seg_mode.pack(fill="x", pady=(0, 10))
        self.seg_mode.set(self.cfg["mode"])

        sb = ctk.CTkFrame(cfg, fg_color="transparent")
        sb.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(sb, text="😾 广告处理:", font=FONT_N, text_color=_c.CURRENT_THEME["text"]).pack(side="left")
        self.c_sponsor_action = ctk.CTkComboBox(
            sb, values=["🙈 视而不见 (Off)", "🔖 做个记号 (Mark)", "✂️ 咬掉扔了 (Remove)"],
            font=FONT_N, width=170, command=self.on_sponsor_action_change,
            text_color=_c.CURRENT_THEME["text"], fg_color=_c.CURRENT_THEME["panel_bg"],
        )
        self.c_sponsor_action.pack(side="left", padx=10)
        self.c_sponsor_action.set(self.cfg["sponsor_action"])
        self.l_sb_cats = ctk.CTkLabel(sb, text="", font=FONT_S, text_color=_c.CURRENT_THEME["accent"])
        self.l_sb_cats.pack(side="left", padx=5)
        self.refresh_sb_display()

        rd = ctk.CTkFrame(cfg, fg_color="transparent")
        rd.pack(fill="x", pady=5)
        self.e_dir = ctk.CTkEntry(rd, placeholder_text="位置...", height=35, font=FONT_N, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        self.e_dir.insert(0, self.cfg["dir"])
        self.e_dir.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(rd, text="🏷️", width=60, height=35, font=FONT_B, fg_color="#9370DB", command=lambda: [self.on_interact(), self.open_template_window()]).pack(side="left", padx=(0, 5))
        ctk.CTkButton(rd, text="📂", width=50, height=35, font=FONT_B, fg_color=_c.CURRENT_THEME["accent"], command=self.browse).pack(side="left")

        sws = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        sws.pack(fill="x", padx=20, pady=5)
        self.sw_list = ctk.CTkSwitch(sws, text="一锅端 (列表)", font=FONT_N, progress_color=_c.CURRENT_THEME["accent"], text_color=_c.CURRENT_THEME["text"])
        self.sw_list.pack(side="left", padx=(0, 15))
        self.sw_embed = ctk.CTkSwitch(sws, text="硬塞字幕", font=FONT_N, progress_color=_c.CURRENT_THEME["accent"], text_color=_c.CURRENT_THEME["text"])
        self.sw_embed.pack(side="left")
        if self.cfg["playlist"]:
            self.sw_list.select()
        if self.cfg["embed"]:
            self.sw_embed.select()

        self.net = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.net.pack(fill="x", padx=20, pady=5)
        self.sw_proxy = ctk.CTkSwitch(self.net, text="魔法通道", font=FONT_N, progress_color=_c.CURRENT_THEME["accent"], command=self.upd_ui, text_color=_c.CURRENT_THEME["text"])
        self.sw_proxy.pack(side="left")
        pip, ppt = ("", "")
        if ":" in self.cfg["proxy"]:
            pip, ppt = self.cfg["proxy"].split(":")[:2]
        else:
            pip = self.cfg["proxy"]
        self.e_proxy_ip = ctk.CTkEntry(self.net, placeholder_text="127.0.0.1", width=130, height=30, font=FONT_N, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        self.e_proxy_ip.insert(0, pip)
        self.e_proxy_ip.pack(side="left", padx=(10, 2))
        ctk.CTkLabel(self.net, text=":", font=FONT_B, text_color=_c.CURRENT_THEME["text"]).pack(side="left")
        self.e_proxy_port = ctk.CTkEntry(self.net, placeholder_text="7890", width=70, height=30, font=FONT_N, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        self.e_proxy_port.insert(0, ppt)
        self.e_proxy_port.pack(side="left", padx=(2, 10))
        ctk.CTkLabel(self.net, text="⚡并发:", font=FONT_S, text_color=_c.CURRENT_THEME["text"]).pack(side="left", padx=(15, 2))
        self.c_concurrent = ctk.CTkComboBox(self.net, values=["1", "2", "3", "4", "5"], width=60, state="readonly", command=lambda v: setattr(self, 'max_concurrent', int(v)), fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        self.c_concurrent.set("2")
        self.c_concurrent.pack(side="left")
        self.c_cookie = ctk.CTkComboBox(self.net, values=["🚫 No Cookie"], width=150, height=30, font=FONT_N, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        self.c_cookie.pack(side="right")
        if self.cfg["proxy_on"]:
            self.sw_proxy.select()

        self.browser_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.browser_frame.columnconfigure(0, weight=1)
        self.browser_frame.columnconfigure(1, weight=1)

        left_part = ctk.CTkFrame(self.browser_frame, fg_color="transparent")
        left_part.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        ctk.CTkLabel(left_part, text="🌐 浏览器 Cookie 授权", font=FONT_B, text_color=_c.CURRENT_THEME["text"], anchor="w").pack(fill="x")
        ctk.CTkLabel(left_part, text="选择已登录视频网站的浏览器以获取会员权限", font=FONT_S, text_color="gray", anchor="w").pack(fill="x")

        right_part = ctk.CTkFrame(self.browser_frame, fg_color="transparent")
        right_part.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        self.c_browser = ctk.CTkComboBox(
            right_part, values=["chrome", "firefox", "edge", "safari"],
            width=120, font=FONT_N, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"],
        )
        self.c_browser.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.c_cookie.configure(command=self.update_browser_selector)

        self.time_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.time_frame.pack(fill="x", padx=20, pady=5)
        self.switch_time = ctk.CTkSwitch(self.time_frame, text="✂️ 片段下载", font=FONT_N, progress_color=_c.CURRENT_THEME["accent"], text_color=_c.CURRENT_THEME["text"], command=self.upd_ui)
        self.switch_time.pack(side="left", padx=(0, 10))
        if self.cfg.get("time_range_on"):
            self.switch_time.select()
        self.cut_box = ctk.CTkFrame(self.time_frame, fg_color="transparent")

        def mk_time_entry(parent, val):
            e = ctk.CTkEntry(parent, width=30, height=25, font=FONT_S, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
            e.insert(0, val)
            return e

        self.e_start_h = mk_time_entry(self.cut_box, self.cfg.get("start_h", "00"))
        self.e_start_h.pack(side="left")
        ctk.CTkLabel(self.cut_box, text=":", text_color=_c.CURRENT_THEME["text"]).pack(side="left")
        self.e_start_m = mk_time_entry(self.cut_box, self.cfg.get("start_m", "00"))
        self.e_start_m.pack(side="left")
        ctk.CTkLabel(self.cut_box, text=":", text_color=_c.CURRENT_THEME["text"]).pack(side="left")
        self.e_start_s = mk_time_entry(self.cut_box, self.cfg.get("start_s", "00"))
        self.e_start_s.pack(side="left")
        ctk.CTkLabel(self.cut_box, text=" 至 ", font=FONT_S, text_color=_c.CURRENT_THEME["text"]).pack(side="left", padx=5)
        self.e_end_h = mk_time_entry(self.cut_box, self.cfg.get("end_h", "00"))
        self.e_end_h.pack(side="left")
        ctk.CTkLabel(self.cut_box, text=":", text_color=_c.CURRENT_THEME["text"]).pack(side="left")
        self.e_end_m = mk_time_entry(self.cut_box, self.cfg.get("end_m", "00"))
        self.e_end_m.pack(side="left")
        ctk.CTkLabel(self.cut_box, text=":", text_color=_c.CURRENT_THEME["text"]).pack(side="left")
        self.e_end_s = mk_time_entry(self.cut_box, self.cfg.get("end_s", "00"))
        self.e_end_s.pack(side="left")

        resume_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        resume_frame.pack(fill="x", padx=20, pady=5)
        self.btn_resume_manager = ctk.CTkButton(resume_frame, text="🔄 续传管理", height=30, font=FONT_N, fg_color="#FF6B6B", command=lambda: [self.on_interact(), self.open_resume_manager()])
        self.btn_resume_manager.pack(side="left", padx=(0, 10))
        self.resume_status_label = ctk.CTkLabel(resume_frame, text="无待续传任务", font=FONT_S, text_color="gray")
        self.resume_status_label.pack(side="left")
        self.after(5000, self.check_resume_status)

        bb = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        bb.pack(fill="x", padx=20, pady=15)
        bb.columnconfigure(0, weight=1)
        bb.columnconfigure(1, weight=1)
        bb.columnconfigure(2, weight=1)

        self.btn_add = ctk.CTkButton(bb, text="📥 放进篮子", height=50, font=FONT_B, fg_color=_c.CURRENT_THEME["btn_add_bg"], text_color=_c.CURRENT_THEME["btn_add_fg"], hover_color=_c.CURRENT_THEME["btn_add_bg"], command=lambda: [self.on_interact(), self.start_thread(self.smart_add_flow)])
        self.btn_add.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        self.btn_now = ctk.CTkButton(bb, text="⚡ 立即抓取", height=50, font=FONT_B, fg_color=_c.CURRENT_THEME["btn_now_bg"], text_color=_c.CURRENT_THEME["btn_now_fg"], hover_color=_c.CURRENT_THEME["btn_now_bg"], command=lambda: [self.on_interact(), self.start_thread(self.download_now_flow)])
        self.btn_now.grid(row=0, column=1, padx=5, sticky="ew")
        self.btn_start = ctk.CTkButton(bb, text="🚀 叼回窝里", height=50, font=FONT_B, fg_color=_c.CURRENT_THEME["btn_start_bg"], text_color=_c.CURRENT_THEME["btn_start_fg"], hover_color=_c.CURRENT_THEME["btn_start_bg"], command=lambda: [self.on_interact(), self.start_thread(self.process_queue)])
        self.btn_start.grid(row=0, column=2, padx=(5, 0), sticky="ew")

        self.l_status = ctk.CTkLabel(self.left_panel, text="呼噜呼噜… 待命中喵", font=FONT_S, text_color="gray")
        self.l_status.pack(pady=(0, 2))
        self.prog = ctk.CTkProgressBar(self.left_panel, progress_color=_c.CURRENT_THEME["accent"], height=12)
        self.prog.pack(fill="x", padx=20, pady=(0, 10))
        self.prog.set(0)
        self.log_box = ctk.CTkTextbox(self.left_panel, height=100, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"], font=FONT_LOG, state="disabled")
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        self.right_panel = ctk.CTkFrame(self.paned, fg_color=_c.CURRENT_THEME["secondary"], corner_radius=15)
        ctk.CTkLabel(self.right_panel, text="🛒 篮子里的小老鼠", font=FONT_B, text_color=_c.CURRENT_THEME["accent"]).pack(pady=10)
        self.scroll_q = ctk.CTkScrollableFrame(self.right_panel, fg_color="transparent")
        self.scroll_q.pack(fill="both", expand=True, padx=5, pady=(0, 10))
        self.upd_ui()
