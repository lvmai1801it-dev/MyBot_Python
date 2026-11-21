# Templates/ — phân loại & quy tắc

Mỗi ảnh ở đây **được code tham chiếu theo đúng vị trí**. Muốn kiểm chứng lại
sau khi thêm/xoá: `python tools/audit_template_refs.py` (liệt kê file không
được tham chiếu) và `python tools/audit_templates.py` (phát hiện ảnh trùng
hash).

## Bố cục

| Thư mục / vị trí | Dùng bởi | Ghi chú |
|---|---|---|
| `./` (gốc) | UI + điều hướng runtime | `next_button`, `end_battle`, `btn_close`, `close_button_*`, `shop_new`, `settings_logo`, `store_home_page(_LD)`, `gold/elixir/DE_collector(_full)`, `hammer`, `events`, `clan_games`, `open_button(_2)`, `disconnected`, icon cho GUI (`icon_*`, `ui_check`, `ui_radio`, `coc_icon`), hero thanh quân (`bk`, `queen`, `warden`, `rc`), wall map-scan (`wall*.png`) |
| `Smart_Auto_train/Army Troops/` | `attack/army.py` (quét thanh quân), GUI Army tab | icon quân — bộ chuẩn duy nhất |
| `Smart_Auto_train/Spells/` | như trên | icon phép |
| `Smart_Auto_train/Siege Machines/` | như trên | icon siege |
| `Smart_Auto_train/to_train/` | `troop_registry.train_template_file` → smart train | ảnh nút quân trong cửa sổ train |
| `Smart_Auto_train/Train_Tab/` | `smart_train_trainers.tap_icon_in_tab` | nút tab trong cửa sổ train |
| `Smart_Auto_train/edit_army_btn.png` | `smart_train_validators` | nút "Edit Army" (được gọi không kèm đuôi `.png`) |
| `Smart_Auto_train/use_button.png` | `quick_train` | nút Use của recipe |
| `Clan Capital/Scenery/` | `capital._scan_all_cc_templates` (`{i}.png`, 1..44) | nhận diện vị trí làng capital |
| `Clan Capital/Troops/`, `Clan Capital/Spells/` | `capital` deploy | icon quân deploy capital |
| `Clan Games/` | `games.choose_game` (quét cả thư mục) | tile chọn mini-game |
| `upgrade/` + `upgrade/hero/` | `features/village/upgrades.py` | nút Upgrade/CONFIRM/Close + chân dung hero |
| `buildings/` | `features/village` (panel label) | nhãn dòng trong Build panel |

## Quy tắc thêm ảnh mới

1. Đặt vào đúng thư mục chức năng ở bảng trên; ảnh điều hướng runtime đặt
   ở gốc (vì `TemplateMatcher`/`os.path.join(TEMPLATE_DIR, ...)` resolve
   theo gốc).
2. Tên file bằng chữ thường + gạch dưới (không khoảng trắng, không
   `cropped_<timestamp>`).
3. Chạy `python tools/audit_template_refs.py` — ảnh mới phải nằm trong tập
   "referenced/kept", không được rơi vào "deletion candidates".
4. Nếu code gọi tên **không kèm đuôi** (như `edit_army_btn` qua
   `find_template_path`), thêm tên đó vào `EXTRA_REFERENCED` trong
   `tools/audit_template_refs.py` để audit không báo nhầm.

## Đã dọn (2026-11-21)

- 241 ảnh chết (63 MB): bản sao icon quân ở gốc trùng `to_train/`, bộ
  chữ số `numbers/` + digit rải rác (đường OCR cũ), `s_troops/` (icon
  capital thế hệ cũ), `BG*.png` (3 ảnh nền ~4.8 MB), ảnh màn hình tham khảo
  `Clan Capital/Clan Capital Attack locations` (45 MB) và
  `Attacks enemy village` (3 MB) không có code nào dùng, các nút của luồng
  Supercell-ID đã xoá (`supercell_ID`, `switch_button`), icon GUI bỏ
  (`icon_hourglass`, `icon_target`, `highres_logo`, `coc_logo`...).
- 72 MB → 8.5 MB; 610 → 369 file; còn lại 0 nhóm trùng hash.
