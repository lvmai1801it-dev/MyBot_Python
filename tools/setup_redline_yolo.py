"""Quick health check / setup for the redline YOLO-seg stack.

Usage:
  python tools/setup_redline_yolo.py
  python tools/setup_redline_yolo.py --download-base
  python tools/setup_redline_yolo.py --smoke
  python tools/setup_redline_yolo.py --strict

Checks:
  - ultralytics + torch availability
  - trained model (models/redline_seg.pt / .onnx)
  - dataset counts under datasets/redline
  - generated dataset YAML
  - optional: run redline detection on one raw image

Exit code is 0 unless `--strict` is given and the stack is not ready.
"""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

try:  # running as `python tools/setup_redline_yolo.py`
    from redline_common import (
        BASE,
        DEFAULT_BASE_MODEL,
        MODELS_DIR,
        ROOT,
        dataset_counts,
        dataset_yaml_path,
        ensure_dataset_yaml,
        find_trained_model,
    )
except ImportError:  # running as `python -m tools.setup_redline_yolo`
    from tools.redline_common import (
        BASE,
        DEFAULT_BASE_MODEL,
        MODELS_DIR,
        ROOT,
        dataset_counts,
        dataset_yaml_path,
        ensure_dataset_yaml,
        find_trained_model,
    )


HF_FALLBACKS = {
    "yolov8n-seg.pt": "https://huggingface.co/jags/yolov8_model_segmentation-set/resolve/main/yolov8n-seg.pt",
    "yolov8s-seg.pt": "https://huggingface.co/jags/yolov8_model_segmentation-set/resolve/main/yolov8s-seg.pt",
    "yolov8m-seg.pt": "https://huggingface.co/jags/yolov8_model_segmentation-set/resolve/main/yolov8m-seg.pt",
    "yolo11n-seg.pt": "https://huggingface.co/Ultralytics/YOLO11/resolve/main/yolo11n-seg.pt",
}


def _download_url(url: str, target: Path) -> bool:
    try:
        import requests
    except Exception as e:
        print("requests not available:", e)
        return False

    tmp = target.with_suffix(target.suffix + ".part")
    try:
        with requests.get(url, timeout=60, stream=True) as r:
            r.raise_for_status()
            with open(tmp, "wb") as f:
                for chunk in r.iter_content(1024 * 256):
                    if chunk:
                        f.write(chunk)
        if tmp.stat().st_size < 100_000:
            raise ValueError("downloaded file is too small")
        os.replace(tmp, target)
        return True
    except Exception as e:
        print("mirror download failed:", e)
        try:
            tmp.unlink()
        except OSError:
            pass
        return False


def _line(title: str) -> None:
    print(f"\n--- {title} ---")


def _check_ultralytics() -> tuple[bool, str]:
    if importlib.util.find_spec("ultralytics") is None:
        return False, "not installed (pip install ultralytics)"
    try:
        import ultralytics
        return True, getattr(ultralytics, "__version__", "unknown")
    except Exception as e:
        return False, f"import failed: {e}"


def _check_torch() -> tuple[bool, str]:
    if importlib.util.find_spec("torch") is None:
        return False, "not installed"
    try:
        import torch
        cuda = torch.cuda.is_available()
        return True, f"{torch.__version__} (cuda={cuda})"
    except Exception as e:
        return False, f"import failed: {e}"


def _download_base(name: str = DEFAULT_BASE_MODEL) -> bool:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    target = MODELS_DIR / name
    if target.exists():
        print("Already present:", target)
        return True

    print(f"Downloading {name} -> {MODELS_DIR} ...")

    # 1) Let Ultralytics try its official release host.
    try:
        from ultralytics import YOLO
        old = os.getcwd()
        try:
            os.chdir(MODELS_DIR)
            YOLO(name)
        finally:
            os.chdir(old)
    except Exception as e:
        print("official host failed:", e)

    if target.exists():
        print("Downloaded:", target)
        return True

    # 2) Fallback mirrors (GitHub releases are sometimes unreachable).
    url = HF_FALLBACKS.get(name)
    if url:
        print("trying mirror:", url)
        if _download_url(url, target):
            print("Downloaded:", target, f"({target.stat().st_size / 1e6:.1f} MB)")
            return True

    print("Download failed. Check the network/proxy, then retry:")
    print("  python tools/setup_redline_yolo.py --download-base")
    return False


