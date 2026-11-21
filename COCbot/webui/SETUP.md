# Web UI (pywebview + React + Tailwind + shadcn/ui)

Giao diện web chạy trong cửa sổ desktop qua **pywebview** (engine
WebView2/EdgeChromium). Backend Python giữ nguyên toàn bộ runtime của bot
— JS chỉ gọi API qua bridge `pywebview.api.*`.

## Lệnh chạy

**Một click** (convention giống `Start_GLM_OCR.bat`):

- `Start_WebUI_Dev.bat` — Vite dev server + pywebview trỏ vào nó
  (hot reload khi bạn đang code UI). Không cần gõ biến môi trường.
- `Start_WebUI.bat` — `npm run build` + mở pywebview bằng bản dist.

Hoặc thủ công:

```powershell
.\.venv\Scripts\python.exe run_web.py      # mở cửa sổ web UI
```

## Workflow env

`COCbot/webui/.env` (copy từ `.env.example`; file thật nằm trong
.gitignore, biến shell luôn thắng giá trị trong file):

```ini
WEBUI_DEV_URL=              # trống = dùng bản build; đặt http://localhost:5173 khi dev
WEBUI_WIDTH=480
WEBUI_HEIGHT=670
```

Trang được chọn theo thứ tự:

1. `WEBUI_DEV_URL` (env / .env) — Vite dev server
2. `frontend/dist/index.html` — bản build React (`npm run build`)
3. `webui/index.html` — trang fallback không cần build (được viết sẵn,
   chỉ để dự phòng khi chưa có dist)

## Dev loop (cho bạn code UI)

```powershell
Start_WebUI_Dev.bat
# hoặc tay:
cd COCbot\webui\frontend ; npm run dev
# terminal 2:
$env:WEBUI_DEV_URL='http://localhost:5173'
.\.venv\Scripts\python.exe run_web.py
```

Dev server đang bật thì **KHÔNG bấm Start bot** trong cùng cửa sổ đó —
JS bridge vẫn hoạt động, nhưng để tránh nhầm lẫn giữa 2 phiên bản trang,
nên test bot bằng bản build.

## Build

```powershell
cd COCbot\webui\frontend
npm run build        # -> dist/, pywebview tự dùng bản này (bỏ env WEBUI_DEV_URL)
```

Lưu ý `vite.config.ts` đã đặt `base: './'` — bắt buộc để bản build nạp
được qua `file://` trong pywebview. **Đừng xoá dòng này.**

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

## Dark mode

Theme CSS của shadcn (preset `mira`) đã có sẵn block `.dark`. Muốn mặc
đèn tối: đặt class trên `<html>`:

```tsx
// index.html: <html lang="vi" class="dark">
```

và dùng component theo biến `dark:` của Tailwind khi cần chốt từng chỗ.

## Ghi chú kiến trúc

- Backend không có Qt: worker là `threading.Thread` chạy
  `bootstrap.bot_loop(cfg)`, log stream qua ring-buffer (stdout redirect)
  → JS poll. Không cần signal/slot nào.
- `COCbot/app/emulator_detect.py` là logic dò MEmu dùng chung bởi cả
  GUI Qt (`choose_emulator`) và web UI (`BotApi.start`).
- GUI Qt (`run.py`) giữ nguyên là entry mặc định — không đụng gì vào đây.
