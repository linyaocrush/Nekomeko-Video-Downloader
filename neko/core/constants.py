import os
import subprocess
import customtkinter as ctk

# ── Subprocess flags for hiding console windows on Windows ──────
SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

# ── Directory paths (absolute, based on project root) ──────────
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))       # neko/core/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(_PKG_DIR))   # repo root
DATA_DIR = os.path.join(_PROJECT_ROOT, "data")
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

# ── MD3 Color Token System ───────────────────────────────────────
# Semantic role keys used by all UI code via _c.CURRENT_THEME["key"].
# Legacy aliases (main_bg, panel_bg, etc.) kept for backward compat.
#
# Widget → token mapping:
#   Window bg       → background      Panel/card bg   → surface
#   Input fields    → surface_variant  Primary text    → on_surface
#   Muted text      → on_surface_variant  Headings    → primary
#   Primary btn     → primary/on_primary
#   Tertiary btn    → tertiary_container/on_tertiary_container
#   Secondary btn   → secondary_container/on_secondary_container
#   Progress/switch → primary          Outline         → outline
#   Error           → error

BASE_THEME_TEMPLATE = {
    "mode": "Light",

    # Primary
    "primary":              "#BE0F6E",
    "on_primary":           "#FFFFFF",
    "primary_container":    "#FFD9E6",
    "on_primary_container": "#3E0021",

    # Secondary
    "secondary":              "#74565F",
    "on_secondary":           "#FFFFFF",
    "secondary_container":    "#FFD9E6",
    "on_secondary_container": "#2B151C",

    # Tertiary
    "tertiary":              "#7C5635",
    "on_tertiary":           "#FFFFFF",
    "tertiary_container":    "#FFDCC2",
    "on_tertiary_container": "#2E1500",

    # Error
    "error":              "#BA1A1A",
    "on_error":           "#FFFFFF",
    "error_container":    "#FFDAD6",
    "on_error_container": "#410002",

    # Surface / Background
    "background":           "#FFF8F8",
    "on_background":        "#23191C",
    "surface":              "#FFF8F8",
    "on_surface":           "#23191C",
    "surface_variant":      "#F2DDE1",
    "on_surface_variant":   "#514347",
    "surface_container_lowest":  "#FFFFFF",
    "surface_container_low":     "#FEF0F3",
    "surface_container":         "#F9E8EC",
    "surface_container_high":    "#F3E2E6",
    "surface_container_highest": "#EDDCDF",
    "surface_bright":            "#FFF8F8",
    "surface_dim":               "#E6D6DA",

    # Outline
    "outline":          "#837377",
    "outline_variant":  "#D5C2C6",

    # Inverse
    "inverse_surface":    "#392E31",
    "inverse_on_surface": "#FFEDF0",
    "inverse_primary":    "#FFB0CB",

    "scrim": "#000000",

    # Legacy aliases
    "main_bg":   "#FFF8F8",
    "panel_bg":  "#F2DDE1",
    "text":      "#23191C",
    "accent":    "#BE0F6E",

    # Per-button overrides (legacy)
    "btn_add_bg": "#FFDCC2",  "btn_add_fg": "#2E1500",
    "btn_now_bg": "#FFD9E6",  "btn_now_fg": "#2B151C",
    "btn_start_bg": "#BE0F6E",  "btn_start_fg": "#FFFFFF",
}

# ── Default presets ─────────────────────────────────────────────

