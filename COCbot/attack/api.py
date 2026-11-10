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

from COCbot.attack.device import (
    init_device,
    get_device,
    reset_device,
    tap,
    set_sleep,
    select_drop_troop,
    check_slot_has_troops,
)
from COCbot.attack.dropper import (
    get_spread_points_along_edge,
    drop_multipoint_concurrent,
    drop_on_edge,
    drop_on_edges,
    drop_on_active_edges,
    drop_heroes_v2,
    drop_cc,
    drop_spells,
)
from COCbot.vision.redline.detector import (
    TARGET_HEX_COLORS,
    hex_to_bgr,
    get_redline_edges_cv,
    get_redline_edges,
    get_redline_edges_ex,
)
from COCbot.vision.redline.yolo import (
    RedlineSegmenter,
    get_redline_from_yolo,
    polygon_to_edges,
)
from COCbot.attack.planner import build_attack_plan, legacy_edge_selection
from COCbot.attack.cycle import run_attack
from COCbot.attack.army import prepare_attack

__all__ = [
    "run_attack",
    "init_device",
    "get_device",
    "reset_device",
    "tap",
    "set_sleep",
    "select_drop_troop",
    "check_slot_has_troops",
    "get_spread_points_along_edge",
    "drop_multipoint_concurrent",
    "drop_on_edge",
    "drop_on_edges",
    "drop_on_active_edges",
    "drop_heroes_v2",
    "drop_cc",
    "drop_spells",
    "TARGET_HEX_COLORS",
    "hex_to_bgr",
    "get_redline_edges_cv",
    "get_redline_edges",
    "get_redline_edges_ex",
    "RedlineSegmenter",
    "get_redline_from_yolo",
    "polygon_to_edges",
    "build_attack_plan",
    "legacy_edge_selection",
    "prepare_attack",
]
