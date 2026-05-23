import threading
import logging
import time

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from ...core.constants import FONT_Q_TITLE, FONT_Q_DESC
from ...core.utils import safe_run, show_windows_toast
from ...core import constants as _c
from .scheduler import TaskScheduler

logger = logging.getLogger(__name__)


class QueueMixin:
    """Download queue: add, edit, delete, cancel, process items."""

    # ── Add / Edit / Delete ─────────────────────────────────────

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
                if pkt['status'] in ('running', 'waiting'):
                    m.add_command(label="❌ 取消此任务", command=lambda: self.cancel_task(pkt))
                m.add_command(label="✏️ Edit", command=lambda: self.edit_queue_item(pkt))
                m.add_command(label="🗑️ Delete", command=lambda: self.delete_queue_item(pkt))
                m.tk_popup(e.x_root, e.y_root)

            def rb(w):
                w.bind("<Button-3>", pop)
                [rb(c) for c in w.winfo_children()]

            rb(item)
            self.log(f"Added: {self.current_meta.get('title', '?')[:15]}...", "done")
            self._save_queue()

        self.run_safe(_add)

    def delete_queue_item(self, i):
        if i in self.queue_items:
            if i['status'] == 'running':
                self.cancel_task(i)
            self.queue_items.remove(i)
            i['widget'].destroy()
            self.log("Deleted.", "sad")
            self._save_queue()

    def edit_queue_item(self, i):
        from ..dialogs import TaskEditWindow

        def save(o, n):
            o['config'] = n
            o['desc_label'].configure(text="Edited")
            self.log("Task updated.", "happy")
        TaskEditWindow(self, i, save)

    # ── Cancel ──────────────────────────────────────────────────

    def cancel_task(self, pkt):
        """Cancel a single task. Kills its subprocess if running."""
        if pkt['status'] not in ('running', 'waiting'):
            return
        sched = getattr(self, '_scheduler', None)
        if sched:
            sched.cancel_task(pkt)
        pkt['status'] = 'cancelled'
        self.run_safe(lambda: pkt['label'].configure(text="Cancelled", text_color="gray"))
        self.log("任务已取消", "sad")

    def cancel_queue(self):
        """Cancel all running and waiting tasks."""
        sched = getattr(self, '_scheduler', None)
        if not sched:
            return
        sched.cancel_all()
        for it in self.queue_items:
            if it['status'] in ('running', 'waiting'):
                it['status'] = 'cancelled'
                self.run_safe(lambda p=it: p['label'].configure(text="Cancelled", text_color="gray"))
        self.log("队列已全部取消", "sad")
        self._on_queue_finished()

    # ── Process queue (non-blocking) ───────────────────────────

    def process_queue(self):
        q = [i for i in self.queue_items if i['status'] == 'waiting']
        if not q:
            self.log("篮子空空的喵…", "sad")
            return

        self.run_safe(lambda: [
            self.btn_add.configure(state="disabled"),
            self.btn_start.configure(state="disabled"),
            self.btn_cancel_queue.configure(state="normal"),
        ])
        self.log(f"Processing {len(q)} items...", "working")

        self._scheduler = TaskScheduler(
            max_workers=self.max_concurrent,
            ui_callback=self._on_task_event,
            done_callback=self._on_queue_finished,
            after_fn=self.after,
        )
        self._scheduler.start_polling(self)

        for it in q:
            it['status'] = 'running'
            self._scheduler.submit(it, self._worker_task, it)

    def _worker_task(self, task_id, it):
        """Runs on a worker thread. Pushes events to the scheduler queue."""
        sched = self._scheduler

        if sched.is_task_cancelled(task_id):
            sched.push_event(task_id, "status", {"state": "cancelled"})
            return

        sched.push_event(task_id, "status", {"state": "running"})

        cfg = it['config']
        session_id = self.generate_session_id(cfg['url'], cfg['dir'])
        temp_file = self.find_current_temp_file(cfg, it['meta'])
        session_dict = None
        if temp_file:
            session_dict = {
                'session_id': session_id, 'url': cfg['url'],
                'output_path': cfg['dir'], 'temp_file': temp_file,
            }

        # Store task pkt reference so download engine can register its Popen
        self._current_task_pkt = task_id
        ok = self.download_item_with_resume(cfg, it['meta'], session_dict)
        self._current_task_pkt = None

        if sched.is_task_cancelled(task_id):
            sched.push_event(task_id, "status", {"state": "cancelled"})
        elif ok:
            sched.push_event(task_id, "status", {"state": "done"})
            self.mood_manager.download_success_today += 1
        else:
            sched.push_event(task_id, "status", {"state": "error"})

    def _on_task_event(self, evt):
        """Called on the main thread for each event from a worker."""
        pkt = evt.task_id  # the queue item dict
        if evt.kind == "status":
            state = evt.data.get("state", "")
            if state == "running":
                pkt['label'].configure(text="Running", text_color="orange")
            elif state == "done":
                pkt['label'].configure(text="Done", text_color="green")
                pkt['status'] = 'done'
                self._save_queue()
            elif state == "error":
                pkt['label'].configure(text="Error", text_color="red")
                pkt['status'] = 'error'
                self._save_queue()
            elif state == "cancelled":
                pkt['label'].configure(text="Cancelled", text_color="gray")
                pkt['status'] = 'cancelled'
                self._save_queue()

    def _on_queue_finished(self):
        """Called on the main thread when all tasks complete."""
        self._save_queue()
        self.run_safe(lambda: [
            self.btn_add.configure(state="normal"),
            self.btn_start.configure(state="normal"),
            self.btn_cancel_queue.configure(state="disabled"),
            self.l_status.configure(text="Finished"),
        ])

        statuses = [i['status'] for i in self.queue_items]
        cancelled = statuses.count('cancelled')
        done = statuses.count('done')
        errors = statuses.count('error')

        if cancelled > 0 and done == 0 and errors == 0:
            self.log("队列已取消", "sad")
        elif done > 0:
            self.log("全部叼回窝里啦喵！", "done")
            show_windows_toast("Neko", "Queue finished!")
            self.mood_manager.interact()
            self.mood_manager.update_logic()
            self.update_mood_display()
        else:
            self.log("队列处理完毕", "working")

    # ── Single download flow ────────────────────────────────────

    def download_now_flow(self):
        u = self.run_safe(lambda: self.e_url.get().strip())
        if not u:
            return
        if (u != self.last_analyzed_url) or (self.current_meta is None):
            self.perform_analysis(u)
            if "手动" in self.run_safe(self.seg_mode.get):
                self.log("Select format first...", "happy")
                return
        cfg, _ = self.run_safe(self.build_current_config)
        self.log("Direct downloading...", "working")
        self.run_safe(lambda: [self.btn_now.configure(state="disabled"), self.btn_add.configure(state="disabled")])

        session_id = self.generate_session_id(cfg['url'], cfg['dir'])
        temp_file = self.find_current_temp_file(cfg, self.current_meta)

        session_dict = None
        if temp_file:
            session_dict = {
                'session_id': session_id, 'url': cfg['url'],
                'output_path': cfg['dir'], 'temp_file': temp_file,
            }
            self.log("Detected partial file, attempting resume...", "working")

        self._single_cancel_flag = threading.Event()
        self._single_popen = None

        def _single_task():
            # Store popen reference for cancellation
            self._current_task_pkt = "__single__"
            ok = self.download_item_with_resume(cfg, self.current_meta, session_dict)
            self._current_task_pkt = None
            cancelled = self._single_cancel_flag.is_set()
            self.after(0, lambda: self._single_done(ok, cancelled))

        self._single_thread = threading.Thread(target=_single_task, daemon=True)
        self._single_thread.start()

    def cancel_single_download(self):
        """Cancel the current single download (immediate grab)."""
        self._single_cancel_flag.set()
        sched = getattr(self, '_scheduler', None)
        if sched:
            sched.cancel_task("__single__")
        self.log("下载已取消", "sad")

    def _single_done(self, ok, cancelled):
        self.btn_now.configure(state="normal")
        self.btn_add.configure(state="normal")
        if cancelled:
            self.log("下载已取消", "sad")
            self.l_status.configure(text="已取消")
        elif ok:
            show_windows_toast("Neko", "Done!")
            self.log("Done!", "done")
            self.mood_manager.report_success()
            self.l_status.configure(text="待命中喵")
        else:
            self.log("Failed.", "sad")
            self.mood_manager.report_fail()
            self.l_status.configure(text="待命中喵")
        self.update_mood_display()

    # ── Queue persistence ───────────────────────────────────────

    def _save_queue(self):
        """Persist current queue items to the database."""
        tasks = []
        for it in self.queue_items:
            tasks.append({
                "url": it["config"].get("url", ""),
                "title": it.get("meta", {}).get("title", "Unknown"),
                "config": it["config"],
                "status": it["status"],
            })
        self.db.save_queue_tasks(tasks)

    def restore_queue(self):
        """Restore queue from database. Call from main_window after setup."""
        saved = self.db.load_queue_tasks()
        if not saved:
            return
        count = len(saved)
        done = sum(1 for t in saved if t["status"] in ("done", "finished"))
        pending = count - done
        if pending == 0:
            self.db.clear_queue_tasks()
            return

        def _do_restore():
            if not messagebox.askyesno("恢复队列", f"发现 {pending} 个未完成任务，是否恢复？"):
                self.db.clear_queue_tasks()
                return

            self.log(f"恢复 {pending} 个任务...", "working")
            for t in saved:
                if t["status"] in ("done", "finished"):
                    continue
                cfg = t["config"]
                if not cfg or not cfg.get("url"):
                    continue

                # Rebuild UI widget for the queue item
                if len(self.queue_items) == 0:
                    self.paned.add(self.right_panel, minsize=320, stretch="always")

                item = ctk.CTkFrame(self.scroll_q, fg_color=_c.CURRENT_THEME["panel_bg"], corner_radius=10)
                item.pack(fill="x", pady=5)
                tf = ctk.CTkFrame(item, fg_color="transparent")
                tf.pack(side="left", fill="both", expand=True, padx=5)
                ctk.CTkLabel(tf, text=t.get("title", "?"), font=FONT_Q_TITLE, anchor="w", text_color=_c.CURRENT_THEME["text"]).pack(fill="x", expand=True)
                desc_parts = [cfg.get("mode", "?")]
                dl = ctk.CTkLabel(tf, text=" ".join(desc_parts), font=FONT_Q_DESC, text_color="gray", anchor="w")
                dl.pack(fill="x", expand=True)

                status = t["status"]
                status_colors = {"waiting": "gray", "error": "red", "cancelled": "gray"}
                status_texts = {"waiting": "Queued", "error": "Error", "cancelled": "Cancelled"}
                lbl = ctk.CTkLabel(item, text=status_texts.get(status, "Queued"), font=("微软雅黑", 10), text_color=status_colors.get(status, "gray"))
                lbl.pack(side="right", padx=10)

                pkt = {"config": cfg, "label": lbl, "desc_label": dl, "status": status, "meta": {"title": t.get("title", "?")}, "widget": item}
                self.queue_items.append(pkt)

                def pop(e, p=pkt):
                    m = tk.Menu(self, tearoff=0)
                    if p['status'] in ('running', 'waiting'):
                        m.add_command(label="❌ 取消此任务", command=lambda: self.cancel_task(p))
                    m.add_command(label="✏️ Edit", command=lambda: self.edit_queue_item(p))
                    m.add_command(label="🗑️ Delete", command=lambda: self.delete_queue_item(p))
                    m.tk_popup(e.x_root, e.y_root)

                def rb(w):
                    w.bind("<Button-3>", pop)
                    [rb(c) for c in w.winfo_children()]

                rb(item)

            self.db.clear_queue_tasks()
            self.log(f"已恢复 {pending} 个任务", "done")

        self.after(1000, _do_restore)
