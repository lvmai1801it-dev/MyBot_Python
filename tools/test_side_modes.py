"""Side-mode tests for the attack dropper (offline matrix + live battles).

Offline (--offline):
    Capture ONE real scout frame (search -> screenshot -> return home, no
    troops spent), then for every GUI mode build the legacy attack plan and
    show which edges/points get chosen. Runs the "Nga^~u nhie^n" RANDOM pick
    200 times to show its distribution.

Live (--live):
    Fight 5 short battles through the REAL legacy deployment path
    (build_attack_plan -> select_drop_troop -> drop_on_active_edges), one
    per mode, spending a few troops each time:

        B0  Nga^~u nhie^n (RANDOM, planner picks 1 random side) - hog_rider x3
        B1  1 huong  TR  (Trên Phải)                          - dragon x2
        B2  2 huong  BL+BR (Nửa Dưới)                         - titan x2
        B3  3 huong  TR+BR+BL (nb_sides=3 fallback)           - titan x3
        B4  Ca? 4 huong (+)                                   - everything left
                                                             + King + bats

Each battle saves a planned-points overlay and a mid-battle screenshot to
artifacts/ so the drop locations can be inspected afterwards.
"""

import argparse
import random
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from COCbot.app import state  # noqa: E402
from COCbot.app.army_presets import attack_sides_for_label  # noqa: E402
from COCbot.attack.army import prepare_attack  # noqa: E402
from COCbot.attack.device import init_device, tap  # noqa: E402
from COCbot.attack.dropper import (  # noqa: E402
    drop_heroes_v2,
    drop_on_active_edges,
    edge_midpoint,
)
from COCbot.attack.device import check_slot_has_troops, select_drop_troop  # noqa: E402
from COCbot.attack.planner import build_attack_plan  # noqa: E402
from COCbot.core.adb import AdbClient  # noqa: E402
from COCbot.core.config.schema import AppConfig  # noqa: E402
from COCbot.core.logging import build_logger  # noqa: E402
from COCbot.core.vision import ScreenCapture, TemplateMatcher  # noqa: E402
from COCbot.core.vision.image import frame_image  # noqa: E402
from COCbot.features.attack.battle import BattleService  # noqa: E402
from COCbot.vision.redline import deploy_zone  # noqa: E402
from COCbot.vision.redline.detector import get_redline_edges_ex  # noqa: E402

ART = ROOT / "artifacts"
ART.mkdir(exist_ok=True)

# Spells are opt-in in the attack flow (mirrors the GUI "Thả spell" toggle).
DROP_SPELLS = False

# GUI label -> side codes, for reference in the report.
MODES = [
    ("Ngẫu nhiên", ["RANDOM"]),
    ("Trên Trái (TL)", ["TL"]),
    ("Trên Phải (TR)", ["TR"]),
    ("Dưới Trái (BL)", ["BL"]),
    ("Dưới Phải (BR)", ["BR"]),
    ("Nửa Trên (TL + TR)", ["TL", "TR"]),
    ("Nửa Dưới (BL + BR)", ["BL", "BR"]),
    ("3 hướng (TR+BR+BL)", ["TR", "BR", "BL"]),
    ("Cả 4 hướng (+)", ["TR", "BR", "BL", "TL"]),
]


def build_services(config: AppConfig):
    """ADB + capture + battle service with real taps."""
    logger = build_logger()
    adb = AdbClient(host=config.emulator.host, logger=logger)
    if not adb.connect(config.emulator.host, timeout=5.0):
        raise SystemExit("ADB connect failed - is the emulator running?")
    capture = ScreenCapture(adb, logger=logger)
    matcher = TemplateMatcher(logger=logger)
    battle = BattleService(
        adb,
        capture,
        matcher,
        logger=logger,
        execute=True,
        scout_timeout=90.0,
        max_battle_wait=240.0,
    )
    state.host = config.emulator.host
    state.stop_event.clear()
    state.pause_event.set()
    init_device(config.emulator.host)
    return capture, battle


