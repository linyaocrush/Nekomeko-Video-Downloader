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

# ── MD3 Color Token System ───────────────────────────────────────
# Full Material Design 3 color role naming.
# Legacy keys (main_bg, panel_bg, etc.) are kept as aliases for backward
# compatibility so the ThemeEditor and all existing UI code keep working.
#
# Tonal palette keys (primary_t0 .. primary_t100 etc.) are stored so that
# the theme editor can expose tonal editing in a future update, but they
# are NOT required by the UI code — only the semantic role keys are used.
#
# Widget mapping (see WIDGET_TOKEN_MAP below):
#   Window background    -> background
#   Main panels/cards    -> surface
#   Elevated cards       -> surface_container
#   Input fields/combo   -> surface_variant
#   Scrollable frames    -> surface_bright / transparent
#   Primary text         -> on_surface
#   Secondary/muted text -> on_surface_variant
#   Accent headings      -> primary
#   Primary filled btn   -> primary fg, on_primary text
#   Tertiary action btn  -> tertiary fg, on_tertiary text
#   Secondary action btn -> secondary_container fg, on_secondary_container text
#   Progress bars        -> primary
#   Switches/toggles     -> primary (progress_color)
#   Checkboxes/radios    -> primary (fg_color, border_color)
#   Tabs/segmented btn   -> primary (selected_color)
#   Outlines/borders     -> outline
#   Error states         -> error

BASE_THEME_TEMPLATE = {
    # ── Mode ─────────────────────────────────────────────────────
    "mode": "Light",

    # ── Primary (brand color) ────────────────────────────────────
    "primary":              "#BE0F6E",
    "on_primary":           "#FFFFFF",
    "primary_container":    "#FFD9E6",
    "on_primary_container": "#3E0021",

    # ── Secondary (supporting brand) ─────────────────────────────
    "secondary":              "#74565F",
    "on_secondary":           "#FFFFFF",
    "secondary_container":    "#FFD9E6",
    "on_secondary_container": "#2B151C",

    # ── Tertiary (accent / contrast) ─────────────────────────────
    "tertiary":              "#7C5635",
    "on_tertiary":           "#FFFFFF",
    "tertiary_container":    "#FFDCC2",
    "on_tertiary_container": "#2E1500",

    # ── Error ────────────────────────────────────────────────────
    "error":              "#BA1A1A",
    "on_error":           "#FFFFFF",
    "error_container":    "#FFDAD6",
    "on_error_container": "#410002",

    # ── Surface / Background ─────────────────────────────────────
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

    # ── Outline ──────────────────────────────────────────────────
    "outline":          "#837377",
    "outline_variant":  "#D5C2C6",

    # ── Inverse (for tooltips, snackbars) ────────────────────────
    "inverse_surface":    "#392E31",
    "inverse_on_surface": "#FFEDF0",
    "inverse_primary":    "#FFB0CB",

    # ── Scrim / Shadow ───────────────────────────────────────────
    "scrim": "#000000",

    # ── Legacy aliases (backward compat) ─────────────────────────
    # These ensure every old key resolves to a sensible MD3 token.
    "main_bg":   "#FFF8F8",  # = background
    "panel_bg":  "#F2DDE1",  # = surface_variant
    "text":      "#23191C",  # = on_background
    "accent":    "#BE0F6E",  # = primary

    # ── Per-button overrides (legacy) ────────────────────────────
    # "放进篮子" (Add to queue) — uses tertiary role
    "btn_add_bg": "#FFDCC2",  # = tertiary_container
    "btn_add_fg": "#2E1500",  # = on_tertiary_container

    # "立即抓取" (Download now) — uses secondary_container role
    "btn_now_bg": "#FFD9E6",  # = secondary_container
    "btn_now_fg": "#2B151C",  # = on_secondary_container

    # "叼回窝里" (Start queue) — uses primary role
    "btn_start_bg": "#BE0F6E",  # = primary
    "btn_start_fg": "#FFFFFF",  # = on_primary

    # ── Tonal palette reference (for future tonal editor) ────────
    "primary_t10": "#3E0021",  "primary_t20": "#5E0036",
    "primary_t30": "#820049",  "primary_t40": "#BE0F6E",
    "primary_t50": "#D93989",  "primary_t60": "#E969A4",
    "primary_t70": "#F593BF",  "primary_t80": "#FFB0CB",
    "primary_t90": "#FFD9E6",  "primary_t95": "#FFECF1",
    "primary_t99": "#FFFBFF",

    "secondary_t10": "#2B151C", "secondary_t20": "#422931",
    "secondary_t30": "#5B3F47", "secondary_t40": "#74565F",
    "secondary_t50": "#8E6E77", "secondary_t60": "#A88791",
    "secondary_t70": "#C3A1AB", "secondary_t80": "#DEBCC6",
    "secondary_t90": "#FFD9E6", "secondary_t95": "#FFECF1",
    "secondary_t99": "#FFFBFF",

    "tertiary_t10": "#2E1500", "tertiary_t20": "#4A2708",
    "tertiary_t30": "#653B1F", "tertiary_t40": "#7C5635",
    "tertiary_t50": "#976E4C", "tertiary_t60": "#B28764",
    "tertiary_t70": "#CEA17D", "tertiary_t80": "#EABB98",
    "tertiary_t90": "#FFDCC2", "tertiary_t95": "#FFEEE0",
    "tertiary_t99": "#FFFBFF",

    "neutral_t10": "#23191C", "neutral_t20": "#392E31",
    "neutral_t30": "#514347", "neutral_t40": "#6A5A5E",
    "neutral_t50": "#847377", "neutral_t60": "#9E8C90",
    "neutral_t70": "#B9A6AA", "neutral_t80": "#D5C2C6",
    "neutral_t90": "#EDDCDF", "neutral_t95": "#F2DDE1",
    "neutral_t99": "#FFFBFF",

    "neutral_variant_t10": "#23191C", "neutral_variant_t20": "#392E31",
    "neutral_variant_t30": "#514347", "neutral_variant_t40": "#6A5A5E",
    "neutral_variant_t50": "#837377", "neutral_variant_t60": "#9E8C90",
    "neutral_variant_t70": "#B9A6AA", "neutral_variant_t80": "#D5C2C6",
    "neutral_variant_t90": "#EDDCDF", "neutral_variant_t95": "#F2DDE1",
    "neutral_variant_t99": "#FFFBFF",
}

