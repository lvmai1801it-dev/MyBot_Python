# Web UI — Catalog-driven, thuần Python (pywebview)

Giao diện web chạy trong cửa sổ desktop qua **pywebview** (engine
WebView2/EdgeChromium). **Không có HTML/JS viết tay, không node_modules,
không build step** — trang được *sinh* từ catalog Python mỗi lần mở app.

> **Kiến trúc (2026-11-22):** stack React/Vite/shadcn đã gỡ (snapshot
> cuối trong git history ở `c4741c9`). Cách làm hiện tại:
>
> ```text
> COCbot/webui/catalog.py    <- SỬA UI Ở ĐÂY (thuần Python)
> COCbot/webui/render.py     <- renderer: catalog -> HTML/CSS/JS
> COCbot/webui/_generated/   <- trang sinh ra khi mở app (gitignored)
> COCbot/webui/app.py        <- bridge BotApi (không đổi qua các lần đổi UI)
> ```

## Sửa UI thế nào

Mở `catalog.py` và thêm/sửa khai báo — không file nào khác cần đụng:

```python
TABS = [
    {"id": "farm", "label": "⚔ Farm", "cards": [
        {"title": "Ngưỡng loot", "fields": [
            {"name": "gold_threshold", "type": "number",
             "label": "Gold", "default": 65000},
            {"name": "drop_spells", "type": "switch",
             "label": "Thả spell", "default": False},
            {"name": "attack_side", "type": "select",
             "label": "Hướng", "options": SIDE_OPTIONS},
        ]},
    ]},
    {"id": "log", "label": "📜 Log", "special": "log"},
]
```

- `type` hỗ trợ: `number`, `select`, `switch`.
- `name` **phải là key của settings.json** — renderer sinh form và
  `start(form)` gửi nguyên key đó qua bridge; mọi key khác của
  settings.json được Python giữ nguyên (`_PRESERVED_KEYS` trong `app.py`).
- `special: "log"` = pane log; `CONTROL_CARD` = thẻ Start/Pause/Stop.
- Màu/size: `THEME` (CSS variables) + `WINDOW` (kích thước cửa sổ).
- Đồng bộ được bảo vệ bởi `tests/unit/test_webui_catalog.py`: khai báo
  sai type, thiếu options, trùng tên field, hoặc renderer bỏ sót field
  nào đó → test đỏ ngay, không cần mở app.

## Lệnh chạy

```powershell
Start_WebUI.bat                          # double-click
# hoặc:
.\.venv\Scripts\python.exe run_web.py    # sinh trang từ catalog rồi mở
```

## Workflow env

`COCbot/webui/.env` (copy từ `.env.example`; file thật gitignored, biến
shell luôn thắng file):

```ini
WEBUI_DEV_URL=              # trống = dùng trang sinh từ catalog
WEBUI_WIDTH=480
WEBUI_HEIGHT=860
```

## Bridge API (sinh tự động trong trang, gọi trực tiếp nếu cần)

`window.pywebview.api` sau event `pywebviewready`:

| Phương thức | Trả về |
|---|---|
| `get_state()` | `{running, paused, host, stopped}` |
| `get_settings()` | settings.json (hoặc default) |
| `save_settings(form)` | `{ok, settings}` |
| `get_logs(after)` | `{lines, index}` — poll, truyền `index` lần trước |
| `start(form)` | `{ok, reason?, error?}` — tự dò MEmu → chạy bot_loop |
| `stop()` / `pause()` / `resume()` | `{ok}` |

## Kiểm thử

```powershell
.venv\Scripts\python.exe -m unittest tests.unit.test_webui_catalog -v
```