def capture_scout_frame(battle: BattleService):
    """Search a base, wait for the scout screen, capture, return home."""
    print("[SCOUT] return home + search ...")
    battle.return_home()
    battle.search_attack()
    if not battle.wait_for_scout():
        battle.return_home()
        raise SystemExit("scout screen not detected")
    frame = battle.capture()
    battle.return_home()
    if frame is None:
        raise SystemExit("capture failed")
    return frame


def redline_and_plan(img_bgr, sides, cfg_extra=None):
    """Run the exact legacy chain: ONNX edges -> plan -> sanitize."""
    edges, source = get_redline_edges_ex(
        img_bgr, model_path="", deploy_model_path="models/deploy_zone.onnx"
    )
    cfg = {"attack_sides": list(sides), "sides": len(sides)}
    if cfg_extra:
        cfg.update(cfg_extra)
    plan = build_attack_plan(edges, cfg)
    deploy_zone.sanitize_plan_edges(plan)
    return edges, source, plan


def save_overlay(img_bgr, plan, name):
    """Draw the redline polygon + active-edge deploy points."""
    vis = img_bgr.copy()
    prediction = deploy_zone.last_prediction()
    if prediction is not None and prediction.polygon:
        cv2.polylines(
            vis, [np.array(prediction.polygon, np.int32)], True, (0, 0, 255), 2
        )
    for edge in plan.get("active_edges") or []:
        for idx, point in enumerate(edge):
            cv2.circle(vis, (int(point[0]), int(point[1])), 4, (0, 255, 0), -1)
            cv2.putText(
                vis, str(idx), (int(point[0]) + 6, int(point[1]) - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1,
            )
    out = ART / name
    cv2.imwrite(str(out), vis)
    return out


def offline_matrix(config: AppConfig) -> None:
    """Part 1: every mode on one real scout frame + RANDOM distribution."""
    capture, battle = build_services(config)
    frame = capture_scout_frame(battle)
    img = frame_image(frame)
    cv2.imwrite(str(ART / "side_mode_frame.png"), img)
    print(f"[FRAME] scout frame saved -> artifacts/side_mode_frame.png\n")

    print(f"{'mode':24s} {'target_side':12s} active edges (points)")
    for label, sides in MODES:
        _, source, plan = redline_and_plan(img, sides)
        if not plan:
            print(f"{label:24s} PLAN FAILED")
            continue
        counts = [len(e) for e in plan["active_edges"]]
        side = plan.get("target_side") or "-"
        print(f"{label:24s} {side:12s} {counts} source={source}")
        save_overlay(img, plan, f"side_mode_{label.split(' ')[0]}_{side}.png")

    print("\n[RANDOM] planner pick distribution (200 runs, one side each):")
    _, _, plan = redline_and_plan(img, ["RANDOM"])  # edges for nothing
    picks = Counter()
    for _ in range(200):
        edges, _src = get_redline_edges_ex(
            img, model_path="", deploy_model_path="models/deploy_zone.onnx"
        )
        plan = build_attack_plan(edges, {"attack_sides": ["RANDOM"]})
        picks[plan.get("target_side") or "-"] += 1
    for side, count in sorted(picks.items()):
        bar = "#" * count
        print(f"    {side:4s} {count:3d}/200 {bar}")

    print("\n[FIXED] determinism check (10 runs per fixed mode):")
    for label, sides in MODES[1:]:
        results = set()
        for _ in range(10):
            edges, _src = get_redline_edges_ex(
                img, model_path="", deploy_model_path="models/deploy_zone.onnx"
            )
            plan = build_attack_plan(edges, {"attack_sides": list(sides)})
            results.add(
                tuple(tuple(e) for e in plan["active_edges"])
            )
        verdict = "FIXED (same edges every run)" if len(results) == 1 else "VARIES!"
        print(f"    {label:24s} -> {verdict}")


LIVE_BATTLES = [
    ("B0-random", ["RANDOM"], "hog_rider", 3, 3),
    ("B1-1huong-TR", ["TR"], "dragon", 2, 2),
    ("B2-2huong-BL-BR", ["BL", "BR"], "electro_titan", 2, 1),
    ("B3-3huong-TR-BR-BL", ["TR", "BR", "BL"], "electro_titan", 2, 1),
    ("B4-all4", ["TR", "BR", "BL", "TL"], None, None, 2),
]


def find_troop_slot(troops, wanted, min_count):
    """Return (name, slot, count) for *wanted* or the first big-enough troop."""
    candidates = [
        info
        for info in troops.values()
        if not info.get("is_spell") and int(info.get("count", 0) or 0) >= min_count
    ]
    for info in candidates:
        if wanted and wanted.lower() in info.get("name", "").lower():
            return info
    return candidates[0] if candidates else None


def wait_home_ready(battle, capture, timeout: float = 30.0) -> bool:
    """Wait for a stable, non-blank frame after returning home.

    The 3s post-battle sleep is not always enough for the game to load the
    home village; taps fired into a loading screen are lost and the next
    search never starts (this is what skipped B2/B3 in the first live run).
    """
    import time as _time

    from COCbot.core.vision.image import frame_image

    deadline = _time.monotonic() + timeout
    stable = 0
    while _time.monotonic() < deadline:
        frame = capture.capture()
        if frame is not None and not frame.is_empty():
            image = frame_image(frame)
            if image is not None and image.std() > 4.0:
                stable += 1
                if stable >= 2:
                    return True
        else:
            stable = 0
        _time.sleep(1.5)
    return False


def live_battles(config: AppConfig) -> None:
    """Part 2: one real mini-battle per side mode."""
    capture, battle = build_services(config)

    for tag, sides, troop, count, pts in LIVE_BATTLES:
        print(f"\n===== {tag} sides={sides} =====")
        try:
            battle.return_home()
            if not wait_home_ready(battle, capture):
                print("  home screen not ready - skipping")
                continue
            battle.search_attack()
            if not battle.wait_for_scout():
                print("  scout screen not detected - skipping")
                battle.return_home()
                continue

            frame = battle.capture()
            img = frame_image(frame)
            edges, source, plan = redline_and_plan(img, sides)
            active = plan["active_edges"]
            print(f"  redline={source} target_side={plan.get('target_side')}")
            print(f"  active edges: {[len(e) for e in active]}")
            overlay = save_overlay(img, plan, f"live_{tag}_plan.png")
            print(f"  plan overlay -> {overlay.name}")

            troops, heroes, cc_slot = prepare_attack(img)
            print(
                "  army:",
                {k: (v.get('name'), v.get('count')) for k, v in troops.items()},
            )
            deployed_slot = None

            if troop is None:
                # Production dump, mirroring run_attack exactly:
                # per-slot verify-and-redrop (3 passes), then heroes, then
                # count-aware spells, then the final 11-slot sweep that
                # catches any badge the earlier passes missed.
                for key, info in troops.items():
                    if info.get("is_spell"):
                        continue
                    current = int(info.get("count", 0) or 0)
                    if current <= 0:
                        continue
                    for attempt in range(3):
                        print(
                            f"  drop {current} x {info.get('name')} "
                            f"(slot {info['slot']}), pass {attempt + 1}"
                        )
                        select_drop_troop(info["slot"])
                        time.sleep(0.15)
                        drop_on_active_edges(active, current, slots_per_edge=pts)
                        time.sleep(0.5)
                        verify = battle.capture()
                        if verify is None:
                            break
                        has_left, remaining = check_slot_has_troops(
                            frame_image(verify), info["slot"]
                        )
                        if not has_left or remaining <= 0:
                            print(f"  slot {info['slot']} empty")
                            break
                        print(f"  slot {info['slot']} still has {remaining} -> redrop")
                        current = remaining
                if any(v >= 0 for v in heroes.values()):
                    drop_heroes_v2(
                        img, plan["edges"], heroes, primary_edge=plan["primary_edge"]
                    )
                for spell in (i for i in troops.values() if i.get("is_spell")):
                    if not DROP_SPELLS:
                        print(
                            f"  skip spell {spell.get('name')} "
                            "(drop_spells disabled)"
                        )
                        continue
                    current = int(spell.get("count", 0) or 0)
                    if current <= 0:
                        continue
                    point = edge_midpoint(active[0] if active else plan["edges"][0])
                    print(f"  drop {current} x spell {spell.get('name')} near {point}")
                    select_drop_troop(spell["slot"])
                    time.sleep(0.15)
                    for _ in range(current):
                        tap(
                            point[0] + random.randint(-5, 5),
                            point[1] + random.randint(-5, 5),
                        )
                        time.sleep(0.25)
                # Final sweep: any TROOP slot that still shows a badge gets
                # dumped; spell slots stay untouched when spells are off.
                time.sleep(1.0)
                sweep_img = battle.capture()
                if sweep_img is not None:
                    simg = frame_image(sweep_img)
                    spell_slots = {
                        int(i.get("slot", -1))
                        for i in troops.values()
                        if i.get("is_spell")
                    }
                    for slot_idx in range(11):
                        if slot_idx in spell_slots and not DROP_SPELLS:
                            continue
                        has_left, rem = check_slot_has_troops(simg, slot_idx)
                        if has_left and rem > 0:
                            print(
                                f"  sweep: slot {slot_idx} still has {rem} "
                                "-> dropping"
                            )
                            select_drop_troop(slot_idx)
                            time.sleep(0.15)
                            drop_on_active_edges(active, rem, slots_per_edge=2)
            else:
                info = find_troop_slot(troops, troop, count or 1)
                if info is None:
                    print("  no troop slot available - skipping battle")
                    battle.return_home()
                    continue
                n = min(count, int(info.get("count", 0) or 0))
                print(
                    f"  drop {n} x {info.get('name')} (slot {info['slot']}) "
                    f"on {len(active)} edge(s), {pts} point(s)/edge"
                )
                select_drop_troop(info["slot"])
                time.sleep(0.15)
                drop_on_active_edges(active, n, slots_per_edge=pts)
                deployed_slot = info["slot"]

            # Verify the drop actually spent troops: re-read the slot badge.
            time.sleep(2.0)
            verify_img = battle.capture()
            if verify_img is not None and deployed_slot is not None:
                vimg = frame_image(verify_img)
                has_left, remaining = check_slot_has_troops(vimg, deployed_slot)
                print(
                    f"  slot {deployed_slot} after drop: "
                    f"{'still has ' + str(remaining) if has_left else 'EMPTY'}"
                )

            time.sleep(5.0)
            proof = battle.capture()
            if proof is not None:
                name = ART / f"live_{tag}_midbattle.png"
                cv2.imwrite(str(name), frame_image(proof))
                print(f"  mid-battle screenshot -> {name.name}")

            # Double-check the end screen: the scout frame can produce one
            # template hit, so require a second consecutive match.
            ended = battle.wait_for_battle_end()
            if ended:
                time.sleep(3.0)
                confirm = battle.capture()
                if confirm is not None:
                    from COCbot.core.config.coordinates import BATTLE_REGION

                    second = battle._matcher.match(
                        confirm,
                        "end_battle.png",
                        region=BATTLE_REGION,
                        threshold=0.65,
                    )
                    if second is None:
                        print("  first end-detection was a fluke; waiting again")
                        ended = battle.wait_for_battle_end()
            print(f"  battle ended detected: {ended}")
        except Exception as exc:
            print(f"  ERROR: {type(exc).__name__}: {exc}")
        finally:
            try:
                battle.return_home()
            except Exception as exc:
                print(f"  return home failed: {exc}")

    print("\nlive battles complete")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="matrix only")
    parser.add_argument("--live", action="store_true", help="real mini battles")
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="one battle: dump everything left with the production logic",
    )
    args = parser.parse_args()

    random.seed()  # planner randomness should be live, not reproducible
    config = AppConfig()
    if args.cleanup:
        global LIVE_BATTLES
        LIVE_BATTLES[:] = [("cleanup-all4", ["TR", "BR", "BL", "TL"], None, None, 2)]
        live_battles(config)
        return 0
    if args.offline:
        offline_matrix(config)
    if args.live:
        live_battles(config)
    if not args.offline and not args.live:
        offline_matrix(config)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