# ── Default presets ─────────────────────────────────────────────

NEKO_PINK_PRESET = BASE_THEME_TEMPLATE.copy()

DEEP_DARK_PRESET = {
    "mode": "Dark",

    # Primary — deep magenta-pink (hue ~340)
    "primary":              "#FFB0CB",
    "on_primary":           "#5E0036",
    "primary_container":    "#820049",
    "on_primary_container": "#FFD9E6",

    # Secondary — muted rose-pink
    "secondary":              "#DEBCC6",
    "on_secondary":           "#422931",
    "secondary_container":    "#5B3F47",
    "on_secondary_container": "#FFD9E6",

    # Tertiary — muted warm apricot
    "tertiary":              "#EABB98",
    "on_tertiary":           "#4A2708",
    "tertiary_container":    "#653B1F",
    "on_tertiary_container": "#FFDCC2",

    # Error
    "error":              "#FFB4AB",
    "on_error":           "#690005",
    "error_container":    "#93000A",
    "on_error_container": "#FFDAD6",

    # Surface — dark elevation model (darker = lower)
    "background":           "#1A1113",
    "on_background":        "#EDDCDF",
    "surface":              "#1A1113",
    "on_surface":           "#EDDCDF",
    "surface_variant":      "#514347",
    "on_surface_variant":   "#D5C2C6",
    "surface_container_lowest":  "#120C0E",
    "surface_container_low":     "#23191C",
    "surface_container":         "#271D20",
    "surface_container_high":    "#32272A",
    "surface_container_highest": "#3D3135",
    "surface_bright":            "#392E31",
    "surface_dim":               "#1A1113",

    # Outline
    "outline":          "#9E8C90",
    "outline_variant":  "#514347",

    # Inverse
    "inverse_surface":    "#EDDCDF",
    "inverse_on_surface": "#392E31",
    "inverse_primary":    "#BE0F6E",

    "scrim": "#000000",

    # Legacy aliases
    "main_bg":   "#1A1113",
    "panel_bg":  "#23191C",
    "text":      "#EDDCDF",
    "accent":    "#FFB0CB",

    "btn_add_bg": "#653B1F",  # tertiary_container (dark)
    "btn_add_fg": "#FFDCC2",  # on_tertiary_container
    "btn_now_bg": "#5B3F47",  # secondary_container (dark)
    "btn_now_fg": "#FFD9E6",  # on_secondary_container
    "btn_start_bg": "#FFB0CB",  # primary (dark)
    "btn_start_fg": "#5E0036",  # on_primary

    # Tonal palette reference (Deep Dark)
    "primary_t10": "#3E0021", "primary_t20": "#5E0036",
    "primary_t30": "#820049", "primary_t40": "#A5005C",
    "primary_t50": "#D93989", "primary_t60": "#E969A4",
    "primary_t70": "#F593BF", "primary_t80": "#FFB0CB",
    "primary_t90": "#FFD9E6", "primary_t95": "#FFECF1",
    "primary_t99": "#FFFBFF",

    "secondary_t10": "#2B151C", "secondary_t20": "#422931",
    "secondary_t30": "#5B3F47", "secondary_t40": "#74565F",
    "secondary_t50": "#8E6E77", "secondary_t60": "#A88791",
    "secondary_t70": "#C3A1AB", "secondary_t80": "#DEBCC6",
    "secondary_t90": "#FFD9E6", "secondary_t95": "#FFECF1",
    "secondary_t99": "#FFFBFF",

    "tertiary_t10": "#2E1500", "tertiary_t20": "#4A2708",
    "tertiary_t30": "#653B1F", "tertiary_t40": "#7C5635",
    "tertiary_t50": "#976E4C", "tertiary_t60": "#B28764",
    "tertiary_t70": "#CEA17D", "tertiary_t80": "#EABB98",
    "tertiary_t90": "#FFDCC2", "tertiary_t95": "#FFEEE0",
    "tertiary_t99": "#FFFBFF",

    "neutral_t10": "#23191C", "neutral_t20": "#392E31",
    "neutral_t30": "#514347", "neutral_t40": "#6A5A5E",
    "neutral_t50": "#847377", "neutral_t60": "#9E8C90",
    "neutral_t70": "#B9A6AA", "neutral_t80": "#D5C2C6",
    "neutral_t90": "#EDDCDF", "neutral_t95": "#F2DDE1",
    "neutral_t99": "#FFFBFF",

    "neutral_variant_t10": "#23191C", "neutral_variant_t20": "#392E31",
    "neutral_variant_t30": "#514347", "neutral_variant_t40": "#6A5A5E",
    "neutral_variant_t50": "#837377", "neutral_variant_t60": "#9E8C90",
    "neutral_variant_t70": "#B9A6AA", "neutral_variant_t80": "#D5C2C6",
    "neutral_variant_t90": "#EDDCDF", "neutral_variant_t95": "#F2DDE1",
    "neutral_variant_t99": "#FFFBFF",
}

