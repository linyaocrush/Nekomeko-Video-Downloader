import os
import json
import re
import logging

import customtkinter as ctk

from .constants import (
    THEMES_DIR, ACTIVE_THEME_FILE, BASE_THEME_TEMPLATE, DEFAULT_PRESETS,
)

logger = logging.getLogger(__name__)


class ThemeManager:
    def __init__(self):
        self.init_defaults()
        self.load_active_theme()

    def init_defaults(self):
        if not os.listdir(THEMES_DIR):
            for name, data in DEFAULT_PRESETS.items():
                self.save_preset(name, data)

    def get_all_presets(self):
        files = [f.replace(".json", "") for f in os.listdir(THEMES_DIR) if f.endswith(".json")]
        return sorted(files)

    def load_preset(self, name):
        path = os.path.join(THEMES_DIR, f"{name}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    temp = BASE_THEME_TEMPLATE.copy()
                    temp.update(data)
                    return temp
            except Exception:
                pass
        return DEFAULT_PRESETS.get(name, BASE_THEME_TEMPLATE.copy())

    def save_preset(self, name, data):
        valid_name = re.sub(r'[\\/*?:"<>|]', "", name).strip()
        if not valid_name:
            valid_name = "Untitled_Theme"
        path = os.path.join(THEMES_DIR, f"{valid_name}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Theme save error: {e}")
            return False

    def load_active_theme(self):
        from . import constants as _c
        active_name = "猫娘粉 (Neko Pink)"
        if os.path.exists(ACTIVE_THEME_FILE):
            try:
                with open(ACTIVE_THEME_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    active_name = cfg.get("active", active_name)
            except Exception:
                pass

        _c.CURRENT_THEME = self.load_preset(active_name)
        ctk.set_appearance_mode(_c.CURRENT_THEME["mode"])
        if _c.CURRENT_THEME["mode"] == "Dark":
            ctk.set_default_color_theme("dark-blue")
        else:
            ctk.set_default_color_theme("blue")

    def set_active_theme_record(self, name):
        try:
            with open(ACTIVE_THEME_FILE, "w", encoding="utf-8") as f:
                json.dump({"active": name}, f)
        except Exception:
            pass
