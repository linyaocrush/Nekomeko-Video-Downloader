import time
import datetime
import random
import logging

logger = logging.getLogger(__name__)


class NekoMoodManager:
    def __init__(self, db):
        self.db = db
        self.mood = "normal"
        self.last_interaction = time.time()
        self.download_success_today = 0
        self.greetings = {
            "normal": [
                "主人喵~ 今天想抓哪只视频小老鼠？", "喵~ 随时待命！", "尾巴摇摇~ 等待指令喵。",
                "只要是Master想要的，我都会努力去抓！", "今天天气真好，适合抓老鼠（视频）~",
            ],
            "happy": [
                "哇！今天收获不错呢！", "主人最棒了喵！再多喂我一点链接嘛~", "呼噜呼噜... 开心~",
                "这种感觉... 是丰收的喜悦喵！",
            ],
            "excited": [
                "哇呜！主人手速超快喵！🔥", "停不下来了喵！还有吗还有吗？",
                "今天是大丰收！Master 最强！💖", "猫娘的引擎正在全速运转！",
            ],
            "lonely": [
                "...好安静... 主人还在吗喵？", "呜呜... 只有我一只猫在这里...",
                "尾巴都不摇了... 理理我嘛...", "Master 是不是去别的猫那里了...",
            ],
            "sleepy": [
                "哈欠... 熬夜会掉毛的哦...", "Master，该睡觉了喵... zzz",
                "虽然很困，但为了 Master 还能坚持一下...", "月亮都睡了喵...",
            ],
            "sad": [
                "呜... 刚才那个没抓到...", "对不起 Master，我搞砸了...",
                "别生气... 我下次会更努力的...", "心情低落... 需要摸摸头...",
            ],
        }
        self.update_counts_from_db()

    def update_counts_from_db(self):
        try:
            self.download_success_today = self.db.get_today_count()
        except Exception:
            pass

    def interact(self):
        self.last_interaction = time.time()
        if self.mood in ("lonely", "sleepy"):
            self.mood = "normal"
            self.update_logic()

    def report_success(self):
        self.interact()
        self.download_success_today += 1
        self.mood = "happy"
        self.update_logic()

    def report_fail(self):
        self.interact()
        self.mood = "sad"

    def update_logic(self):
        now = time.time()
        idle = now - self.last_interaction
        hour = datetime.datetime.now().hour
        if self.mood == "sad" and idle < 10:
            return
        if (hour >= 23 or hour < 6) and idle > 60:
            self.mood = "sleepy"
            return
        if idle > 300:
            self.mood = "lonely"
            return
        if self.download_success_today >= 10:
            self.mood = "excited"
        elif self.download_success_today >= 3:
            self.mood = "happy"
        else:
            self.mood = "normal"

    def get_greeting(self):
        self.update_logic()
        msgs = self.greetings.get(self.mood, self.greetings["normal"])
        return f"[{self.mood.upper()}] {random.choice(msgs)}"