DEFAULT_PRESETS = {
    "猫娘粉 (Neko Pink)": BASE_THEME_TEMPLATE.copy(),

    "深邃夜 (Deep Dark)": {
        "mode": "Dark",
        "primary": "#FFB0CB", "on_primary": "#5E0036",
        "primary_container": "#820049", "on_primary_container": "#FFD9E6",
        "secondary": "#DEBCC6", "on_secondary": "#422931",
        "secondary_container": "#5B3F47", "on_secondary_container": "#FFD9E6",
        "tertiary": "#EABB98", "on_tertiary": "#4A2708",
        "tertiary_container": "#653B1F", "on_tertiary_container": "#FFDCC2",
        "error": "#FFB4AB", "on_error": "#690005",
        "error_container": "#93000A", "on_error_container": "#FFDAD6",
        "background": "#1A1113", "on_background": "#EDDCDF",
        "surface": "#1A1113", "on_surface": "#EDDCDF",
        "surface_variant": "#514347", "on_surface_variant": "#D5C2C6",
        "surface_container_lowest": "#120C0E", "surface_container_low": "#23191C",
        "surface_container": "#271D20", "surface_container_high": "#32272A",
        "surface_container_highest": "#3D3135", "surface_bright": "#392E31",
        "surface_dim": "#1A1113",
        "outline": "#9E8C90", "outline_variant": "#514347",
        "inverse_surface": "#EDDCDF", "inverse_on_surface": "#392E31",
        "inverse_primary": "#BE0F6E", "scrim": "#000000",
        "main_bg": "#1A1113", "panel_bg": "#23191C",
        "text": "#EDDCDF", "accent": "#FFB0CB",
        "btn_add_bg": "#653B1F", "btn_add_fg": "#FFDCC2",
        "btn_now_bg": "#5B3F47", "btn_now_fg": "#FFD9E6",
        "btn_start_bg": "#FFB0CB", "btn_start_fg": "#5E0036",
    },

    "清爽蓝 (Fresh Blue)": {
        "mode": "Light",
        "primary": "#0061A4", "on_primary": "#FFFFFF",
        "primary_container": "#D1E4FF", "on_primary_container": "#001D36",
        "secondary": "#535F70", "on_secondary": "#FFFFFF",
        "secondary_container": "#D7E3F7", "on_secondary_container": "#101C2B",
        "tertiary": "#6B5733", "on_tertiary": "#FFFFFF",
        "tertiary_container": "#F5DFA7", "on_tertiary_container": "#241A00",
        "error": "#BA1A1A", "on_error": "#FFFFFF",
        "error_container": "#FFDAD6", "on_error_container": "#410002",
        "background": "#F8F9FF", "on_background": "#191C20",
        "surface": "#F8F9FF", "on_surface": "#191C20",
        "surface_variant": "#DFE2EB", "on_surface_variant": "#43474E",
        "surface_container_lowest": "#FFFFFF", "surface_container_low": "#F1F3FA",
        "surface_container": "#ECEDF4", "surface_container_high": "#E6E8EF",
        "surface_container_highest": "#E1E2E9", "surface_bright": "#F8F9FF",
        "surface_dim": "#D8DAE0",
        "outline": "#73777F", "outline_variant": "#C3C7CF",
        "inverse_surface": "#2E3135", "inverse_on_surface": "#EFF0F7",
        "inverse_primary": "#9ECAFF", "scrim": "#000000",
        "main_bg": "#F8F9FF", "panel_bg": "#DFE2EB",
        "text": "#191C20", "accent": "#0061A4",
        "btn_add_bg": "#F5DFA7", "btn_add_fg": "#241A00",
        "btn_now_bg": "#D7E3F7", "btn_now_fg": "#101C2B",
        "btn_start_bg": "#0061A4", "btn_start_fg": "#FFFFFF",
    },
}

# ── Global mutable theme (set by ThemeManager at startup) ───────
CURRENT_THEME = BASE_THEME_TEMPLATE.copy()

# ── Fonts ────────────────────────────────────────────────────────
FONT_N = ("微软雅黑", 12)
FONT_B = ("微软雅黑", 12, "bold")
FONT_T = ("微软雅黑", 24, "bold")
FONT_S = ("微软雅黑", 10)
FONT_LOG = ("Consolas", 14)
FONT_Q_TITLE = ("微软雅黑", 13, "bold")
FONT_Q_DESC = ("微软雅黑", 12)
