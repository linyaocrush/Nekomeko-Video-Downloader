import os
import customtkinter as ctk

# ── Directory paths ──────────────────────────────────────────────
DATA_DIR = "data"
THEMES_DIR = os.path.join(DATA_DIR, "themes")
COOKIES_DIR = os.path.join(DATA_DIR, "cookies")

for d in [DATA_DIR, THEMES_DIR, COOKIES_DIR]:
    try:
        if not os.path.exists(d):
            os.makedirs(d)
    except Exception as e:
        print(f"Failed to create directory {d}: {e}")

CFG_FILE = os.path.join(DATA_DIR, "config.json")
DB_FILE = os.path.join(DATA_DIR, "neko_history.db")
ACTIVE_THEME_FILE = os.path.join(DATA_DIR, "active_theme.json")

# ── Appearance ───────────────────────────────────────────────────
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")

# ── Theme template ───────────────────────────────────────────────
BASE_THEME_TEMPLATE = {
    "mode": "Light",
    "main_bg": "#FFF0F5",
    "panel_bg": "#F8F8F8",
    "secondary": "#FFFFFF",
    "text": "#333333",
    "accent": "#FF69B4",
    "btn_add_bg": "#87CEEB",
    "btn_add_fg": "#FFFFFF",
    "btn_now_bg": "#FFA500",
    "btn_now_fg": "#FFFFFF",
    "btn_start_bg": "#FF69B4",
    "btn_start_fg": "#FFFFFF",
}

DEFAULT_PRESETS = {
    "猫娘粉 (Neko Pink)": BASE_THEME_TEMPLATE.copy(),
    "深邃夜 (Deep Dark)": {
        "mode": "Dark", "main_bg": "#1A1A1A", "panel_bg": "#232323", "secondary": "#2B2B2B",
        "text": "#E0E0E0", "accent": "#7B68EE",
        "btn_add_bg": "#4682B4", "btn_add_fg": "#FFFFFF",
        "btn_now_bg": "#CD853F", "btn_now_fg": "#FFFFFF",
        "btn_start_bg": "#7B68EE", "btn_start_fg": "#FFFFFF",
    },
    "清爽蓝 (Fresh Blue)": {
        "mode": "Light", "main_bg": "#F0F8FF", "panel_bg": "#E6F2FF", "secondary": "#FFFFFF",
        "text": "#222222", "accent": "#1E90FF",
        "btn_add_bg": "#1E90FF", "btn_add_fg": "#FFFFFF",
        "btn_now_bg": "#32CD32", "btn_now_fg": "#FFFFFF",
        "btn_start_bg": "#4169E1", "btn_start_fg": "#FFFFFF",
    },
}

# ── Global mutable theme (set by ThemeManager) ──────────────────
CURRENT_THEME = BASE_THEME_TEMPLATE.copy()

# ── Fonts ────────────────────────────────────────────────────────
FONT_N = ("微软雅黑", 12)
FONT_B = ("微软雅黑", 12, "bold")
FONT_T = ("微软雅黑", 24, "bold")
FONT_S = ("微软雅黑", 10)
FONT_LOG = ("Consolas", 14)
FONT_Q_TITLE = ("微软雅黑", 13, "bold")
FONT_Q_DESC = ("微软雅黑", 12)
