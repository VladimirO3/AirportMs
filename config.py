"""Centralized application configuration."""

from pathlib import Path


APP_TITLE = "Диспетчерская служба аэропорта"
APP_COPYRIGHT = "© 2026 AirportMs"
LOGIN_TITLE = "Вход в диспетчерскую службу"
APP_ICON_PATH = Path(__file__).with_name("app.ico")

DEFAULT_LOGIN = "admin"
DEFAULT_PASSWORD = "admin"

MAIN_GEOMETRY = "1100x650"
MAIN_MIN_WIDTH = 900
MAIN_MIN_HEIGHT = 550
LOGIN_GEOMETRY = "420x280"
SPLASH_GEOMETRY = "520x300"
SPLASH_DURATION_MS = 1800
INACTIVITY_TIMEOUT_MS = 5 * 60 * 1000
REPORT_GEOMETRY = "1050x600"
REPORT_MIN_WIDTH = 760
REPORT_MIN_HEIGHT = 450
PREVIEW_GEOMETRY = "850x600"
PREVIEW_MIN_WIDTH = 650
PREVIEW_MIN_HEIGHT = 420
HELP_GEOMETRY = "760x500"
HELP_MIN_WIDTH = 620
HELP_MIN_HEIGHT = 400

COLORS = {
    "background": "#eaf4ff",
    "button": "#cfeeff",
    "button_active": "#b8e5ff",
    "button_pressed": "#9fd8f5",
    "text": "#174a6e",
    "text_active": "#123b58",
    "muted_text": "#4b6b80",
    "tab_selected": "#a9dcf5",
    "table": "#ffffff",
}

FLIGHT_DATETIME_FORMAT = "%Y-%m-%d %H:%M"
