"""Small dialog windows: ThemeEditor, Settings, SponsorSelect, BatchUrl,
TemplateEditor, ChatFilter, TaskEdit."""

import sys
import os
import shutil
import webbrowser
from tkinter import messagebox, colorchooser, filedialog

import customtkinter as ctk

from ..core.constants import (
    FONT_N, FONT_B, FONT_S, FONT_LOG,
    DEFAULT_PRESETS, BASE_THEME_TEMPLATE,
)
from ..core import constants as _c
from ..core.theme import ThemeManager


# ═══════════════════════════════════════════════════════════════
#  ThemeEditorWindow
# ═══════════════════════════════════════════════════════════════

class ThemeEditorWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("🎨 魔法调色板 (Theme Editor)")
        self.geometry("550x750")
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=_c.CURRENT_THEME["main_bg"])
        self.after(10, self._create_widgets)

    def _create_widgets(self):
        theme_manager = ThemeManager()

        self.presets = theme_manager.get_all_presets()
        self.active_name = "猫娘粉 (Neko Pink)"
        for name in self.presets:
            if theme_manager.load_preset(name) == _c.CURRENT_THEME:
                self.active_name = name
                break

        top_f = ctk.CTkFrame(self, fg_color="transparent")
        top_f.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(top_f, text="选择主题:", font=FONT_B, text_color=_c.CURRENT_THEME["text"]).pack(side="left")
        self.c_theme = ctk.CTkComboBox(
            top_f, values=self.presets, width=220, font=FONT_N,
            command=self.on_theme_select,
            text_color=_c.CURRENT_THEME["text"], fg_color=_c.CURRENT_THEME["panel_bg"],
        )
        self.c_theme.pack(side="left", padx=10)
        self.c_theme.set(self.active_name)

        save_f = ctk.CTkFrame(self, fg_color="transparent")
        save_f.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(save_f, text="另存为新名:", font=FONT_N, text_color=_c.CURRENT_THEME["text"]).pack(side="left")
        self.e_new_name = ctk.CTkEntry(
            save_f, width=200, placeholder_text="输入名字以新建...",
            text_color=_c.CURRENT_THEME["text"], fg_color=_c.CURRENT_THEME["panel_bg"],
        )
        self.e_new_name.pack(side="left", padx=10)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color=_c.CURRENT_THEME["panel_bg"])
        self.scroll.pack(fill="both", expand=True, padx=20, pady=5)

        ctk.CTkLabel(self.scroll, text="--- 🌏 全局基础色 ---", font=FONT_B, text_color=_c.CURRENT_THEME["accent"]).pack(pady=5)
        self.create_color_row("主题模式 (Mode)", "mode_switch")
        self.create_color_row("主背景色 (Main BG)", "main_bg")
        self.create_color_row("面板背景 (Panel BG)", "panel_bg")
        self.create_color_row("卡片背景 (Card BG)", "secondary")
        self.create_color_row("文字颜色 (Text)", "text")
        self.create_color_row("强调色 (Accent)", "accent")

        ctk.CTkLabel(self.scroll, text="--- 🔘 核心按钮自定义 ---", font=FONT_B, text_color=_c.CURRENT_THEME["accent"]).pack(pady=(15, 5))
        self.create_color_row("📥 放进篮子 (背景)", "btn_add_bg")
        self.create_color_row("📥 放进篮子 (文字)", "btn_add_fg")
        self.create_color_row("⚡ 立即抓取 (背景)", "btn_now_bg")
        self.create_color_row("⚡ 立即抓取 (文字)", "btn_now_fg")
        self.create_color_row("🚀 叼回窝里 (背景)", "btn_start_bg")
        self.create_color_row("🚀 叼回窝里 (文字)", "btn_start_fg")

        self._theme_manager = theme_manager
        self.load_to_editor(self.active_name)

        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(pady=20)
        ctk.CTkButton(btn_f, text="💾 保存并重启", fg_color=_c.CURRENT_THEME["accent"], width=150, font=FONT_B, command=self.save_theme).pack()

    def create_color_row(self, label, key):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(fill="x", padx=5, pady=4)
        ctk.CTkLabel(row, text=label, font=FONT_N, width=160, anchor="w", text_color=_c.CURRENT_THEME["text"]).pack(side="left")
        if key == "mode_switch":
            self.seg_mode = ctk.CTkSegmentedButton(
                row, values=["Light", "Dark"],
                selected_color=_c.CURRENT_THEME["accent"], text_color=_c.CURRENT_THEME["text"],
            )
            self.seg_mode.pack(side="right", fill="x", expand=True)
        else:
            preview = ctk.CTkLabel(row, text="", width=40, height=24, fg_color="#FFFFFF", corner_radius=5)
            preview.pack(side="right", padx=5)
            ctk.CTkButton(
                row, text="🎨", width=40, height=24,
                fg_color=_c.CURRENT_THEME["accent"],
                command=lambda: self.pick_color(key, preview),
            ).pack(side="right")
            setattr(self, f"preview_{key}", preview)
            setattr(self, f"val_{key}", "#FFFFFF")

    def load_to_editor(self, theme_name):
        data = self._theme_manager.load_preset(theme_name)
        if hasattr(self, "seg_mode"):
            self.seg_mode.set(data.get("mode", "Light"))
        all_keys = [k for k in BASE_THEME_TEMPLATE if k != "mode"]
        for key in all_keys:
            if hasattr(self, f"preview_{key}"):
                color = data.get(key, "#FFFFFF")
                getattr(self, f"preview_{key}").configure(fg_color=color)
                setattr(self, f"val_{key}", color)

    def on_theme_select(self, choice):
        self.e_new_name.delete(0, "end")
        self.load_to_editor(choice)

    def pick_color(self, key, preview_widget):
        curr = getattr(self, f"val_{key}")
        color = colorchooser.askcolor(initialcolor=curr, title=f"Color: {key}")
        if color[1]:
            preview_widget.configure(fg_color=color[1])
            setattr(self, f"val_{key}", color[1])

    def save_theme(self):
        # Start from the full current preset (preserves MD3 keys not exposed in editor)
        new_data = self._theme_manager.load_preset(self.c_theme.get()).copy()
        new_data["mode"] = self.seg_mode.get()
        # Only overwrite keys that have color pickers in the editor
        for k in BASE_THEME_TEMPLATE:
            if k == "mode":
                continue
            if hasattr(self, f"val_{k}"):
                new_data[k] = getattr(self, f"val_{k}")

        target_name = self.e_new_name.get().strip()
        if not target_name:
            target_name = self.c_theme.get()

        if target_name in DEFAULT_PRESETS and target_name == self.c_theme.get() and new_data != DEFAULT_PRESETS[target_name]:
            if not messagebox.askyesno("修改内置预设", f"'{target_name}' 是内置预设，修改它将自动保存为新文件。\n是否继续？"):
                return

        if self._theme_manager.save_preset(target_name, new_data):
            self._theme_manager.set_active_theme_record(target_name)
            if messagebox.askyesno("保存成功", f"主题 '{target_name}' 已保存！\n需要重启生效，立即重启？"):
                from ..core.process import popen_text
                popen_text([sys.executable, "-m", "neko.main"], cwd=os.getcwd())
                sys.exit(0)
            else:
                self.destroy()


