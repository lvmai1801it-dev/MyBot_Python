# src/gui/debug_tab.py
import os
import subprocess
import sys
import threading
import time

from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from COCbot.emulator.adb_config import ADB_BIN

from COCbot.core import main
from COCbot.attacks.attacks import run_attack
from COCbot.core.coords import ATTACK_CONFIRM_TAP
from COCbot.routines.ensure_home_base import ensure_home_base
from COCbot.routines.IsTarget import extract_resources
from COCbot.emulator.adb_utils import tap # Import đúng hàm tap

CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0

# ============================================================
# LỚP BẮT LOG AN TOÀN (Dùng Signal thay vì gọi trực tiếp UI)
# ============================================================
class EmittingStream(QObject):
    textWritten = pyqtSignal(str)

    def write(self, text):
        self.textWritten.emit(str(text))

    def flush(self):
        pass

class DebugTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_running = False
        self._build_ui()
        
        # Thiết lập bắt log an toàn qua Signal
        self.stream = EmittingStream()
        self.stream.textWritten.connect(self.append_log)
        
        # Lưu lại stdout cũ và ghi đè bằng stream mới
        self.original_stdout = sys.stdout
        sys.stdout = self.stream

    def _build_ui(self):
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(10, 10, 10, 10)
        vbox.setSpacing(10)

        # --- PHẦN 1: NÚT TEST TÍNH NĂNG ---
        group_tests = QGroupBox("Bảng Điều Khiển Test Tính Năng")
        group_tests.setStyleSheet("QGroupBox { color: #eee; font-weight: bold; border: 1px solid #555; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        
        grid = QGridLayout(group_tests)
        grid.setSpacing(10)

        # Danh sách các nút test (Tên hiển thị, Module, Tên hàm)
        # Sử dụng "self" làm module_name để báo hiệu gọi hàm nội bộ trong class
                # Danh sách các nút test (Tên hiển thị, Module, Tên hàm)
        self.buttons_config = [
            ("1. Kiểm Tra Home Base", "routines.ensure_home_base", "ensure_home_base"),
            ("2. Xin Quân (Request Troops)", "routines.request_troops", "auto_request"),
            ("3. Thu Hoạch Tài Nguyên", "routines.Tap_Collectors", "find_and_tap_collectors"),
            ("4. Đọc Tài Nguyên Đối Thủ", "routines.IsTarget", "extract_resources"),
            ("5. Tìm Trận Đánh", "main", "search_attack"),
            ("6. Chờ Màn Hình Dò Làng", "main", "wait_for_scout_screen"),
            ("7. Khởi Động Lại Game", "routines.boot_recovery", "boot_recovery"),
            ("8. Train Quân (Smart)", "routines.smart_train", "smart_train"),
            # Nút số 9 gọi hàm test_full_attack nội bộ trong class
            ("9. Test Toàn Bộ Trận Đánh", "self", "test_full_attack"),
        ]

        row, col = 0, 0
        for text, module_name, func_name in self.buttons_config:
            btn = QPushButton(text)
            # Nút số 9 sẽ có màu khác để dễ nhận biết
            if "9." in text:
                btn.setStyleSheet("background: #E91E63; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
            else:
                btn.setStyleSheet("background: #2196F3; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
            
            btn.clicked.connect(lambda checked, m=module_name, f=func_name, t=text: self.run_test(t, m, f))
            grid.addWidget(btn, row, col)
            
            col += 1
            if col > 1: # 2 cột
                col = 0
                row += 1

        vbox.addWidget(group_tests)

        # --- PHẦN 2: LOG OUTPUT ---
        vbox.addWidget(QLabel("Nhật ký hoạt động (Log):"))
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: Consolas, monospace; font-size: 12px;")
        vbox.addWidget(self.txt_log, 1) # stretch=1 để log chiếm toàn bộ phần còn lại

        # Nút xóa log
        btn_clear_log = QPushButton("Xóa nhật ký")
        btn_clear_log.clicked.connect(self.txt_log.clear)
        vbox.addWidget(btn_clear_log)

    def append_log(self, text):
        """Hàm nhận log từ luồng khác và in lên giao diện (An toàn)"""
        self.txt_log.insertPlainText(text)
        self.txt_log.moveCursor(QTextCursor.End)

    def _ensure_connection(self):
        import main
        if getattr(main, "host", None):
            return True

        print("[DEBUG] Chưa có kết nối ADB. Đang tự động quét tìm giả lập...")
        try:
            subprocess.run([str(ADB_BIN), "start-server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
            out = subprocess.check_output([str(ADB_BIN), "devices"], text=True, creationflags=CREATE_NO_WINDOW)
            lines = out.strip().split('\n')[1:]
            for line in lines:
                if "device" in line and "offline" not in line:
                    host = line.split('\t')[0].strip()
                    if host:
                        main.host = host
                        print(f"[DEBUG] Tự động kết nối thành công tới: {host}")
                        return True
        except Exception:
            pass

        common_hosts = ["127.0.0.1:21503", "127.0.0.1:5556", "127.0.0.1:5555"]
        for h in common_hosts:
            try:
                subprocess.run([str(ADB_BIN), "connect", h], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
                out = subprocess.check_output([str(ADB_BIN), "-s", h, "shell", "echo", "1"], text=True, creationflags=CREATE_NO_WINDOW)
                if "1" in out:
                    main.host = h
                    print(f"[DEBUG] Tự động kết nối thành công tới: {h}")
                    return True
            except Exception:
                continue
        return False

    def run_test(self, btn_text, module_name, func_name):
        if self.is_running:
            QMessageBox.warning(self, "Cảnh báo", "Đang có một tiến trình test chạy. Vui lòng đợi nó xong!")
            return

        self.is_running = True
        print(f"\n{'='*50}\n🚀 BẮT ĐẦU TEST: {btn_text}\n{'='*50}")

        # Chạy trong Thread riêng để không treo giao diện
        threading.Thread(target=self._execute_task, args=(module_name, func_name), daemon=True).start()

    def _execute_task(self, module_name, func_name):
        try:
            if not self._ensure_connection():
                print("❌ Không tìm thấy giả lập nào đang bật! Hãy mở MEmu/BlueStacks trước.")
                self.is_running = False
                return

            import importlib
            if module_name == "self":
                # Gọi hàm nội bộ trong class (dành cho nút 9)
                func = getattr(self, func_name)
            else:
                mod = importlib.import_module(module_name)
                func = getattr(mod, func_name)

            if func_name in ["smart_train", "quick_train"]:
                print(f"⚠️ Hàm {func_name} yêu cầu tham số 'cfg' (config). Bỏ qua test.")
            else:
                result = func()
                print(f"✅ Test hoàn tất. Kết quả trả về: {result}")

        except Exception as e:
            print(f"❌ LỖI KHI CHẠY TEST: {e}")
            import traceback
            print(traceback.format_exc())
        finally:
            self.is_running = False
            print("--- KẾT THÚC TEST ---\n")

    # ============================================================
    # HÀM LOGIC CHO NÚT SỐ 9 (DEBUG ATTACK TRỰC TIẾP)
    # ============================================================
    def test_full_attack(self):

        print("[DEBUG ATTACK] ⚡ BỎ QUA KIỂM TRA TÀI NGUYÊN. Vào trận trực tiếp!")

        # 1. Bấm Attack để vào trận
        print("[DEBUG ATTACK] Bấm Attack...")
        tap(ATTACK_CONFIRM_TAP[0], ATTACK_CONFIRM_TAP[1])
        time.sleep(2.5)  # Chờ map load xong

        # 2. Thả quân
        print("[DEBUG ATTACK] Bắt đầu thả quân...")
        test_cfg = {'sides': 2}  # Đổi thành 1, 3, 4 tùy ý muốn test
        run_attack(test_cfg)
        
        print("✅ Đã thả xong quân! (Bạn tự bấm End Battle nhé)")
        return True

    def __del__(self):
        # Khôi phục lại stdout khi tab bị hủy
        sys.stdout = self.original_stdout