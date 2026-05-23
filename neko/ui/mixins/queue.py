import threading
import time
import logging

import customtkinter as ctk
import tkinter as tk

from ...core.constants import FONT_Q_TITLE, FONT_Q_DESC
from ...core.utils import safe_run, show_windows_toast
from ...core import constants as _c

logger = logging.getLogger(__name__)


class QueueMixin:
    """Download queue: add, edit, delete, process items."""

    def smart_add_flow(self):
        u = self.run_safe(lambda: self.e_url.get().strip())
        if not u:
            return
        if (u != self.last_analyzed_url) or (self.current_meta is None):
            self.perform_analysis(u)
            if "手动" in self.run_safe(self.seg_mode.get):
                self.log("Ready for manual selection...", "happy")
                return
        self.add_to_queue_internal()

    def add_to_queue_internal(self):
        def _add():
            if not self.current_meta:
                return
            cfg, desc = self.build_current_config()
            if len(self.queue_items) == 0:
                self.paned.add(self.right_panel, minsize=320, stretch="always")

            item = ctk.CTkFrame(self.scroll_q, fg_color=_c.CURRENT_THEME["panel_bg"], corner_radius=10)
            item.pack(fill="x", pady=5)
            img = ctk.CTkImage(self.current_thumb_img._light_image, size=(80, 45)) if self.current_thumb_img else None
            ctk.CTkLabel(item, text="", image=img, width=80).pack(side="left", padx=5, pady=5)
            tf = ctk.CTkFrame(item, fg_color="transparent")
            tf.pack(side="left", fill="both", expand=True, padx=5)
            ctk.CTkLabel(tf, text=self.current_meta.get('title', '?'), font=FONT_Q_TITLE, anchor="w", text_color=_c.CURRENT_THEME["text"]).pack(fill="x", expand=True)
            dl = ctk.CTkLabel(tf, text=desc, font=FONT_Q_DESC, text_color="gray", anchor="w")
            dl.pack(fill="x", expand=True)
            lbl = ctk.CTkLabel(item, text="Queued", font=("微软雅黑", 10), text_color="gray")
            lbl.pack(side="right", padx=10)

            pkt = {"config": cfg, "label": lbl, "desc_label": dl, "status": "waiting", "meta": self.current_meta, "widget": item}
            self.queue_items.append(pkt)

            def pop(e):
                m = tk.Menu(self, tearoff=0)
                m.add_command(label="✏️ Edit", command=lambda: self.edit_queue_item(pkt))
                m.add_command(label="🗑️ Delete", command=lambda: self.delete_queue_item(pkt))
                m.tk_popup(e.x_root, e.y_root)

            def rb(w):
                w.bind("<Button-3>", pop)
                [rb(c) for c in w.winfo_children()]

            rb(item)
            self.log(f"Added: {self.current_meta.get('title', '?')[:15]}...", "done")

        self.run_safe(_add)

    def delete_queue_item(self, i):
        if i in self.queue_items:
            self.queue_items.remove(i)
            i['widget'].destroy()
            self.log("Deleted.", "sad")

    def edit_queue_item(self, i):
        from ..dialogs import TaskEditWindow

        def save(o, n):
            o['config'] = n
            o['desc_label'].configure(text="Edited")
            self.log("Task updated.", "happy")
        TaskEditWindow(self, i, save)

    def process_queue(self):
        q = [i for i in self.queue_items if i['status'] == 'waiting']
        if not q:
            self.log("篮子空空的喵…", "sad")
            return
        self.run_safe(lambda: [self.btn_add.configure(state="disabled"), self.btn_start.configure(state="disabled")])
        self.log(f"Processing {len(q)} items...", "working")
        sem = threading.Semaphore(self.max_concurrent)
        ths = []
        for i, it in enumerate(q):
            t = threading.Thread(target=self._dw, args=(it, sem), daemon=True)
            t.start()
            ths.append(t)
        for t in ths:
            t.join()
        self.run_safe(lambda: [self.btn_add.configure(state="normal"), self.btn_start.configure(state="normal"), self.l_status.configure(text="Finished")])
        self.log("全部叼回窝里啦喵！", "done")
        show_windows_toast("Neko", "Queue finished!")
        self.mood_manager.interact()
        self.mood_manager.update_logic()
        self.update_mood_display()

    @safe_run
    def _dw(self, it, sem):
        with sem:
            self.run_safe(lambda: it['label'].configure(text="Running", text_color="orange"))
            it['status'] = 'running'

            cfg = it['config']
            session_id = self.generate_session_id(cfg['url'], cfg['dir'])
            temp_file = self.find_current_temp_file(cfg, it['meta'])
            session_dict = None
            if temp_file:
                session_dict = {
                    'session_id': session_id, 'url': cfg['url'],
                    'output_path': cfg['dir'], 'temp_file': temp_file,
                }

            ok = self.download_item_with_resume(cfg, it['meta'], session_dict)

            c, t = ("green", "Done") if ok else ("red", "Error")
            self.run_safe(lambda: it['label'].configure(text=t, text_color=c))
            it['status'] = 'done' if ok else 'error'
            if ok:
                self.mood_manager.download_success_today += 1
