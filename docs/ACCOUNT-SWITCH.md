# CHUYỂN ACCOUNT BẰNG SHARED_PREFS

Bot chỉ dùng **shared_prefs** để chuyển account. Không còn Supercell ID,
không cần thao tác trên màn hình Switch Account của game.

---

## 1. Yêu cầu

- `adb shell id` trả `uid=0` (MEmu/LDPlayer thường có adbd root sẵn).
- Không cần root thủ công, không cần `su`.
- Cùng package:
  ```text
  com.supercell.clashofclans
  ```
- Nên dùng cùng emulator/instance.
- **Stop bot** trước khi Pull/Push/Switch.

Nếu `adb shell id` không phải `uid=0`:
- bật `adb root` cho emulator, hoặc
- dùng emulator/instance khác có adbd root.

---

## 2. UI tab Accounts

```text
Profile: [combo profile]  [Pull] [Push] [Switch] [Refresh] [Delete]
Current: ...
root: adbd root sẵn có
```

- **Pull**: lưu shared_prefs của account đang mở trong game thành profile.
- **Push**: đưa profile đang chọn vào game (game sẽ restart).
- **Switch**: Pull account hiện tại trước, rồi Push profile đích.
- **Refresh**: tải lại danh sách profile.
- **Delete**: xoá profile đang chọn.

Trạng thái dưới cùng hiển thị kết quả thao tác gần nhất.

---

## 3. Quy trình tạo profile

1. Đăng nhập account 1 trong CoC, về Home Base.
2. Stop bot.
3. Tab **Accounts** → chọn/nhập tên profile → **Pull**.
4. Đổi account trong game (thủ công) → lặp lại Pull với tên khác.
5. Chọn profile → **Push** hoặc **Switch**.

File lưu:

```text
profiles/accounts/
├── acc_chinh/
│   ├── shared_prefs/
│   │   ├── storage_new.xml
│   │   └── ...
│   └── meta.json
└── acc_phu/
    └── ...
```

---

## 4. Auto switch

Bật **Enable Switch Accounts**. Điều kiện nào tới trước sẽ chuyển:

- **By attacks**: mỗi account có ô **Trận** riêng.
  - `0` = dùng số mặc định ở ô **Attacks / acc**.
- **By time**: sau X phút kể từ lần chuyển gần nhất.
- **By full 3 storages**: khi cả 3 kho (vàng, tiêu, DE) đầy.
  - Template trong `Templates/*_collector_full.png`.
  - Nếu không còn account khác: treo online và kiểm tra lại sau **Wait** phút.

### Hành vi khi mới Start

- Bot **dùng account đang mở sẵn trong game**.
- **Không tự chuyển account** chỉ vì trước đó đã hết thời gian.
- Bộ đếm trận reset; mốc thời gian được đặt lại khi bắt đầu phiên.
- Chỉ chuyển khi thực sự thỏa điều kiện ở trên.

---

## 5. Cấu hình

`profiles/switch_accounts.json`:

```json
{
  "enabled": true,
  "consecutive_attacks": 2,
  "use_attack_limit": true,
  "use_time_schedule": false,
  "use_storage_full": false,
  "storage_full_wait_minutes": 10,
  "schedule_minutes": 60,
  "last_switch_ts": 0,
  "total_accounts": 3,
  "current_profile": "MaiCongChua",
  "accounts": [
    {"enabled": true, "profile": "Mai 001", "attacks": 5},
    {"enabled": true, "profile": "MaiCongChua", "attacks": 10},
    {"enabled": true, "profile": "Thanh", "attacks": 0}
  ]
}
```

---

## 6. Lưu ý

- Không chạy Pull/Push/Switch khi bot đang chạy.
- Can thiệp dữ liệu game có thể vi phạm điều khoản Supercell; tự cân nhắc.
- Nếu adbd root không ổn định, kiểm tra lại kết nối ADB trước khi thao tác.