FRESH_BLUE_PRESET = {
    "mode": "Light",

    # Primary — clean mid-blue (hue ~210)
    "primary":              "#0061A4",
    "on_primary":           "#FFFFFF",
    "primary_container":    "#D1E4FF",
    "on_primary_container": "#001D36",

    # Secondary — muted blue-gray
    "secondary":              "#535F70",
    "on_secondary":           "#FFFFFF",
    "secondary_container":    "#D7E3F7",
    "on_secondary_container": "#101C2B",

    # Tertiary — amber-gold accent (hue ~45)
    "tertiary":              "#6B5733",
    "on_tertiary":           "#FFFFFF",
    "tertiary_container":    "#F5DFA7",
    "on_tertiary_container": "#241A00",

    # Error
    "error":              "#BA1A1A",
    "on_error":           "#FFFFFF",
    "error_container":    "#FFDAD6",
    "on_error_container": "#410002",

    # Surface
    "background":           "#F8F9FF",
    "on_background":        "#191C20",
    "surface":              "#F8F9FF",
    "on_surface":           "#191C20",
    "surface_variant":      "#DFE2EB",
    "on_surface_variant":   "#43474E",
    "surface_container_lowest":  "#FFFFFF",
    "surface_container_low":     "#F1F3FA",
    "surface_container":         "#ECEDF4",
    "surface_container_high":    "#E6E8EF",
    "surface_container_highest": "#E1E2E9",
    "surface_bright":            "#F8F9FF",
    "surface_dim":               "#D8DAE0",

    # Outline
    "outline":          "#73777F",
    "outline_variant":  "#C3C7CF",

    # Inverse
    "inverse_surface":    "#2E3135",
    "inverse_on_surface": "#EFF0F7",
    "inverse_primary":    "#9ECAFF",

    "scrim": "#000000",

    # Legacy aliases
    "main_bg":   "#F8F9FF",
    "panel_bg":  "#DFE2EB",
    "text":      "#191C20",
    "accent":    "#0061A4",

    "btn_add_bg": "#F5DFA7",  # tertiary_container
    "btn_add_fg": "#241A00",  # on_tertiary_container
    "btn_now_bg": "#D7E3F7",  # secondary_container
    "btn_now_fg": "#101C2B",  # on_secondary_container
    "btn_start_bg": "#0061A4",  # primary
    "btn_start_fg": "#FFFFFF",  # on_primary

    # Tonal palette reference (Fresh Blue)
    "primary_t10": "#001D36", "primary_t20": "#003062",
    "primary_t30": "#00468A", "primary_t40": "#0061A4",
    "primary_t50": "#2C7DBD", "primary_t60": "#5698D6",
    "primary_t70": "#7DB3F0", "primary_t80": "#9ECAFF",
    "primary_t90": "#D1E4FF", "primary_t95": "#E8F1FF",
    "primary_t99": "#FBFCFF",

    "secondary_t10": "#101C2B", "secondary_t20": "#253140",
    "secondary_t30": "#3B4858", "secondary_t40": "#535F70",
    "secondary_t50": "#6C7889", "secondary_t60": "#8692A3",
    "secondary_t70": "#A0ACBE", "secondary_t80": "#BCC8DA",
    "secondary_t90": "#D7E3F7", "secondary_t95": "#EBF0FA",
    "secondary_t99": "#FBFCFF",

    "tertiary_t10": "#241A00", "tertiary_t20": "#3E2F0B",
    "tertiary_t30": "#574420", "tertiary_t40": "#6B5733",
    "tertiary_t50": "#85704A", "tertiary_t60": "#9F8963",
    "tertiary_t70": "#BAA37C", "tertiary_t80": "#D6BE96",
    "tertiary_t90": "#F5DFA7", "tertiary_t95": "#FAEFC9",
    "tertiary_t99": "#FBFCFF",

    "neutral_t10": "#191C20", "neutral_t20": "#2E3135",
    "neutral_t30": "#43474E", "neutral_t40": "#5E636B",
    "neutral_t50": "#777C84", "neutral_t60": "#91969E",
    "neutral_t70": "#ACB0B9", "neutral_t80": "#C7CBD4",
    "neutral_t90": "#E1E2E9", "neutral_t95": "#E6E8EF",
    "neutral_t99": "#FBFCFF",

    "neutral_variant_t10": "#191C20", "neutral_variant_t20": "#2E3135",
    "neutral_variant_t30": "#43474E", "neutral_variant_t40": "#5E636B",
    "neutral_variant_t50": "#73777F", "neutral_variant_t60": "#91969E",
    "neutral_variant_t70": "#ACB0B9", "neutral_variant_t80": "#C3C7CF",
    "neutral_variant_t90": "#DFE2EB", "neutral_variant_t95": "#ECEDF4",
    "neutral_variant_t99": "#FBFCFF",
}