# ═══════════════════════════════════════════════════════════════
#  SettingsWindow
# ═══════════════════════════════════════════════════════════════

class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("⚙️ 设置")
        self.geometry("600x350")
        self.callback = callback
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=_c.CURRENT_THEME["main_bg"])

        ctk.CTkLabel(self, text="🔧 路径配置", font=FONT_B, text_color=_c.CURRENT_THEME["accent"]).pack(pady=10)
        self.mk_path_row("yt-dlp.exe:", "ytdlp", "https://github.com/yt-dlp/yt-dlp/releases", parent.cfg.get('ytdlp_path', ''))
        self.mk_path_row("ffmpeg bin:", "ffmpeg", "https://www.gyan.dev/ffmpeg/builds/", parent.cfg.get('ffmpeg_path', ''), is_dir=True)

        btn_box = ctk.CTkFrame(self, fg_color="transparent")
        btn_box.pack(pady=20)
        ctk.CTkButton(btn_box, text="💾 保存", fg_color=_c.CURRENT_THEME["accent"], command=self.save).pack(side="left", padx=10)
        ctk.CTkButton(btn_box, text="❌ 取消", fg_color=_c.CURRENT_THEME["surface_variant"], command=self.destroy).pack(side="left", padx=10)

    def mk_path_row(self, lbl, key, url, val, is_dir=False):
        f = ctk.CTkFrame(self, fg_color="transparent")
        f.pack(fill="x", padx=20, pady=10)
        t = ctk.CTkFrame(f, fg_color="transparent")
        t.pack(fill="x")
        ctk.CTkLabel(t, text=lbl, width=100, anchor="w", text_color=_c.CURRENT_THEME["text"]).pack(side="left")
        ctk.CTkButton(t, text="⬇️ 下载", width=60, height=20, fg_color=_c.CURRENT_THEME["secondary_container"], text_color=_c.CURRENT_THEME["on_secondary_container"], command=lambda: webbrowser.open(url)).pack(side="right")
        b = ctk.CTkFrame(f, fg_color="transparent")
        b.pack(fill="x", pady=2)
        e = ctk.CTkEntry(b, width=350, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        e.pack(side="left", padx=5)
        setattr(self, f"e_{key}", e)
        sys_path = shutil.which("ffmpeg" if "ffmpeg" in key else "yt-dlp")
        cmd = self.browse_dir if is_dir else self.browse_file
        btn = ctk.CTkButton(b, text="📂", width=50, command=lambda: cmd(e), fg_color=_c.CURRENT_THEME["accent"])
        btn.pack(side="left")
        if sys_path:
            e.insert(0, sys_path)
            e.configure(state="disabled")
            btn.configure(state="disabled")
            ctk.CTkLabel(b, text="✅ 系统环境", text_color=_c.CURRENT_THEME["tertiary"]).pack(side="left", padx=5)
        else:
            e.insert(0, val)

    def browse_file(self, e):
        f = filedialog.askopenfilename(filetypes=[("Executables", "*.exe"), ("All", "*.*")])
        if f:
            e.delete(0, "end")
            e.insert(0, f)

    def browse_dir(self, e):
        d = filedialog.askdirectory()
        if d:
            e.delete(0, "end")
            e.insert(0, d)

    def save(self):
        self.callback(self.e_ytdlp.get(), self.e_ffmpeg.get())
        self.destroy()


# ═══════════════════════════════════════════════════════════════
#  SponsorSelectWindow
# ═══════════════════════════════════════════════════════════════

class SponsorSelectWindow(ctk.CTkToplevel):
    def __init__(self, parent, current_cats, callback):
        super().__init__(parent)
        self.title("🍽️ 挑食菜单")
        self.geometry("450x550")
        self.callback = callback
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=_c.CURRENT_THEME["main_bg"])

        self.cats_map = {
            "all": "🌐 全部一口吞 (All)", "sponsor": "💰 恰饭广告 (Sponsor)",
            "selfpromo": "🗣️ 自卖自夸 (Self Promo)", "intro": "🎞️ 啰嗦片头 (Intro)",
            "outro": "🎬 啰嗦片尾 (Outro)", "intermission": "🚻 中场尿点 (Intermission)",
            "preview": "🔍 剧透预告 (Preview)", "filler": "💤 水时长 (Filler)",
            "music_offtopic": "🎶 乱放BGM (Music Offtopic)",
        }
        self.vars = {}

        ctk.CTkLabel(self, text="主人喵~ 不想吃哪几段？", font=FONT_B, text_color=_c.CURRENT_THEME["accent"]).pack(pady=15)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=5)

        self.all_var = ctk.CTkCheckBox(
            scroll, text=self.cats_map["all"],
            font=FONT_N, border_color=_c.CURRENT_THEME["accent"],
            fg_color=_c.CURRENT_THEME["accent"],
            command=self.on_all_click, text_color=_c.CURRENT_THEME["text"],
        )
        if "all" in current_cats:
            self.all_var.select()
        self.all_var.pack(anchor="w", pady=5)
        self.vars["all"] = self.all_var

        ctk.CTkFrame(scroll, height=2, fg_color=_c.CURRENT_THEME["outline_variant"]).pack(fill="x", pady=10)

        for key, label in self.cats_map.items():
            if key == "all":
                continue
            v = ctk.CTkCheckBox(
                scroll, text=label, font=FONT_N,
                border_color=_c.CURRENT_THEME["primary"], fg_color=_c.CURRENT_THEME["primary"],
                command=lambda k=key: self.on_item_click(k),
                text_color=_c.CURRENT_THEME["text"],
            )
            if (key in current_cats) and ("all" not in current_cats):
                v.select()
            v.pack(anchor="w", pady=5)
            self.vars[key] = v

        ctk.CTkButton(self, text="👌 就这么定了", fg_color=_c.CURRENT_THEME["accent"], width=150, font=FONT_B, command=self.confirm).pack(pady=20)

    def on_all_click(self):
        if self.all_var.get():
            for k, v in self.vars.items():
                if k != "all":
                    v.deselect()

    def on_item_click(self, key):
        if self.vars[key].get():
            self.all_var.deselect()

    def confirm(self):
        s = ["all"] if self.all_var.get() else [k for k, v in self.vars.items() if k != "all" and v.get()]
        self.callback(s if s else ["all"])
        self.destroy()


