import json
import os
import re
import io
import glob
import time
import subprocess
import shutil
import urllib.request
import logging

import customtkinter as ctk
from PIL import Image

from ...core.utils import safe_run

logger = logging.getLogger(__name__)


class DownloadMixin:
    """yt-dlp command building, metadata analysis, and download execution."""

    def get_cmd_base(self, pon, pip, ppt, ck):
        exe = self.cfg.get('ytdlp_path', '') or "yt-dlp"
        cmd = [exe, "--no-warnings", "--ignore-errors", "--encoding", "utf-8"]
        if not shutil.which("ffmpeg") and self.cfg.get('ffmpeg_path'):
            cmd.extend(["--ffmpeg-location", self.cfg['ffmpeg_path']])
        if pon and pip and ppt:
            cmd.extend(["--proxy", f"http://{pip}:{ppt}"])
        if "🚫" not in ck:
            if ck == "🔄 使用内置提取器":
                browser = self.c_browser.get()
                cmd.extend(["--cookies-from-browser", browser])
            else:
                from ...core.constants import COOKIES_DIR
                cp = os.path.join(COOKIES_DIR, ck)
                if os.path.exists(cp):
                    cmd.extend(["--cookies", cp])
        return cmd

    @safe_run
    def perform_analysis(self, url):
        self.log("Sniffing metadata...", "working")

        def gc():
            return {
                "pon": self.sw_proxy.get(), "pip": self.e_proxy_ip.get(),
                "ppt": self.e_proxy_port.get(), "ck": self.c_cookie.get(),
            }

        c = self.run_safe(gc)
        self.run_safe(lambda: [self.l_info.configure(text="Connecting..."), self.l_thumb.configure(image=None, text="...")])
        self.video_opts.clear()
        self.audio_opts.clear()
        self.video_infos.clear()
        self.subtitle_opts = []

        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        cmd = self.get_cmd_base(c["pon"], c["pip"], c["ppt"], c["ck"])

        res = subprocess.run(
            cmd + ["--dump-json", url], capture_output=True, text=True,
            encoding='utf-8', errors='replace', startupinfo=si,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

        if res.returncode != 0:
            self.log("Metadata fetch failed, using basic info for download", "sad")
            d = {"title": "Unknown Video", "uploader": "Unknown Uploader", "webpage_url": url, "formats": [], "thumbnail": None}
        else:
            try:
                d = json.loads(res.stdout.split('\n')[0])
            except Exception:
                self.log("Metadata parse failed, using basic info for download", "sad")
                d = {"title": "Unknown Video", "uploader": "Unknown Uploader", "webpage_url": url, "formats": [], "thumbnail": None}

        tr = None
        if 'thumbnail' in d:
            px = None
            if c["pon"]:
                px = {'http': f"http://{c['pip']}:{c['ppt']}", 'https': f"http://{c['pip']}:{c['ppt']}"}
            op = urllib.request.build_opener(urllib.request.ProxyHandler(px)) if px else urllib.request.build_opener()
            op.addheaders = [('User-Agent', 'Mozilla/5.0')]
            urllib.request.install_opener(op)
            try:
                tr = urllib.request.urlopen(d['thumbnail'], timeout=10).read()
            except Exception:
                pass

        v_list, a_list = [], []
        if 'formats' in d:
            for f in d['formats']:
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

        self.log("Checking subtitles...", "working")
        try:
            subs_cmd = cmd + ["--list-subs", url]
            subs_res = subprocess.run(
                subs_cmd, capture_output=True, text=True,
                encoding='utf-8', errors='replace', startupinfo=si,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            if subs_res.returncode == 0:
                for line in subs_res.stdout.strip().split('\n'):
                    line = line.strip()
                    if line and not line.startswith('['):
                        parts = line.split(' -- ')
                        if len(parts) >= 2:
                            lang_info = parts[0].strip()
                            sub_info = parts[1].strip()
                            lang_match = re.search(r'"([^"]+)"\s+\(([^\)]+)\)', lang_info)
                            if lang_match:
                                lang_code = lang_match.group(1)
                                lang_name = lang_match.group(2)
                                is_auto = 'automatic' in sub_info.lower()
                                label = f"{lang_name} ({lang_code})"
                                label += " [自动]" if is_auto else " [手动]"
                                self.subtitle_opts.append((lang_code, label, is_auto))
                if self.subtitle_opts:
                    self.log(f"Found {len(self.subtitle_opts)} subtitle languages", "happy")
                else:
                    self.log("No subtitles found", "sad")
        except Exception as e:
            logger.error(f"Error parsing subtitles: {e}")
            self.log("Failed to check subtitles", "sad")

        v_list.sort(key=lambda x: (x['h'], x['br']), reverse=True)
        a_list.sort(key=lambda x: x['abr'], reverse=True)
        v_labels = [x['label'] for x in v_list]
        a_labels = [x['label'] for x in a_list]

        def upd():
            self.current_meta = d
            self.last_analyzed_url = url
            if tr:
                self.current_thumb_img = ctk.CTkImage(Image.open(io.BytesIO(tr)), size=(160, 90))
                self.l_thumb.configure(image=self.current_thumb_img, text="")
                self.l_thumb.image = self.current_thumb_img
            else:
                self.current_thumb_img = None
                self.l_thumb.configure(image=None, text="No Image")
                self.l_thumb.image = None

            self.video_opts = {x['label']: x['id'] for x in v_list}
            self.audio_opts = {x['label']: x['id'] for x in a_list}
            self.c_video.configure(values=v_labels if v_labels else ["No Video"])
            self.c_audio.configure(values=a_labels if a_labels else ["No Audio"])
            if v_labels:
                self.c_video.set(v_labels[0])
            if a_labels:
                self.c_audio.set(a_labels[0])
            self.on_main_video_select(self.c_video.get())

            if self.subtitle_opts:
                sub_labels = [opt[1] for opt in self.subtitle_opts]
                self.c_subtitle_manual.configure(values=["不下载字幕"] + sub_labels)
                self.c_subtitle_manual.set("不下载字幕")
                self.c_subtitle_only.configure(values=sub_labels)
                self.c_subtitle_only.set(sub_labels[0])
            else:
                self.c_subtitle_manual.configure(values=["不下载字幕"])
                self.c_subtitle_manual.set("不下载字幕")
                self.c_subtitle_only.configure(values=["下载所有字幕"])
                self.c_subtitle_only.set("下载所有字幕")

            self.l_info.configure(text=f"Title: {d.get('title', '?')}\nUP: {d.get('uploader', '?')}")
            if 'entries' in d or d.get('_type') == 'playlist':
                self.sw_list.select()
            self.upd_ui()
            self.log(f"Analyzed: {d.get('title', '?')[:15]}...", "happy")

        self.run_safe(upd)
        return True

    def analyze_ui_wrapper(self):
        u = self.run_safe(lambda: self.e_url.get().strip())
        if u:
            self.perform_analysis(u)

    def build_current_config(self):
        m = self.seg_mode.get()
        desc = [m]
        if "手动" in m:
            desc.append(f"{self.c_video.get().split('|')[0]}")
        if self.sw_embed.get():
            desc.append("+Sub")
        if self.switch_time.get():
            desc.append(f"Cut({self.e_start_h.get()}:{self.e_start_m.get()}:{self.e_start_s.get()})")

        aid = self.audio_opts.get(self.c_audio.get())
        if "手动" in m and self.c_audio.cget("state") == "disabled":
            aid = None

        if self.current_meta is None:
            self.current_meta = {
                "title": "Unknown Video", "uploader": "Unknown Uploader",
                "webpage_url": self.e_url.get(), "formats": [], "thumbnail": None,
            }

        is_subtitle_mode = "字幕" in m
        if is_subtitle_mode:
            selected_subtitle = self.c_subtitle_only.get()
        else:
            selected_subtitle = self.c_subtitle_manual.get()

        subtitle_lang = None
        if selected_subtitle == "下载全部字幕":
            subtitle_lang = "all"
        elif selected_subtitle != "不下载字幕":
            for lang_code, label, _ in getattr(self, 'subtitle_opts', []):
                if label == selected_subtitle:
                    subtitle_lang = lang_code
                    break

        browser = self.c_browser.get()

        return {
            "url": self.current_meta.get("webpage_url", self.e_url.get()),
            "dir": self.e_dir.get(), "mode": m, "proxy_on": self.sw_proxy.get(),
            "proxy_ip": self.e_proxy_ip.get(), "proxy_port": self.e_proxy_port.get(),
            "cookie": self.c_cookie.get(), "browser": browser,
            "playlist": self.sw_list.get(), "embed": self.sw_embed.get(),
            "sb_act": self.c_sponsor_action.get(), "sb_cats": self.current_sponsor_cats,
            "v_id": self.video_opts.get(self.c_video.get()), "a_id": aid,
            "tmpl_on": self.cfg["tmpl_on"], "tmpl_str": self.cfg["tmpl_str"],
            "ytdlp_path": self.cfg.get('ytdlp_path', ''), "ffmpeg_path": self.cfg.get('ffmpeg_path', ''),
            "chat_mode": self.chat_mode_var.get() if hasattr(self, 'chat_mode_var') else "full",
            "chat_filters": self.chat_filters if hasattr(self, 'chat_filters') else ["author", "message", "timestamp"],
            "time_range_on": self.switch_time.get(),
            "start_h": self.e_start_h.get(), "start_m": self.e_start_m.get(), "start_s": self.e_start_s.get(),
            "end_h": self.e_end_h.get(), "end_m": self.e_end_m.get(), "end_s": self.e_end_s.get(),
            "subtitle_lang": subtitle_lang,
        }, " ".join(desc)

    @safe_run
    def download_item_with_resume(self, cfg, meta, resume_session=None):
        session_id = resume_session['session_id'] if resume_session else self.generate_session_id(cfg['url'], cfg['dir'])
        self.db.save_resume_session(
            session_id=session_id, url=cfg['url'], output_path=cfg['dir'],
            temp_file=self.get_expected_filename(cfg, meta) + ".part",
            downloaded_bytes=0, total_bytes=0, download_params=cfg,
            title=meta.get('title', 'Unknown'),
        )

        output_template = cfg['tmpl_str'] if cfg['tmpl_on'] else "%(title)s.%(ext)s"

        if 'browser' in cfg:
            self.c_browser.set(cfg['browser'])

        cmd = self.get_cmd_base(cfg["proxy_on"], cfg["proxy_ip"], cfg["proxy_port"], cfg["cookie"])
        cmd.extend([
            "--continue", "--no-part", "-N", "8",
            "-P", cfg["dir"], "-o", f"{output_template}",
            "--windows-filenames", "--no-mtime", "--embed-thumbnail", "--embed-metadata", "--newline",
        ])

        sb = cfg.get("sb_act", "")
        if "Mark" in sb:
            cmd.extend(["--sponsorblock-mark", "all", "--embed-chapters"])
        elif "Remove" in sb:
            cmd.extend(["--sponsorblock-remove", "all"])

        m = cfg["mode"]
        if "字幕" in m:
            cmd.extend(["--skip-download", "--write-subs", "--write-auto-subs"])
            subtitle_lang = cfg.get("subtitle_lang")
            if subtitle_lang and subtitle_lang != "all":
                cmd.extend(["--sub-langs", subtitle_lang])
        elif "声音" in m:
            cmd.extend(["-f", "bestaudio/best", "--extract-audio", "--audio-format", "mp3"])
        elif "直播" in m:
            cmd.extend(["--wait-for-video", "15", "--live-from-start"])
        elif "聊天室" in m:
            cmd.extend(["--write-sub", "--sub-langs", "live_chat", "--skip-download"])
        elif "手动" in m:
            v, a = cfg.get("v_id"), cfg.get("a_id")
            if v and a:
                cmd.extend(["-f", f"{v}+{a}"])
            elif v:
                cmd.extend(["-f", f"{v}+bestaudio"])
            else:
                cmd.extend(["-f", "bestvideo+bestaudio/best"])
        else:
            cmd.extend(["-f", "bestvideo+bestaudio/best"])

        if cfg.get("embed"):
            subtitle_lang = cfg.get("subtitle_lang")
            if subtitle_lang:
                cmd.extend(["--write-subs", "--write-auto-subs", "--embed-subs"])
                if subtitle_lang != "all":
                    cmd.extend(["--sub-langs", subtitle_lang])

        if cfg.get("time_range_on"):
            start_str = f"{cfg.get('start_h', '00')}:{cfg.get('start_m', '00')}:{cfg.get('start_s', '00')}"
            end_str = f"{cfg.get('end_h', '00')}:{cfg.get('end_m', '00')}:{cfg.get('end_s', '00')}"
            cmd.extend(["--download-sections", f"*{start_str}-{end_str}"])

        cmd.append("--yes-playlist" if cfg["playlist"] else "--no-playlist")
        cmd.append(cfg["url"])

        return self.execute_download_with_progress(cmd, cfg, meta, session_id)

    def process_chat_filtering(self, json_file, filters):
        try:
            filtered_file = json_file.replace(".live_chat.json", ".filtered.json")
            if filtered_file == json_file:
                filtered_file += ".json"

            output_data = []
            with open(json_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if 'replayChatItemAction' not in data:
                            continue
                        actions = data['replayChatItemAction']['actions']
                        for action in actions:
                            if 'addChatItemAction' not in action:
                                continue
                            item = action['addChatItemAction']['item']
                            renderer = None
                            msg_type = "normal"
                            if 'liveChatTextMessageRenderer' in item:
                                renderer = item['liveChatTextMessageRenderer']
                            elif 'liveChatPaidMessageRenderer' in item:
                                renderer = item['liveChatPaidMessageRenderer']
                                msg_type = "paid"
                            if not renderer:
                                continue
                            entry = {}
                            if "author" in filters:
                                entry['author'] = renderer.get('authorName', {}).get('simpleText', 'Unknown')
                            if "message" in filters:
                                runs = renderer.get('message', {}).get('runs', [])
                                entry['message'] = "".join([r.get('text', '') for r in runs])
                            if "timestamp" in filters:
                                entry['timestamp'] = renderer.get('timestampUsec', '0')
                            if "money" in filters and msg_type == "paid":
                                entry['money'] = renderer.get('purchaseAmountText', {}).get('simpleText', '')
                            if "badges" in filters:
                                badges = renderer.get('authorBadges', [])
                                entry['badges'] = [b.get('liveChatAuthorBadgeRenderer', {}).get('tooltip', '') for b in badges]
                            output_data.append(entry)
                    except Exception:
                        continue

            if output_data:
                with open(filtered_file, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                return True
        except Exception as e:
            print(f"Chat filter error: {e}")
            return False
        return False

    def execute_download_with_progress(self, cmd, cfg, meta, session_id):
        p = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace',
            startupinfo=subprocess.STARTUPINFO(),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

        # Register with scheduler for cancellation (if running in queue mode)
        sched = getattr(self, '_scheduler', None)
        task_pkt = getattr(self, '_current_task_pkt', None)
        if sched and task_pkt:
            sched.register_process(task_pkt, p)

        rp = re.compile(r"(\d+\.?\d*)%")
        rs = re.compile(r"of\s+(\S+)")
        rsp = re.compile(r"at\s+(\S+)")
        ret = re.compile(r"ETA\s+(\S+)")
        st = time.time()
        last_save_time = 0
        last_ui_time = 0
        final_file_path = None
        pending_pct = None
        pending_txt = None

        re_merge = re.compile(r'\[Merger\] Merging formats into "(.*?)"')
        re_dest = re.compile(r'\[download\] Destination: (.*)')
        re_exist = re.compile(r'\[download\] (.*?) has already been downloaded')

        def flush_ui():
            nonlocal last_ui_time, pending_pct, pending_txt
            if pending_pct is not None:
                self.run_safe(lambda p=pending_pct: self.prog.set(p))
                pending_pct = None
            if pending_txt is not None:
                self.run_safe(lambda t=pending_txt: self.l_status.configure(text=t))
                pending_txt = None
            last_ui_time = time.time()

        for l in p.stdout:
            # Check cancellation
            if sched and task_pkt and sched.is_task_cancelled(task_pkt):
                p.terminate()
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    p.kill()
                flush_ui()
                return False

            if "Merger" in l:
                if m := re_merge.search(l):
                    final_file_path = m.group(1)
            elif "Destination:" in l:
                if m := re_dest.search(l):
                    final_file_path = m.group(1)
            elif "has already been downloaded" in l:
                if m := re_exist.search(l):
                    final_file_path = m.group(1)

            if "[download]" in l and "%" in l:
                if mp := rp.search(l):
                    pct = float(mp.group(1))
                    pending_pct = pct / 100
                    txt = f"{pct}%"
                    if ms := rs.search(l):
                        size_str = ms.group(1)
                        txt += f" | {size_str}"
                    if msp := rsp.search(l):
                        txt += f" | {msp.group(1)}"
                    if me := ret.search(l):
                        txt += f" | {me.group(1)}"
                    pending_txt = txt

                    if time.time() - last_ui_time > 0.2:
                        flush_ui()

                    if time.time() - last_save_time > 2:
                        temp_file = self.find_current_temp_file(cfg, meta)
                        if temp_file and os.path.exists(temp_file):
                            current_size = os.path.getsize(temp_file)
                            self.save_resume_state(session_id, cfg, meta, current_size, 0)
                            last_save_time = time.time()
            elif not any(x in l for x in ["[download]", "Deleting"]):
                self.log(l.strip())

        flush_ui()

        # Check cancellation one more time after process exits
        if sched and task_pkt and sched.is_task_cancelled(task_pkt):
            return False

        p.wait()
        self.run_safe(lambda: self.prog.set(1 if p.returncode == 0 else 0))

        if p.returncode == 0:
            if "聊天室" in cfg.get("mode", "") and cfg.get("chat_mode") == "filter":
                base_name = self.get_expected_filename(cfg, meta)
                json_candidates = glob.glob(f"{base_name}*.live_chat.json")
                if json_candidates:
                    json_file = json_candidates[0]
                    self.log("Filtering chat data...", "working")
                    if self.process_chat_filtering(json_file, cfg.get("chat_filters", [])):
                        try:
                            os.remove(json_file)
                        except Exception:
                            pass

            if meta:
                fs = 0
                if final_file_path:
                    if not os.path.isabs(final_file_path):
                        final_file_path = os.path.join(cfg['dir'], final_file_path)
                    if os.path.exists(final_file_path):
                        try:
                            fs = os.path.getsize(final_file_path)
                        except Exception:
                            pass
                if fs == 0:
                    fs = meta.get('filesize', 0) or meta.get('filesize_approx', 0)
                self.db.add_record(meta, fs, time.time() - st)
            self.db.complete_resume_session(session_id)
            return True
        else:
            return False
