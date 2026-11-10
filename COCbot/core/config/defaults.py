"""Default runtime values.

Keep every tunable here (or in the feature config dataclasses) instead of
hard-coding it inside views, models, or adapters.
"""

from __future__ import annotations

from COCbot.models.enums import EmulatorType

# --- ADB / emulator -------------------------------------------------------
EMULATOR_HOSTS: dict[EmulatorType, str] = {
    EmulatorType.MEMU: "127.0.0.1:21503",
    EmulatorType.LDPLAYER: "127.0.0.1:5555",
    EmulatorType.BLUESTACKS: "127.0.0.1:5556",
    EmulatorType.CUSTOM: "127.0.0.1:5555",
}
DEFAULT_EMULATOR = EmulatorType.MEMU
DEFAULT_ADB_TIMEOUT = 10.0
DEFAULT_TAP_DURATION_MS = 40
DEFAULT_SWIPE_DURATION_MS = 300
ADB_RETRY_COUNT = 2
ADB_RETRY_DELAY_SEC = 0.5

# --- Screen ---------------------------------------------------------------
SCREEN_WIDTH = 860
SCREEN_HEIGHT = 732
DEFAULT_SCREENSHOT_FORMAT = "png"

# --- Vision ---------------------------------------------------------------
DEFAULT_YOLO_MODEL = "models/redline_seg.pt"
DEFAULT_YOLO_CONFIDENCE = 0.35
DEFAULT_YOLO_IOU = 0.45
DEFAULT_REDLINE_OFFSET_RATIO = 0.35
DEFAULT_OCR_MIN_CONFIDENCE = 0.40

# --- Bot loop -------------------------------------------------------------
DEFAULT_CYCLE_DELAY_SEC = 1.0
DEFAULT_MAX_CONSECUTIVE_ERRORS = 5
DEFAULT_ATTACK_TIMEOUT_SEC = 180.0
DEFAULT_RETURN_HOME_TIMEOUT_SEC = 30.0

# --- Logging --------------------------------------------------------------
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_LOG_FILE = "logs/bot.log"
DEFAULT_LOG_MAX_BYTES = 5_000_000
DEFAULT_LOG_BACKUP_COUNT = 5
LOG_TIME_FORMAT = "%H:%M:%S"
LOG_MESSAGE_FORMAT = "%(asctime)s • %(levelname)s %(name)s: %(message)s"

# --- Settings / resources -------------------------------------------------
DEFAULT_SETTINGS_FILE = "settings.json"
DEFAULT_ARMY_PRESETS_FILE = "army_presets.json"

# --- Auto capture ---------------------------------------------------------
DEFAULT_AUTO_CAPTURE_DIR = "datasets/redline/images/raw"
DEFAULT_AUTO_CAPTURE_INTERVAL_SEC = 2.0
DEFAULT_AUTO_CAPTURE_MAX_FILES = 2000
DEFAULT_AUTO_CAPTURE_JPEG_QUALITY = 92
DEFAULT_AUTO_CAPTURE_WEBP_QUALITY = 90
DEFAULT_AUTO_CAPTURE_PNG_COMPRESSION = 9