# ═══════════════════════════════════════════════════════════════
#  BatchUrlWindow
# ═══════════════════════════════════════════════════════════════

class BatchUrlWindow(ctk.CTkToplevel):
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("📚 批量喂食")
        self.geometry("600x500")
        self.callback = callback
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=_c.CURRENT_THEME["main_bg"])

        ctk.CTkLabel(self, text="请把链接统统贴在这里 (一行一个) 喵！👇", font=FONT_B, text_color=_c.CURRENT_THEME["accent"]).pack(pady=15)
        self.txt_urls = ctk.CTkTextbox(self, font=FONT_LOG, width=550, height=350, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        self.txt_urls.pack(pady=5)

        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(pady=15)
        ctk.CTkButton(btn_f, text="❌ 算了", fg_color=_c.CURRENT_THEME["surface_variant"], width=100, command=self.destroy).pack(side="left", padx=10)
        ctk.CTkButton(btn_f, text="✅ 全部吞掉", fg_color=_c.CURRENT_THEME["accent"], width=150, font=FONT_B, command=self.confirm).pack(side="left", padx=10)

    def confirm(self):
        c = self.txt_urls.get("1.0", "end").strip()
        if not c:
            self.destroy()
            return
        self.callback([l.strip() for l in c.split('\n') if l.strip()])
        self.destroy()


# ═══════════════════════════════════════════════════════════════
#  TemplateEditorWindow
# ═══════════════════════════════════════════════════════════════

class TemplateEditorWindow(ctk.CTkToplevel):
    def __init__(self, parent, tmpl_on, current_tmpl, callback):
        super().__init__(parent)
        self.title("🏷️ 命名模板")
        self.geometry("600x600")
        self.callback = callback
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=_c.CURRENT_THEME["main_bg"])

        ctk.CTkLabel(self, text="主人喵~ 想怎么给猎物取名？", font=FONT_B, text_color=_c.CURRENT_THEME["accent"]).pack(pady=15)

        self.sw_on = ctk.CTkSwitch(self, text="启用自定义重命名", font=FONT_N, progress_color=_c.CURRENT_THEME["accent"], text_color=_c.CURRENT_THEME["text"])
        self.sw_on.pack(pady=5)
        if tmpl_on:
            self.sw_on.select()

        self.e_tmpl = ctk.CTkEntry(self, font=FONT_LOG, width=500, height=40, fg_color=_c.CURRENT_THEME["panel_bg"], text_color=_c.CURRENT_THEME["text"])
        self.e_tmpl.insert(0, current_tmpl)
        self.e_tmpl.pack(pady=10)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", width=550, height=350)
        scroll.pack(pady=10)

        tags = [
            ("📄 标题", "%(title)s"), ("👤 UP主", "%(uploader)s"),
            ("📅 日期", "%(upload_date)s"), ("🆔 视频ID", "%(id)s"),
            ("📺 频道名", "%(channel)s"), ("🔢 列表序号", "%(playlist_index)s"),
            ("⏱️ 时长", "%(duration)s"), ("📐 分辨率", "%(resolution)s"),
            ("📂 原文件名", "%(original_filename)s"),
        ]
        for i, (t, v) in enumerate(tags):
            ctk.CTkButton(scroll, text=t, font=FONT_N, fg_color=_c.CURRENT_THEME["secondary_container"], text_color=_c.CURRENT_THEME["on_secondary_container"], command=lambda v=v: self.e_tmpl.insert("end", v)).grid(row=i // 2, column=i % 2, padx=10, pady=5, sticky="ew")
        scroll.columnconfigure(0, weight=1)
        scroll.columnconfigure(1, weight=1)

        btn_box = ctk.CTkFrame(self, fg_color="transparent")
        btn_box.pack(pady=10)
        ctk.CTkButton(btn_box, text="💾 保存", fg_color=_c.CURRENT_THEME["accent"], command=self.save).pack(side="left", padx=10)

    def save(self):
        t = self.e_tmpl.get().strip()
        self.callback(self.sw_on.get(), t if t else "%(title)s")
        self.destroy()


# ═══════════════════════════════════════════════════════════════
#  ChatFilterSelector
# ═══════════════════════════════════════════════════════════════

class ChatFilterSelector(ctk.CTkToplevel):
    def __init__(self, parent, current_filters, callback):
        super().__init__(parent)
        self.title("💬 聊天室筛选器")
        self.geometry("400x500")
        self.callback = callback
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=_c.CURRENT_THEME["main_bg"])

        ctk.CTkLabel(self, text="🔎 请选择要保留的成分", font=FONT_B, text_color=_c.CURRENT_THEME["accent"]).pack(pady=15)

        self.fields = {
            "author": "👤 发言人 (Author)", "message": "💬 弹幕内容 (Message)",
            "timestamp": "⏱️ 时间戳 (Timestamp)", "money": "💰 投喂金额 (SuperChat)",
            "badges": "🏅 徽章/头衔 (Badges)",
        }

        self.vars = {}
        for k, v in self.fields.items():
            val = ctk.CTkCheckBox(
                self, text=v, font=FONT_N,
                text_color=_c.CURRENT_THEME["text"],
                border_color=_c.CURRENT_THEME["accent"],
                fg_color=_c.CURRENT_THEME["accent"],
            )
            if k in current_filters:
                val.select()
            val.pack(anchor="w", padx=40, pady=10)
            self.vars[k] = val

        btn_f = ctk.CTkFrame(self, fg_color="transparent")
        btn_f.pack(pady=20)
        ctk.CTkButton(btn_f, text="✅ 确认", fg_color=_c.CURRENT_THEME["accent"], command=self.confirm).pack()

    def confirm(self):
        selected = [k for k, v in self.vars.items() if v.get()]
        if not selected:
            selected = ["author", "message"]
        self.callback(selected)
        self.destroy()


