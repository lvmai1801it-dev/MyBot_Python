# CHUYỂN ACCOUNT (theo MyBot)

Có 2 chế độ, giống MyBot:

| Mode | Cần root? | Cách hoạt động |
|---|---|---|
| **Supercell ID** (mặc định) | **Không** | Dùng màn hình Switch Account trong game |
| **Shared_prefs** | Dùng adbd root sẵn có | Copy/restore `/data/data/com.supercell.clashofclans/shared_prefs` |

MyBot mặc định dùng **Supercell ID**. Shared_prefs không cần bạn root thủ công:
MEmu/LDPlayer thường có **adbd root sẵn** (`adb shell id` = `uid=0`).
Nếu emulator không có adbd root, dùng Supercell ID.

---

## A. Supercell ID (không cần root)

### UI

Tab **Accounts**:

```text
Mode: (o) Supercell ID   ( ) Shared_prefs
Slot: [1]
[Switch now]
```

- `Slot 1-5` tương ứng thứ tự account trong màn hình **Switch Account** của game.
- Không dùng Pull/Push; các nút đó bị disable.
- `Switch now` gọi `switch_to_village(slot)`:
  - Mở Settings
  - Bấm Switch Account
  - Chọn account theo slot
  - Chờ load

### Auto switch

Bật **Enable Switch Accounts**, chọn **Supercell ID**, tick các slot trong bảng.

Trigger có thể chọn (có thể bật nhiều cái; cái nào tới trước sẽ switch):

- **By attacks**: mỗi account có ô **Trận** riêng trong bảng.
  - `0` = dùng số mặc định ở ô **Attacks / acc**.
  - Ví dụ Acc 1 = 4, Acc 2 = 7, Acc 3 = 12 → mỗi acc đánh đủ số đó rồi đổi.
- **By time, every X min**: sau X phút, kể cả khi không đánh.
- **By full 3 storages**: khi cả 3 kho (vàng, tiêu, DE) đầy thì đổi acc.
  - Dùng OpenCV template matching với `gold_collector_full.png`,
    `elixir_collector_full.png`, `DE_collector_full.png` trong `Templates/`.
  - Nếu **không còn account khác**, bot treo online và kiểm tra lại sau
    **Wait: X min** (mặc định 10 phút). Bấm Stop để thoát ngay.
  - Ngưỡng mặc định `0.85`; chỉnh trong `profiles/switch_accounts.json`:
    `storage_full_threshold`, `storage_full_min_matches`.

```text
return_home()
→ ensure_home_base()
→ switch_to_village(next_slot)
```

Không cần root, không đụng shared_prefs.

---

## B. Shared_prefs (dùng adbd root sẵn có)

### Yêu cầu

- `adb shell id` trả `uid=0` (MEmu/LDPlayer thường mặc định như vậy).
  Không cần root thủ công, không cần `su`.
- Nếu `adb shell id` không phải `uid=0`, dùng **Supercell ID** hoặc bật `adb root`.
- Cùng package:
  ```text
  com.supercell.clashofclans
  ```
- Nên dùng cùng emulator/instance (file chứa Android ID).
- **Stop bot** trước khi Pull/Push/Switch.

### UI

```text
Profile: [profile combo] [Pull current] [Push selected] [Switch now] [Refresh] [Delete]
Current: ...
root: adbd (uid=0)

Mode: ( ) Supercell ID   (o) Shared_prefs
```

### Quy trình

1. Đăng nhập account 1 trong CoC, về Home Base.
2. Stop bot.
3. Tab **Accounts** → nhập tên profile, bấm **Pull current**.
4. Đăng nhập account 2 trong game → lặp lại với tên khác.
5. Chọn profile → **Push selected** hoặc **Switch now**.

### File lưu

```text
profiles/accounts/
├── acc_chinh/
│   ├── shared_prefs/
│   │   ├── storage_new.xml
│   │   └── ...
│   └── meta.json
└── acc_phu/
    ├── shared_prefs/
    └── meta.json
```

`meta.json` lưu tên, package, thời gian, Android ID, host, số file.

### Pull / Push

Pull:

```text
force-stop CoC
→ lấy /data/data/com.supercell.clashofclans/shared_prefs
→ lưu vào profiles/accounts/<name>/shared_prefs
→ mở lại CoC
```

Push:

```text
force-stop CoC
→ (nếu có current_profile) Pull account hiện tại trước
→ cập nhật storage_new.xml (language/zoom/rated)
→ copy profile vào /data/data/.../shared_prefs
→ chown/chmod/restorecon
→ mở lại CoC
```

Switch = Pull current + Push target.

### storage_new.xml

Giống MyBot:

```text
d0h6phQUOxO/uSfvat949w== -> FWCNTu39RUlYoSt0Y6mCwg==   language
MjhxqoFNUV+begGvsz3gkg== -> vJsDdCCIGCzyfC7c1FsIrA==   zoom
7lJCTt3TmNyzikZuHh9wZQ== -> pmvEzdQuRQuKZob4KB0IeA==   rated
```

### Auto switch

Trigger:

- **By attacks**: sau N trận.
- **By time, every X min**: sau X phút.
- Bật cả hai: điều kiện nào tới trước sẽ switch.

```text
Pull current_profile (lưu tiến độ account hiện tại)
→ Push profile kế tiếp
→ cập nhật current_profile
→ reset bộ đếm / timer
```

Cấu hình: `profiles/switch_accounts.json`:

```json
{
  "enabled": true,
  "mode": "shared_prefs",
  "use_attack_limit": true,
  "consecutive_attacks": 2,
  "use_time_schedule": true,
  "schedule_minutes": 60,
  "last_switch_ts": 0
}
```

---

## C. So sánh với MyBot

| Tính năng | MyBot | Bản này |
|---|---|---|
| Supercell ID switch | ✅ mặc định | ✅ |
| Shared_prefs switch | ✅ tùy chọn | ✅ |
| Pull/Push folder | ✅ | ✅ |
| storage_new update | ✅ | ✅ |
| Auto switch theo trận | ✅ | ✅ (cả 2 mode) |
| Auto switch theo giờ | ✅ | ✅ (cả 2 mode) |
| Switch While Waiting | ✅ | Lưu config, chưa tự động |
| Group 1–8 | ✅ | Chưa; 1 danh sách |

## D. Lưu ý

- Supercell ID mode phụ thuộc UI game; nếu Supercell đổi giao diện, cần cập nhật
  template/coords (`ready_villages.py`).
- Shared_prefs backup chứa thông tin đăng nhập cục bộ → **không chia sẻ**.
- Can thiệp dữ liệu game có thể vi phạm điều khoản Supercell; tự cân nhắc.
