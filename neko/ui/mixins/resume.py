import os
import re
import glob
import hashlib
import datetime


class ResumeMixin:
    """Resume session tracking, temp file detection, and resume manager."""

    def generate_session_id(self, url, output_path):
        content = f"{url}_{output_path}_{datetime.datetime.now().timestamp()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]

    def get_expected_filename(self, cfg, meta):
        if cfg['tmpl_on']:
            template = cfg['tmpl_str']
            title = meta.get('title', 'Unknown')
            filename = template.replace('%(title)s', title)
        else:
            filename = meta.get('title', 'Unknown')
        filename = re.sub(r'[\\/*?:"<>|\[\]]', "", filename)
        return os.path.join(cfg['dir'], filename)

    def find_current_temp_file(self, cfg, meta):
        expected_name = self.get_expected_filename(cfg, meta)
        possible_temps = [
            expected_name + ".part", expected_name + ".temp",
            expected_name + ".ytdl", expected_name + ".f*.part",
        ]
        for pattern in possible_temps:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]
        return None

    def save_resume_state(self, session_id, cfg, meta, downloaded_bytes, total_bytes):
        temp_file = self.find_current_temp_file(cfg, meta)
        if temp_file and downloaded_bytes > 0:
            self.db.save_resume_session(
                session_id=session_id, url=cfg['url'], output_path=cfg['dir'],
                temp_file=temp_file, downloaded_bytes=downloaded_bytes,
                total_bytes=total_bytes, download_params=cfg,
                title=meta.get('title', 'Unknown'),
            )

    def check_resume_status(self):
        try:
            if not self.winfo_exists():
                return
            pending_sessions = self.db.get_pending_resume_sessions()
            count = len(pending_sessions) if pending_sessions else 0
            if count > 0:
                self.resume_status_label.configure(text=f"📂 {count}个任务可续传", text_color="orange")
                self.btn_resume_manager.configure(fg_color="#FF8C42")
            else:
                self.resume_status_label.configure(text="无待续传任务", text_color="gray")
                self.btn_resume_manager.configure(fg_color="#FF6B6B")
            self.after(5000, self.check_resume_status)
        except Exception:
            pass  # Window destroyed, stop polling

    def open_resume_manager(self):
        from ..resume import ResumeManagerWindow
        ResumeManagerWindow(self, self.db)

    def start_resume_download(self, session, download_params):
        try:
            self.log(f"Resuming: {session[9]}...", "working")
            meta = {'title': session[9]}
            session_dict = {
                'session_id': session[0], 'url': session[1],
                'output_path': session[2], 'temp_file': session[3],
            }
            self.download_item_with_resume(download_params, meta, session_dict)
        except Exception as e:
            self.log(f"Resume failed: {e}", "sad")