# ═══════════════════════════════════════════════════════════════
#  TaskEditWindow
# ═══════════════════════════════════════════════════════════════

class TaskEditWindow(ctk.CTkToplevel):
    def __init__(self, parent, item_data, on_save):
        super().__init__(parent)
        self.title("✏️ 任务编辑")
        self.geometry("600x700")
        self.item_data = item_data
        self.on_save = on_save
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=_c.CURRENT_THEME["main_bg"])

        cfg = item_data['config']
        meta = item_data.get('meta', {})

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=5)

        ctk.CTkLabel(scroll, text="模式:", font=FONT_B, text_color=_c.CURRENT_THEME["text"]).pack(anchor="w")
        self.seg_mode = ctk.CTkSegmentedButton(
            scroll,
            values=["最佳喵 (Auto)", "手动挑选 (Manual)", "直播蹲守 (Live)", "只要声音 (MP3)", "只要小纸条 (字幕)", "只抓聊天室 (Chat)"],
            selected_color=_c.CURRENT_THEME["accent"], command=self.upd_ui,
        )
        self.seg_mode.pack(fill="x", pady=5)
        self.seg_mode.set(cfg['mode'])

        self.fmt_frame = ctk.CTkFrame(scroll, fg_color=_c.CURRENT_THEME["panel_bg"])
        self.c_video = ctk.CTkComboBox(self.fmt_frame, width=400, command=self.on_video_change)
        self.c_video.pack(pady=5)
        self.c_audio = ctk.CTkComboBox(self.fmt_frame, width=400)
        self.c_audio.pack(pady=5)
        self.video_infos = {}
        self.populate_formats(meta, cfg)

        self.chat_frame = ctk.CTkFrame(scroll, fg_color=_c.CURRENT_THEME["panel_bg"])
        ctk.CTkLabel(self.chat_frame, text="主人喵~ 聊天记录要怎么处理？", font=FONT_S, text_color=_c.CURRENT_THEME["text"]).pack(anchor="w", padx=5, pady=2)
        self.chat_mode_full = ctk.CTkRadioButton(
            self.chat_frame, text="全部完整记录 (Raw JSON)", font=FONT_N,
            text_color=_c.CURRENT_THEME["text"], fg_color=_c.CURRENT_THEME["accent"],
            command=lambda: self.set_chat_mode("full"),
        )
        self.chat_mode_full.pack(anchor="w", padx=10, pady=5)
        self.chat_mode_filter = ctk.CTkRadioButton(
            self.chat_frame, text="精简筛选 (Filter JSON)", font=FONT_N,
            text_color=_c.CURRENT_THEME["text"], fg_color=_c.CURRENT_THEME["accent"],
            command=lambda: self.set_chat_mode("filter"),
        )
        self.chat_mode_filter.pack(anchor="w", padx=10, pady=5)

        self._chat_mode = cfg.get("chat_mode", "full")
        if self._chat_mode == "full":
            self.chat_mode_full.select()
        else:
            self.chat_mode_filter.select()

        self.btn_chat_filter = ctk.CTkButton(self.chat_frame, text="⚙️ 选择保留项...", width=150, fg_color=_c.CURRENT_THEME["secondary_container"], text_color=_c.CURRENT_THEME["on_secondary_container"], command=self.open_filter_selector)
        self.chat_filters = cfg.get("chat_filters", ["author", "message", "timestamp"])

        self.sw_embed = ctk.CTkSwitch(scroll, text="硬塞字幕", font=FONT_N, progress_color=_c.CURRENT_THEME["accent"], text_color=_c.CURRENT_THEME["text"])
        self.sw_embed.pack(pady=10)
        if cfg.get('embed'):
            self.sw_embed.select()

        self.upd_ui()
        ctk.CTkButton(self, text="保存", fg_color=_c.CURRENT_THEME["accent"], command=self.save).pack(pady=10)

    def set_chat_mode(self, mode):
        self._chat_mode = mode

    def populate_formats(self, meta, cfg):
        if 'formats' not in meta:
            self.c_video.configure(values=["No Video"])
            self.c_audio.configure(values=["No Audio"])
            return

        v_list, a_list = [], []
        self.video_infos = {}

        for f in meta['formats']:
            fid = f.get('format_id')
            if not fid:
                continue

            if f.get('vcodec') and f.get('vcodec') != 'none':
                h = f.get('height', 0) or 0
                br = f.get('tbr') or f.get('vbr') or 0
                vc = f.get('vcodec', '')
                ac = f.get('acodec', 'none')
                ext = f.get('ext', '')
                has_audio = (ac and ac != 'none')
                label = f"{h}P | {ext} | {vc} | {int(br)}k"
                if has_audio:
                    label += " | 🔊"
                label += f" | ID:{fid}"
                v_list.append({'h': h, 'br': br, 'label': label, 'id': fid, 'has_audio': has_audio})
                self.video_infos[label] = {'has_audio': has_audio, 'id': fid}

            if f.get('acodec') and f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                abr = f.get('abr', 0) or 0
                ac = f.get('acodec', '')
                ext = f.get('ext', '')
                label = f"{int(abr)}k | {ext} | {ac} | ID:{fid}"
                a_list.append({'abr': abr, 'label': label, 'id': fid})

        v_list.sort(key=lambda x: (x['h'], x['br']), reverse=True)
        a_list.sort(key=lambda x: x['abr'], reverse=True)

        v_labels = [x['label'] for x in v_list]
        a_labels = [x['label'] for x in a_list]

        self.c_video.configure(values=v_labels if v_labels else ["No Video"])
        self.c_audio.configure(values=a_labels if a_labels else ["No Audio"])

        curr_vid = cfg.get('v_id')
        if curr_vid:
            for x in v_labels:
                if x.endswith(f"ID:{curr_vid}"):
                    self.c_video.set(x)
                    break
        elif v_labels:
            self.c_video.set(v_labels[0])

        curr_aid = cfg.get('a_id')
        if curr_aid:
            for x in a_labels:
                if x.endswith(f"ID:{curr_aid}"):
                    self.c_audio.set(x)
                    break
        elif a_labels:
            self.c_audio.set(a_labels[0])

        self.on_video_change(self.c_video.get())

    def on_video_change(self, choice):
        info = self.video_infos.get(choice)
        if info and info['has_audio']:
            self.c_audio.configure(state="disabled")
        else:
            self.c_audio.configure(state="normal")

    def upd_ui(self, _=None):
        m = self.seg_mode.get()
        if "手动" in m:
            self.fmt_frame.pack(fill="x", pady=5, after=self.seg_mode)
        else:
            self.fmt_frame.pack_forget()
        if "聊天室" in m:
            self.chat_frame.pack(fill="x", pady=5, after=self.seg_mode)
            self.upd_chat_ui()
        else:
            self.chat_frame.pack_forget()

    def get_filter_text(self):
        if not self.chat_filters:
            return "⚙️ 选择保留项..."
        display = ", ".join([f.capitalize() for f in self.chat_filters])
        if len(display) > 20:
            display = display[:20] + "..."
        return f"⚙️ 选择保留项... ({display})"

    def upd_chat_ui(self):
        if self._chat_mode == "filter":
            self.btn_chat_filter.configure(text=self.get_filter_text())
            self.btn_chat_filter.pack(pady=5, padx=30, anchor="w")
        else:
            self.btn_chat_filter.pack_forget()

    def open_filter_selector(self):
        ChatFilterSelector(self, self.chat_filters, self.set_filters)

    def set_filters(self, filters):
        self.chat_filters = filters
        self.upd_chat_ui()

    def save(self):
        new = self.item_data['config'].copy()
        new['mode'] = self.seg_mode.get()
        new['embed'] = self.sw_embed.get()
        if "手动" in new['mode']:
            new['v_id'] = self.c_video.get().split("ID:")[-1] if "ID:" in self.c_video.get() else None
            if self.c_audio.cget("state") == "normal":
                new['a_id'] = self.c_audio.get().split("ID:")[-1] if "ID:" in self.c_audio.get() else None
            else:
                new['a_id'] = None
        if "聊天室" in new['mode']:
            new['chat_mode'] = self._chat_mode
            new['chat_filters'] = self.chat_filters
        self.on_save(self.item_data, new)
        self.destroy()