def _first_raw_image() -> Path | None:
    raw = BASE / "images" / "raw"
    if not raw.is_dir():
        return None
    for p in sorted(raw.iterdir()):
        if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
            return p
    return None


def _smoke(model_path: Path | None, image_path: str = "") -> None:
    _line("smoke test")

    image = Path(image_path) if image_path else _first_raw_image()
    if image is None or not image.exists():
        print("No image to test. Run the bot first or pass --image PATH.")
        return

    try:
        import cv2
        sys.path.insert(0, str(ROOT))
        from COCbot.vision.redline.detector import get_redline_edges_ex
    except Exception as e:
        print("Cannot import detector:", e)
        return

    img = cv2.imread(str(image), cv2.IMREAD_COLOR)
    if img is None:
        print("Cannot read image:", image)
        return

    edges, source = get_redline_edges_ex(
        img, model_path=str(model_path) if model_path else "")
    counts = [len(e) for e in edges] if edges else None
    print(f"image : {image}")
    print(f"shape : {img.shape[1]}x{img.shape[0]}")
    print(f"source: {source}")
    print(f"edges : {counts}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the redline YOLO-seg stack")
    parser.add_argument("--download-base", action="store_true",
                        help=f"Download {DEFAULT_BASE_MODEL} into models/")
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL,
                        help="Base model name for --download-base "
                             "(yolov8n-seg.pt / yolo11n-seg.pt)")
    parser.add_argument("--smoke", action="store_true",
                        help="Run redline detection on one raw image")
    parser.add_argument("--image", default="", help="Image for --smoke")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 when model or dataset is missing")
    args = parser.parse_args()

    print("=== REDLINE YOLO-SEG SETUP ===")
    print("project:", ROOT)
    print("python :", sys.version.split()[0],
          f"({'64' if sys.maxsize > 2**32 else '32'}-bit)")

    _line("dependencies")
    ultra_ok, ultra_ver = _check_ultralytics()
    torch_ok, torch_ver = _check_torch()
    print(f"ultralytics: {ultra_ver}")
    print(f"torch      : {torch_ver}")

    if args.download_base:
        _line("download base model")
        _download_base(args.base_model)

    _line("model")
    model = find_trained_model()
    if model:
        print("found  :", model)
        print("size   :", f"{model.stat().st_size / 1e6:.1f} MB")
    else:
        print("missing:", MODELS_DIR / "redline_seg.pt")
        print("         runtime will use the OpenCV fallback")
        base = MODELS_DIR / DEFAULT_BASE_MODEL
        if base.exists():
            print("base   :", base, "(train this, not the final model)")

    _line("dataset")
    counts = dataset_counts()
    for key, value in counts.items():
        print(f"{key:12s}: {value}")
    yaml_path = dataset_yaml_path()
    if not yaml_path.exists():
        yaml_path = ensure_dataset_yaml()
    print("yaml   :", yaml_path)
    try:
        print("root   :", yaml_path.read_text(encoding="utf-8").splitlines()[1])
    except Exception:
        pass

    if args.smoke:
        _smoke(model, args.image)

    _line("verdict")
    ready_train = (counts["images/train"] > 0 and counts["labels/train"] > 0)
    ready_runtime = ultra_ok and model is not None

    if ready_runtime:
        print("runtime: YOLO-seg READY")
    elif ultra_ok:
        print("runtime: fallback OpenCV (no trained model)")
    else:
        print("runtime: fallback OpenCV (ultralytics missing)")

    if ready_train:
        print("train  : dataset READY")
    else:
        print("train  : NOT READY (need labeled images)")

    print("\nnext steps:")
    if not ultra_ok:
        print("  1. .venv\\Scripts\\python.exe -m pip install ultralytics")
    if counts["images/raw"] == 0 and not ready_train:
        print("  2. Run the bot with auto_capture_dataset=true to collect images")
    if counts["images/train"] == 0:
        print("  3. Label polygons -> datasets/redline/labels/raw")
        print("  4. python tools/split_redline_dataset.py --val-ratio 0.2 --clean")
    if model is None:
        print("  5. python tools/train_redline_yolo.py --model yolov8n-seg.pt")
        print("     (or --download-base then edit labels first)")
    if ready_runtime:
        print("  nothing to do - YOLO-seg is active")

    if args.strict and not (ready_runtime and ready_train):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
