import sqlite3
import datetime
import threading
import json
import logging
from collections import Counter
from typing import List

from ..core.models import HistoryRecord
from ..core.constants import DB_FILE

logger = logging.getLogger(__name__)


class NekoDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.lock = threading.Lock()
        self.init_table()
        self.upgrade_table()
        self.upgrade_resume_support()

    def init_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                uploader TEXT,
                uploader_url TEXT,
                webpage_url TEXT,
                file_size INTEGER,
                download_date TIMESTAMP,
                duration INTEGER DEFAULT 0,
                elapsed_seconds REAL DEFAULT 0
            )
        ''')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_uploader ON downloads (uploader)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_date ON downloads (download_date)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON downloads (webpage_url)')
        self.cursor.execute('''
            CREATE VIEW IF NOT EXISTS stats_view AS
            SELECT
                COUNT(*) as total_count,
                SUM(file_size) as total_size,
                date(download_date) as d,
                strftime('%H', download_date) as hour,
                CASE
                    WHEN duration < 300 THEN 'short'
                    WHEN duration < 1800 THEN 'medium'
                    ELSE 'long'
                END as dur_type
            FROM downloads
            GROUP BY d, hour, dur_type
        ''')
        self.conn.commit()

    def upgrade_table(self):
        for col, default in [
            ("duration", "INTEGER DEFAULT 0"),
            ("elapsed_seconds", "REAL DEFAULT 0"),
        ]:
            try:
                self.cursor.execute(f"ALTER TABLE downloads ADD COLUMN {col} {default}")
            except Exception:
                pass
        self.conn.commit()

    def upgrade_resume_support(self):
        for col, default in [
            ("download_status", "TEXT DEFAULT 'pending'"),
            ("progress_percentage", "REAL DEFAULT 0.0"),
            ("downloaded_bytes", "INTEGER DEFAULT 0"),
            ("total_bytes", "INTEGER DEFAULT 0"),
            ("temp_file_path", "TEXT"),
            ("session_id", "TEXT"),
        ]:
            try:
                self.cursor.execute(f"ALTER TABLE downloads ADD COLUMN {col} {default}")
            except Exception:
                pass

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS resume_sessions (
                session_id TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                output_path TEXT NOT NULL,
                temp_file TEXT NOT NULL,
                downloaded_bytes INTEGER DEFAULT 0,
                total_bytes INTEGER DEFAULT 0,
                last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                download_params TEXT,
                status TEXT DEFAULT 'active',
                title TEXT DEFAULT 'Unknown'
            )
        """)
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_status ON resume_sessions (status)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_session_update ON resume_sessions (last_update)')
        self.conn.commit()

    def save_resume_session(self, session_id, url, output_path, temp_file,
                            downloaded_bytes, total_bytes, download_params, title):
        with self.lock:
            self.cursor.execute("""
                INSERT OR REPLACE INTO resume_sessions
                (session_id, url, output_path, temp_file, downloaded_bytes,
                 total_bytes, download_params, title, last_update)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_id, url, output_path, temp_file,
                downloaded_bytes, total_bytes, json.dumps(download_params), title,
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            self.conn.commit()

    def get_pending_resume_sessions(self):
        with self.lock:
            self.cursor.execute(
                "SELECT * FROM resume_sessions WHERE status = 'active' ORDER BY last_update DESC"
            )
            return self.cursor.fetchall()

    def complete_resume_session(self, session_id):
        self.delete_resume_session(session_id)

    def delete_resume_session(self, session_id):
        with self.lock:
            self.cursor.execute("DELETE FROM resume_sessions WHERE session_id = ?", (session_id,))
            self.conn.commit()

    def delete_all_resume_sessions(self):
        with self.lock:
            self.cursor.execute("DELETE FROM resume_sessions")
            self.conn.commit()

    def add_record(self, meta, size_bytes, elapsed):
        with self.lock:
            try:
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                duration = meta.get('duration', 0) or 0
                self.cursor.execute('''
                    INSERT INTO downloads
                    (title, uploader, uploader_url, webpage_url, file_size,
                     download_date, duration, elapsed_seconds,
                     download_status, progress_percentage, downloaded_bytes, total_bytes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed', 100.0, ?, ?)
                ''', (
                    meta.get('title', 'Unknown'),
                    meta.get('uploader', 'Unknown'),
                    meta.get('uploader_url', '') or meta.get('channel_url', ''),
                    meta.get('webpage_url', ''),
                    size_bytes, now, duration, elapsed,
                    size_bytes, size_bytes,
                ))
                self.conn.commit()
                return True
            except Exception as e:
                logger.error(f"DB Error: {e}")
                return False

    def get_today_count(self):
        with self.lock:
            try:
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                self.cursor.execute("SELECT COUNT(*) FROM downloads WHERE date(download_date) = ?", (today,))
                return self.cursor.fetchone()[0]
            except Exception:
                return 0

    def get_full_stats(self):
        with self.lock:
            self.cursor.execute(
                "SELECT file_size, download_date, elapsed_seconds, duration, webpage_url FROM downloads"
            )
            rows = self.cursor.fetchall()
        stats = {
            "total_count": len(rows),
            "total_size": sum(r[0] for r in rows if r[0]),
            "total_time": sum(r[2] for r in rows if r[2]),
            "today_count": 0, "today_size": 0,
            "week_count": 0, "week_size": 0,
            "month_count": 0, "month_size": 0,
            "hours": Counter(), "platforms": Counter(),
            "durations": {"short": 0, "medium": 0, "long": 0},
        }
        now = datetime.datetime.now()
        for r in rows:
            size = r[0] or 0
            dt_str = r[1]
            try:
                dt = datetime.datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            except Exception:
                continue
            if dt.date() == now.date():
                stats["today_count"] += 1
                stats["today_size"] += size
            if (now - dt).days < 7:
                stats["week_count"] += 1
                stats["week_size"] += size
            if (now - dt).days < 30:
                stats["month_count"] += 1
                stats["month_size"] += size
            stats["hours"][dt.hour] += 1
            dur = r[3] or 0
            if dur < 300:
                stats["durations"]["short"] += 1
            elif dur < 1800:
                stats["durations"]["medium"] += 1
            else:
                stats["durations"]["long"] += 1
            url = (r[4] or "").lower()
            if "bilibili" in url:
                stats["platforms"]["B站"] += 1
            elif "youtube" in url or "youtu.be" in url:
                stats["platforms"]["YouTube"] += 1
            elif "douyin" in url:
                stats["platforms"]["抖音"] += 1
            elif "tiktok" in url:
                stats["platforms"]["TikTok"] += 1
            elif "twitter" in url or "x.com" in url:
                stats["platforms"]["推特(X)"] += 1
            else:
                stats["platforms"]["其他"] += 1
        return stats

    def get_top_uploaders(self, limit=5):
        with self.lock:
            self.cursor.execute(
                'SELECT uploader, COUNT(*) as count FROM downloads GROUP BY uploader ORDER BY count DESC LIMIT ?',
                (limit,),
            )
            return self.cursor.fetchall()

    def get_all_uploaders(self):
        with self.lock:
            self.cursor.execute("SELECT DISTINCT uploader FROM downloads ORDER BY uploader")
            return [r[0] for r in self.cursor.fetchall() if r[0]]

    def search_history(self, keyword="", uploader_filter="全部",
                       platform_filter="全部", limit=50) -> List[HistoryRecord]:
        with self.lock:
            sql = "SELECT * FROM downloads WHERE 1=1"
            params: list = []
            if keyword:
                sql += " AND title LIKE ?"
                params.append(f"%{keyword}%")
            if uploader_filter and uploader_filter != "全部":
                sql += " AND uploader = ?"
                params.append(uploader_filter)
            if platform_filter and platform_filter != "全部":
                if platform_filter == "B站 (Bilibili)":
                    sql += " AND webpage_url LIKE '%bilibili%'"
                elif platform_filter == "油管 (YouTube)":
                    sql += " AND (webpage_url LIKE '%youtube%' OR webpage_url LIKE '%youtu.be%')"
                elif platform_filter == "抖音 (Douyin)":
                    sql += " AND webpage_url LIKE '%douyin%'"
                elif platform_filter == "推特 (X)":
                    sql += " AND (webpage_url LIKE '%twitter%' OR webpage_url LIKE '%x.com%')"
            sql += " ORDER BY download_date DESC LIMIT ?"
            params.append(limit)
            self.cursor.execute(sql, tuple(params))
            rows = self.cursor.fetchall()
        records = []
        for r in rows:
            try:
                records.append(HistoryRecord(
                    id=r[0], title=r[1], uploader=r[2], uploader_url=r[3],
                    webpage_url=r[4], file_size=r[5], download_date=r[6],
                    duration=r[7], elapsed_seconds=r[8],
                ))
            except Exception as e:
                logger.error(f"Data conversion error for row {r[0]}: {e}")
        return records
