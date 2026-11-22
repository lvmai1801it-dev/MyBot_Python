"""UI catalog — nguồn duy nhất của giao diện web (thuần Python).

Sửa UI = sửa file này. ``render.py`` sinh HTML/CSS/JS từ catalog và
``app.py`` nạp trang đã sinh vào pywebview — không có HTML/JS viết tay,
không node_modules, không build step.

Đồng bộ được bảo vệ bằng test (``tests/unit/test_webui_catalog.py``):
mọi field trong catalog phải có type renderer hỗ trợ và tên khớp với
settings.json mà BotApi đọc/ghi.
"""

from __future__ import annotations

TITLE = "MRB VM BOT MOD"

# Design tokens: renderer nhét thẳng vào CSS variables của trang.
THEME = {
    "bg": "#F2F5F3",
    "header": "#142C2B",
    "card": "#FFFFFF",
    "primary": "#13775F",
    "warn": "#B8860B",
    "danger": "#B3452E",
    "border": "#DCE5E1",
    "text": "#193431",
    "muted": "#6B7F7A",
    "log_bg": "#10231F",
    "log_fg": "#C9E6DD",
}

WINDOW = {"width": 480, "height": 860}

SIDE_OPTIONS = [
    "Ngẫu nhiên",
    "Trên Trái (TL)",
    "Trên Phải (TR)",
    "Dưới Trái (BL)",
    "Dưới Phải (BR)",
    "Nửa Trên (TL + TR)",
    "Nửa Dưới (BL + BR)",
    "Cả 4 hướng (+)",
]

# Thẻ điều khiển luôn hiển thị trên cùng (renderer đặt tự động).
CONTROL_CARD = {
    "title": "Điều khiển",
    "buttons": [
        {"id": "start", "label": "Start", "style": "primary"},
        {"id": "pause", "label": "Pause", "style": "warn"},
        {"id": "stop", "label": "Stop", "style": "danger"},
    ],
    "status": True,  # dòng trạng thái (running/paused/host)
}

# Mỗi tab là một danh mục card; field là khai báo thuần Python.
TABS = [
    {
        "id": "farm",
        "label": "⚔ Farm",
        "cards": [
            {
                "title": "Ngưỡng loot (mới đánh)",
                "fields": [
                    {"name": "gold_threshold", "type": "number",
                     "label": "Gold", "default": 65000},
                    {"name": "elixir_threshold", "type": "number",
                     "label": "Elixir", "default": 65000},
                    {"name": "dark_elixir_threshold", "type": "number",
                     "label": "Dark Elixir", "default": 500},
                ],
            },
            {
                "title": "Hướng thả quân",
                "fields": [
                    {"name": "attack_side", "type": "select",
                     "label": "Hướng", "options": SIDE_OPTIONS,
                     "default": "Ngẫu nhiên"},
                ],
            },
            {
                "title": "Tùy chọn đánh",
                "fields": [
                    {"name": "drop_spells", "type": "switch",
                     "label": "Thả spell", "default": False},
                    {"name": "check_troops", "type": "switch",
                     "label": "Check quân trước khi đánh", "default": False},
                ],
            },
        ],
    },
    {
        "id": "village",
        "label": "🏠 Village",
        "cards": [
            {
                "title": "Nâng tường",
                "fields": [
                    {"name": "upgrade_wall", "type": "switch",
                     "label": "Bật nâng tường", "default": False},
                    {"name": "wall_level", "type": "number",
                     "label": "Level tường", "default": 5},
                    {"name": "wall_gold_threshold", "type": "number",
                     "label": "Ngưỡng gold", "default": 5_000_000},
                    {"name": "wall_elixir_threshold", "type": "number",
                     "label": "Ngưỡng elixir", "default": 5_000_000},
                ],
            },
        ],
    },
    {
        "id": "clan",
        "label": "🛡 Clan",
        "cards": [
            {
                "title": "Clan Games / Capital",
                "fields": [
                    {"name": "enable_clan_games", "type": "switch",
                     "label": "Clan Games", "default": False},
                    {"name": "enable_clan_capital", "type": "switch",
                     "label": "Clan Capital", "default": False},
                    {"name": "capital_hall_level", "type": "number",
                     "label": "Capital Hall level", "default": 9},
                ],
            },
            {
                "title": "Clan chat",
                "fields": [
                    {"name": "request_troops", "type": "switch",
                     "label": "Tự xin quân", "default": True},
                ],
            },
        ],
    },
    {
        "id": "log",
        "label": "📜 Log",
        "special": "log",  # renderer thay bằng pane log + poll get_logs
    },
]
