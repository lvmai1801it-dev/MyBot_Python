"""Live rehearsal of the MVVM attack chain (no troops are dropped).

Drives the real game through the clean BattleService taps (search, scout
wait, loot OCR, return home) and runs the ONNX redline + army scan + dry-run
deployment planning on the live scout frame. Nothing is deployed, so the
matchmaking browse costs nothing; return home cancels the search.
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from COCbot.core.adb import AdbClient  # noqa: E402
from COCbot.core.config.schema import AppConfig  # noqa: E402
from COCbot.core.logging import build_logger  # noqa: E402
from COCbot.core.vision import (  # noqa: E402
    NumberOcr,
    RedlineDetector,
    ScreenCapture,
    TemplateMatcher,
    YoloDetector,
)
from COCbot.features.attack.army_bar import ArmyBarScanner  # noqa: E402
from COCbot.features.attack.battle import BattleService  # noqa: E402
from COCbot.features.attack.executor import AttackExecutor  # noqa: E402
from COCbot.features.attack.model import AttackModel  # noqa: E402
from COCbot.vision.redline.deploy_zone import try_load_polygon_source  # noqa: E402


def main() -> int:
    logger = build_logger()
    config = AppConfig()
    adb = AdbClient(host=config.emulator.host, logger=logger)
    if not adb.connect(config.emulator.host, timeout=5.0):
        print("ADB connect failed")
        return 1
    capture = ScreenCapture(adb, logger=logger)
    matcher = TemplateMatcher(logger=logger)
    ocr = NumberOcr(logger=logger)

    redline = RedlineDetector(
        offset_ratio=config.vision.redline_offset_ratio,
        logger=logger,
        segmenter=try_load_polygon_source(config.vision.deploy_zone_model),
    )
    attack_model = AttackModel(
        capture=capture,
        detector=YoloDetector(logger=logger),
        redline=redline,
        adb=adb,
        config=config,
        logger=logger,
        allow_input=False,
    )
    battle = BattleService(
        adb, capture, matcher, ocr=ocr, logger=logger, execute=True,
        scout_timeout=60.0,
    )
    scanner = ArmyBarScanner(ocr=ocr, logger=logger)
    executor = AttackExecutor(adb, logger=logger, execute=False)

    print("[1/5] return home + open attack menu")
    battle.return_home()
    battle.search_attack()

    print("[2/5] waiting for the scout screen")
    if not battle.wait_for_scout():
        print("scout screen not detected; returning home")
        battle.return_home()
        return 1

    print("[3/5] reading the loot offer")
    offer = battle.read_loot_offer()
    print(f"      offer: gold={offer.gold} elixir={offer.elixir} dark={offer.dark_elixir}")
    thresholds = config.resources
    print(
        f"      thresholds: gold>={thresholds.gold} elixir>={thresholds.elixir} "
        f"dark>={thresholds.dark_elixir}"
    )

    print("[4/5] ONNX redline + army scan + dry-run deploy plan")
    scan = attack_model.scan()
    red = scan.redline
    prediction = getattr(redline._segmenter, "_last_prediction", None)
    unsafe = 0
    total = 0
    if prediction is not None:
        cls = prediction.cls
        for edge in red.edges:
            for point in edge:
                total += 1
                x, y = int(point.x), int(point.y)
                if not (0 <= x < cls.shape[1] and 0 <= y < cls.shape[0]):
                    unsafe += 1
                elif int(cls[y, x]) != 0:
                    unsafe += 1
    print(
        f"      redline: source={red.source} edges={[len(e) for e in red.edges]} "
        f"unsafe={unsafe}/{total}"
    )
    slots = scanner.scan(scan.frame)
    print(f"      army slots: {[(s.name, s.kind.value, s.count) for s in slots]}")
    result = executor.deploy(scan.plan, red, slots, execute=False)
    print(f"      dry-run deploy: ok={result.ok} planned={result.planned} {result.message}")

    print("[5/5] returning home (no troops dropped)")
    battle.return_home()
    print("rehearsal complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
