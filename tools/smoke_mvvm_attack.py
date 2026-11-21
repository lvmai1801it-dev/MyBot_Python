"""Smoke: run the MVVM FullAttackStep chain on a real scout frame.

Uses the real ONNX redline, the real ArmyBarScanner, and the real AttackExecutor
in dry-run mode; only the screen source is a saved dataset frame. Verifies the
fixed chain end to end: scan -> redline -> army slots -> planned deploy points
-> every point outside the no-deploy polygon.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402

from COCbot.core.config.schema import AppConfig  # noqa: E402
from COCbot.core.vision.redline import RedlineDetector  # noqa: E402
from COCbot.models.frame import Frame  # noqa: E402
from COCbot.vision.redline.deploy_zone import try_load_polygon_source  # noqa: E402

from COCbot.core.vision.detector import YoloDetector  # noqa: E402
from COCbot.features.attack.army_bar import ArmyBarScanner  # noqa: E402
from COCbot.features.attack.battle import BattleService, FullAttackStep  # noqa: E402
from COCbot.features.attack.executor import AttackExecutor  # noqa: E402
from COCbot.features.attack.model import AttackModel  # noqa: E402
from COCbot.core.vision.templates import TemplateMatcher  # noqa: E402
from COCbot.app.orchestrator import BotSession, CycleContext  # noqa: E402
from COCbot.models.enums import BotPhase  # noqa: E402


class FakeCapture:
    """Serve one saved scout frame."""

    def __init__(self, image):
        self.frame = Frame(image=image, width=image.shape[1], height=image.shape[0])

    def capture(self):
        return self.frame


class FakeAdb:
    """Record taps; the executor stays dry-run so none should arrive."""

    def __init__(self):
        self.taps = []

    def tap(self, x, y):
        self.taps.append((x, y))
        return True


class FakeClock:
    def now(self):
        return 0.0

    def monotonic(self):
        return 0.0

    def sleep(self, seconds):
        pass


def main() -> int:
    config = AppConfig()
    frames = sorted((ROOT / "datasets" / "redline" / "images" / "raw").glob("*.jpg"))
    picked = frames[:: max(1, len(frames) // 6)][:6]
    matcher = TemplateMatcher(logger=None)
    scanner = ArmyBarScanner(logger=None)

    failures = 0
    for path in picked:
        image = cv2.imread(str(path))
        capture = FakeCapture(image)
        adb = FakeAdb()
        redline = RedlineDetector(
            offset_ratio=config.vision.redline_offset_ratio,
            segmenter=try_load_polygon_source(config.vision.deploy_zone_model),
        )
        attack_model = AttackModel(
            capture=capture,
            detector=YoloDetector(logger=None),
            redline=redline,
            adb=adb,
            config=config,
            logger=None,
            allow_input=False,
        )
        battle = BattleService(
            adb, capture, matcher, clock=FakeClock(), execute=False
        )
        executor = AttackExecutor(adb, clock=FakeClock(), execute=False)
        step = FullAttackStep(attack_model, battle, scanner, executor, execute=False)

        context = CycleContext(session=BotSession(), config=config)
        context.session.start()
        context.session.mark_phase(BotPhase.RUNNING)
        result = step.run(context)

        scan = attack_model.last_scan
        red = scan.redline if scan else None
        prediction = getattr(redline._segmenter, "_last_prediction", None)
        unsafe = 0
        total = 0
        if red is not None and red.edges and prediction is not None:
            # The per-pixel mask is authoritative (the polygon is an
            # approximation with ~12px error near thin boundaries).
            cls = prediction.cls
            for edge in red.edges:
                for point in edge:
                    total += 1
                    x, y = int(point.x), int(point.y)
                    if not (0 <= x < cls.shape[1] and 0 <= y < cls.shape[0]):
                        unsafe += 1
                    elif int(cls[y, x]) != 0:
                        unsafe += 1

        status = "OK " if result.success and unsafe == 0 else "FAIL"
        if status == "FAIL":
            failures += 1
        print(f"[{status}] {path.name}")
        print(f"       success={result.success} msg={result.message[:90]}")
        print(
            f"       source={red.source if red else '?'} "
            f"unsafe_deploy_points={unsafe}/{total} taps={len(adb.taps)}"
        )

    print(f"\n{len(picked) - failures}/{len(picked)} frames passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