DEFAULT_PRESETS = {
    "猫娘粉 (Neko Pink)": NEKO_PINK_PRESET,
    "深邃夜 (Deep Dark)": DEEP_DARK_PRESET,
    "清爽蓝 (Fresh Blue)": FRESH_BLUE_PRESET,
}

# ── Widget Token Mapping ────────────────────────────────────────
# Quick-reference dict: widget_type -> { parameter -> theme_key }
# Use this when styling any CustomTkinter widget to pick the right token.
#
# Example usage in code:
#   from .core.constants import WIDGET_TOKEN_MAP
#   tokens = WIDGET_TOKEN_MAP["ctk_button_primary"]
#   ctk.CTkButton(..., fg_color=theme[tokens["fg_color"]],
#                      text_color=theme[tokens["text_color"]],
#                      hover_color=theme[tokens["hover_color"]])

WIDGET_TOKEN_MAP = {
    # ── Window / TopLevel ────────────────────────────────────────
    "window": {
        "fg_color": "background",
    },

    # ── Main panels (left_panel, right_panel) ────────────────────
    "panel": {
        "fg_color": "surface",
    },

    # ── Cards / elevated containers ──────────────────────────────
    "card": {
        "fg_color": "surface_container",
    },

    # ── Sub-panels / inner frames ────────────────────────────────
    "frame_inner": {
        "fg_color": "surface_container_low",
    },

    # ── Scrollable frames ────────────────────────────────────────
    "scrollable_frame": {
        "fg_color": "transparent",  # or "surface_container_lowest"
    },

    # ── Input fields (CTkEntry) ──────────────────────────────────
    "entry": {
        "fg_color":           "surface_variant",
        "text_color":         "on_surface",
        "placeholder_text_color": "on_surface_variant",
        "border_color":       "outline",
    },

    # ── Combo boxes (CTkComboBox) ────────────────────────────────
    "combobox": {
        "fg_color":           "surface_variant",
        "text_color":         "on_surface",
        "button_color":       "primary",
        "button_hover_color": "primary_t30",
        "border_color":       "outline",
        "dropdown_fg_color":  "surface_container",
        "dropdown_hover_color": "surface_variant",
        "dropdown_text_color":  "on_surface",
    },

    # ── Textbox (CTkTextbox / log box) ───────────────────────────
    "textbox": {
        "fg_color":   "surface_variant",
        "text_color": "on_surface",
        "border_color": "outline_variant",
    },

    # ── Labels ───────────────────────────────────────────────────
    "label_heading": {
        "text_color": "primary",
    },
    "label_body": {
        "text_color": "on_surface",
    },
    "label_muted": {
        "text_color": "on_surface_variant",
    },
    "label_secondary": {
        "text_color": "secondary",
    },

    # ── Primary filled button (e.g. "叼回窝里") ─────────────────
    "button_primary": {
        "fg_color":   "primary",
        "text_color": "on_primary",
        "hover_color": "primary_t30",
    },

    # ── Tertiary filled button (e.g. "放进篮子") ─────────────────
    "button_tertiary": {
        "fg_color":   "tertiary_container",
        "text_color": "on_tertiary_container",
        "hover_color": "tertiary_t80",
    },

    # ── Secondary filled button (e.g. "立即抓取") ────────────────
    "button_secondary_container": {
        "fg_color":   "secondary_container",
        "text_color": "on_secondary_container",
        "hover_color": "secondary_t80",
    },

    # ── Neutral/gray button (e.g. cancel, "算了") ───────────────
    "button_neutral": {
        "fg_color":   "surface_variant",
        "text_color": "on_surface",
        "hover_color": "outline_variant",
    },

    # ── Destructive button (e.g. delete, "全部删除") ─────────────
    "button_destructive": {
        "fg_color":   "error",
        "text_color": "on_error",
        "hover_color": "error_container",
    },

    # ── Success button (e.g. resume, "全部续传") ─────────────────
    "button_success": {
        "fg_color":   "#4CAF50",  # semantic green, not in MD3 tonal
        "text_color": "#FFFFFF",
        "hover_color": "#388E3C",
    },

    # ── Icon/utility small buttons (stats, links) ────────────────
    "button_icon": {
        "fg_color":   "secondary_container",
        "text_color": "on_secondary_container",
        "hover_color": "secondary_t80",
    },

    # ── Progress bar ─────────────────────────────────────────────
    "progress_bar": {
        "progress_color": "primary",
        "fg_color":       "surface_variant",
    },

    # ── Switch / Toggle ──────────────────────────────────────────
    "switch": {
        "progress_color": "primary",
        "text_color":     "on_surface",
    },

    # ── Checkbox ─────────────────────────────────────────────────
    "checkbox": {
        "fg_color":     "primary",
        "border_color": "primary",
        "text_color":   "on_surface",
        "hover_color":  "primary_t30",
    },

    # ── Radio button ─────────────────────────────────────────────
    "radio_button": {
        "fg_color":   "primary",
        "text_color": "on_surface",
        "hover_color": "primary_t30",
    },

    # ── Segmented button (mode selector) ─────────────────────────
    "segmented_button": {
        "selected_color": "primary",
        "selected_hover_color": "primary_t30",
        "unselected_color":     "surface_variant",
        "text_color":           "on_surface",
    },

    # ── Tabview ──────────────────────────────────────────────────
    "tabview": {
        "segmented_button_selected_color": "primary",
        "fg_color":                        "transparent",
    },

    # ── Slider ───────────────────────────────────────────────────
    "slider": {
        "button_color":       "primary",
        "button_hover_color": "primary_t30",
        "progress_color":     "primary",
        "fg_color":           "surface_variant",
    },

    # ── Scrollbar (internal) ─────────────────────────────────────
    "scrollbar": {
        "fg_color":    "outline_variant",
        "button_color": "outline",
    },

    # ── Tooltip / snackbar (inverse surface) ─────────────────────
    "tooltip": {
        "fg_color":   "inverse_surface",
        "text_color": "inverse_on_surface",
    },

    # ── Divider / separator ──────────────────────────────────────
    "divider": {
        "fg_color": "outline_variant",
    },

    # ── Status indicators (non-MD3 semantic colors) ──────────────
    "status_success": {"text_color": "#4CAF50"},
    "status_warning": {"text_color": "#FF9800"},
    "status_error":   {"text_color": "error"},
    "status_info":    {"text_color": "primary"},
    "status_running": {"text_color": "#FFA500"},
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
