import os
import json
import threading
import logging
from tkinter import messagebox

import customtkinter as ctk

from ..core.constants import FONT_N, FONT_B, FONT_T, FONT_S
from ..core import constants as _c

logger = logging.getLogger(__name__)


class ResumeManagerWindow(ctk.CTkToplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.title("🔄 续传管理")
        self.geometry("800x600")
        self.db = db
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=_c.CURRENT_THEME["main_bg"])
        self.parent = parent
        self.setup_ui()
        self.load_pending_sessions()

    def setup_ui(self):
        title_frame = ctk.CTkFrame(self, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(title_frame, text="🔄 断点续传管理", font=FONT_T, text_color=_c.CURRENT_THEME["accent"]).pack()

        control_frame = ctk.CTkFrame(self, fg_color="transparent")
        control_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(control_frame, text="🔄 全部续传", width=120, fg_color="#4CAF50", command=self.resume_all).pack(side="left", padx=(0, 10))
        ctk.CTkButton(control_frame, text="🗑️ 清理失效", width=120, fg_color="#FF9800", command=self.clean_invalid_sessions).pack(side="left", padx=5)
        ctk.CTkButton(control_frame, text="❌ 全部删除", width=120, fg_color="#F44336", command=self.delete_all).pack(side="left", padx=5)

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color=_c.CURRENT_THEME["panel_bg"])
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

    def load_pending_sessions(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        sessions = self.db.get_pending_resume_sessions()
        if not sessions:
            ctk.CTkLabel(self.scroll_frame, text="✨ 没有待续传的任务", font=FONT_N, text_color=_c.CURRENT_THEME["text"]).pack(pady=20)
            return
        for session in sessions:
            self.create_session_item(session)

    def create_session_item(self, session):
        item_frame = ctk.CTkFrame(self.scroll_frame, fg_color=_c.CURRENT_THEME["secondary"], corner_radius=10)
        item_frame.pack(fill="x", pady=5, padx=5)

        info_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=8)

        title_text = session[9] if len(session) > 9 and session[9] else session[1]
        if len(title_text) > 60:
            title_text = title_text[:60] + "..."
        url_label = ctk.CTkLabel(info_frame, text=title_text, font=FONT_B, text_color=_c.CURRENT_THEME["text"], anchor="w")
        url_label.pack(fill="x")

        downloaded = session[4] if session[4] else 0
        total = session[5] if session[5] else 0
        progress = (downloaded / total * 100) if total > 0 else 0
        progress_text = f"进度: {downloaded // 1024 // 1024}MB / {total // 1024 // 1024}MB ({progress:.1f}%)"
        if session[6]:
            progress_text += f" | 最后更新: {session[6][:16]}"
        progress_label = ctk.CTkLabel(info_frame, text=progress_text, font=FONT_S, text_color="gray", anchor="w")
        progress_label.pack(fill="x")

        progress_bar = ctk.CTkProgressBar(info_frame, progress_color=_c.CURRENT_THEME["accent"], height=8)
        progress_bar.pack(fill="x", pady=(5, 0))
        progress_bar.set(progress / 100)

        button_frame = ctk.CTkFrame(item_frame, fg_color="transparent")
        button_frame.pack(side="right", padx=10, pady=8)
        ctk.CTkButton(button_frame, text="▶️ 续传", width=80, height=30, fg_color="#4CAF50", command=lambda s=session: self.resume_session(s)).pack(pady=2)
        ctk.CTkButton(button_frame, text="❌ 删除", width=80, height=30, fg_color="#F44336", command=lambda s=session: self.delete_session(s)).pack(pady=2)

    def resume_session(self, session):
        try:
            download_params = json.loads(session[7]) if session[7] else {}
            if not os.path.exists(session[3]):
                pass
            threading.Thread(target=self.parent.start_resume_download, args=(session, download_params), daemon=True).start()
            self.destroy()
        except Exception as e:
            messagebox.showerror("续传失败", f"续传失败: {str(e)}")

    def delete_session(self, session):
        if messagebox.askyesno("确认删除", "确定要删除这个续传会话吗？"):
            try:
                if os.path.exists(session[3]):
                    os.remove(session[3])
                self.db.delete_resume_session(session[0])
                self.load_pending_sessions()
            except Exception as e:
                messagebox.showerror("删除失败", f"删除失败: {str(e)}")

    def resume_all(self):
        sessions = self.db.get_pending_resume_sessions()
        for session in sessions:
            self.resume_session(session)

    def clean_invalid_sessions(self):
        sessions = self.db.get_pending_resume_sessions()
        cleaned = 0
        for session in sessions:
            if not os.path.exists(session[3]):
                self.db.delete_resume_session(session[0])
                cleaned += 1
        if cleaned > 0:
            messagebox.showinfo("清理完成", f"已清理 {cleaned} 个失效会话")
            self.load_pending_sessions()
        else:
            messagebox.showinfo("清理完成", "没有发现失效会话")

    def delete_all(self):
        if messagebox.askyesno("确认删除", "确定要删除所有续传会话吗？这将删除所有临时下载文件。"):
            sessions = self.db.get_pending_resume_sessions()
            for session in sessions:
                try:
                    if os.path.exists(session[3]):
                        os.remove(session[3])
                except Exception:
                    pass
            self.db.delete_all_resume_sessions()
            self.load_pending_sessions()
