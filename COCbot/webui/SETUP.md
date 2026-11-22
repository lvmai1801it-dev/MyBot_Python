# Web UI (pywebview — renderer-agnostic)

Giao diện web chạy trong cửa sổ desktop qua **pywebview** (engine
WebView2/EdgeChromium). Backend Python giữ nguyên toàn bộ runtime của bot
— JS chỉ gọi API qua bridge `pywebview.api.*`.

> **Ghi chú kiến trúc (2026-11-22):** stack React/Vite/shadcn
> (`frontend/`) đã được gỡ để chuyển sang cách tiếp cận
> **catalog-driven** — giao diện được sinh ra từ một danh mục cấu trúc
> (catalog) thay vì code tay từng component + node_modules. Bản React
> cuối cùng (kèm tab AttackPlan) vẫn nằm trong git history ở commit
> `c4741c9` nếu cần tham khảo. Bridge Python dưới đây không đổi —
> renderer mới cắm thẳng vào.

## Lệnh chạy

```powershell
Start_WebUI.bat                          # double-click
# hoặc:
.\.venv\Scripts\python.exe run_web.py
```

Trang: `COCbot/webui/index.html` (kèm sẵn trong repo, không cần build).
Muốn xem trang dev khác (vd. preview catalog): đặt `WEBUI_DEV_URL`
trong `.env` (copy từ `.env.example`).

## Workflow env

`COCbot/webui/.env` (file thật nằm trong .gitignore, biến shell luôn
thắng giá trị trong file):

```ini
WEBUI_DEV_URL=              # trống = dùng webui/index.html
WEBUI_WIDTH=480
WEBUI_HEIGHT=860
```

## Bridge API (JS → Python)

`window.pywebview.api` sẵn sàng sau event `pywebviewready`:

| Phương thức | Trả về | Ghi chú |
|---|---|---|
| `get_state()` | `{running, paused, host, stopped}` | poll ~1.2s cho status bar |
| `get_settings()` | settings.json (hoặc default) | nạp form lúc mở |
| `save_settings(form)` | `{ok, settings}` | merge + ghi settings.json |
| `get_logs(after)` | `{lines, index}` | poll ~0.6s; truyền `index` lần trước |
| `start(form)` | `{ok, reason?, error?}` | tự dò MEmu → chạy bot_loop |
| `stop()` / `pause()` / `resume()` | `{ok}` | cooperative qua stop/pause event |

Form `start(form)` nhận các key ngưỡng/toggle (`gold_threshold`,
`elixir_threshold`, `dark_elixir_threshold`, `attack_side`,
`drop_spells`, `check_troops`); mọi key khác của settings.json được
giữ nguyên phía Python (danh sách `_PRESERVED_KEYS` trong `app.py`).

## Ghi chú kiến trúc

- Backend không có Qt: worker là `threading.Thread` chạy
  `bootstrap.bot_loop(cfg)`, log stream qua ring-buffer (stdout redirect)
  → JS poll. Không cần signal/slot nào.
- `COCbot/app/emulator_detect.py` là logic dò MEmu dùng chung bởi cả
  GUI Qt (`choose_emulator`) và web UI (`BotApi.start`).
- GUI Qt (`run.py`) giữ nguyên là entry mặc định — không đụng gì vào đây.
