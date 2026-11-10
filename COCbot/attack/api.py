"""Public entry point for the attack pipeline.

The old 26 KB monolith has been split into:
  device.py             - tap / uiautomator2 / slot helpers
  dropper.py            - troop/hero/CC/spell dropping
  planner.py            - redline offset + side selection
  cycle.py              - run_attack orchestration
  vision/redline/       - YOLO-seg + OpenCV redline detection

Existing imports continue to work:
  from COCbot.attack.api import run_attack, init_device
"""

from COCbot.attack.army import prepare_attack
from COCbot.attack.cycle import run_attack
from COCbot.attack.device import (
    check_slot_has_troops,
    get_device,
    init_device,
    reset_device,
    select_drop_troop,
    set_sleep,
    tap,
)
from COCbot.attack.dropper import (
    drop_cc,
    drop_heroes_v2,
    drop_multipoint_concurrent,
    drop_on_active_edges,
    drop_on_edge,
    drop_on_edges,
    drop_spells,
    get_spread_points_along_edge,
)
from COCbot.attack.planner import build_attack_plan, legacy_edge_selection
from COCbot.vision.redline.detector import (
    TARGET_HEX_COLORS,
    get_redline_edges,
    get_redline_edges_cv,
    get_redline_edges_ex,
    hex_to_bgr,
)
from COCbot.vision.redline.yolo import (
    RedlineSegmenter,
    get_redline_from_yolo,
    polygon_to_edges,
)

__all__ = [
    "TARGET_HEX_COLORS",
    "RedlineSegmenter",
    "build_attack_plan",
    "check_slot_has_troops",
    "drop_cc",
    "drop_heroes_v2",
    "drop_multipoint_concurrent",
    "drop_on_active_edges",
    "drop_on_edge",
    "drop_on_edges",
    "drop_spells",
    "get_device",
    "get_redline_edges",
    "get_redline_edges_cv",
    "get_redline_edges_ex",
    "get_redline_from_yolo",
    "get_spread_points_along_edge",
    "hex_to_bgr",
    "init_device",
    "legacy_edge_selection",
    "polygon_to_edges",
    "prepare_attack",
    "reset_device",
    "run_attack",
    "select_drop_troop",
    "set_sleep",
    "tap",
]
