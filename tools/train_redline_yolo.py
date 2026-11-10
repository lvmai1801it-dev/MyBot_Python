"""Train a YOLO segmentation model for the CoC redline / base area.

Dataset layout (YOLO segmentation):
  datasets/redline/
    images/train/*.png
    images/val/*.png
    labels/train/*.txt
    labels/val/*.txt
    redline.local.yaml   (generated with an absolute `path:`)

Label format per line:
  class x1 y1 x2 y2 x3 y3 ...   (normalized polygon, class 0 = base_area)

Usage:
  python tools/train_redline_yolo.py --model yolov8n-seg.pt
  python tools/train_redline_yolo.py --model yolo11n-seg.pt --epochs 150 --imgsz 736 --batch 8
  python tools/train_redline_yolo.py --export-only --weights runs/redline/seg/weights/best.pt

The trained model is copied to:
  models/redline_seg.pt
  models/redline_seg.onnx
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys

try:  # running as `python tools/train_redline_yolo.py`
    from redline_common import (
        BASE,
        DEFAULT_BASE_MODEL,
        MODELS_DIR,
        ROOT,
        dataset_counts,
        ensure_dataset_yaml,
    )
except ImportError:  # running as `python -m tools.train_redline_yolo`
    from tools.redline_common import (
        BASE,
        DEFAULT_BASE_MODEL,
        MODELS_DIR,
        ROOT,
        dataset_counts,
        ensure_dataset_yaml,
    )


def _resolve_base_model(name: str) -> str:
    """Prefer a local copy in models/ over letting Ultralytics download to cwd."""
    if os.path.isabs(name) or os.sep in name or "/" in name:
        return name
    local = MODELS_DIR / name
    if local.exists():
        return str(local)
    return name


def _copy_to_models(src):
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    ext = os.path.splitext(src)[1].lower()
    dst = MODELS_DIR / ("redline_seg" + ext)
    shutil.copy2(src, dst)
    print("Copied:", src, "->", dst)


def _check_dataset(data_path: str) -> bool:
    counts = dataset_counts()
    print("Dataset:")
    for key, value in counts.items():
        print(f"  {key:12s}: {value}")
    if counts["images/train"] == 0:
        print("No training images. Run the bot to auto-capture, label them, then:")
        print("  python tools/split_redline_dataset.py --val-ratio 0.2 --clean")
        return False
    if counts["labels/train"] < counts["images/train"]:
        print("[WARN] Some training images have no label; Ultralytics will skip them.")
    print("Dataset YAML:", data_path)
    return True


def main():
    parser = argparse.ArgumentParser(description="Train YOLO-seg for CoC redline")
    parser.add_argument("--model", default=DEFAULT_BASE_MODEL,
                        help=f"Base model (default: {DEFAULT_BASE_MODEL}); "
                             "yolo11n-seg.pt / yolov8n-seg.pt / local .pt")
    parser.add_argument("--data", default="",
                        help="Dataset YAML (default: generated redline.local.yaml)")
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--imgsz", type=int, default=736)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--device", default="0", help="0 for GPU, cpu for CPU")
    parser.add_argument("--project", default=str(ROOT / "runs" / "redline"))
    parser.add_argument("--name", default="seg")
    parser.add_argument("--export-only", action="store_true")
    parser.add_argument("--weights", default="", help="Path to best.pt for export-only")
    args = parser.parse_args()

    try:
        from ultralytics import YOLO
    except Exception as e:
        print("Ultralytics is not installed. Run: pip install ultralytics")
        print("Error:", e)
        sys.exit(1)

    if args.export_only:
        weights = args.weights or os.path.join(args.project, args.name, "weights", "best.pt")
        if not os.path.exists(weights):
            print("Weights not found:", weights)
            sys.exit(1)
        model = YOLO(weights)
        onnx_path = model.export(format="onnx", imgsz=args.imgsz, simplify=True, opset=12)
        print("Exported:", onnx_path)
        _copy_to_models(onnx_path)
        return

    data_path = args.data or str(ensure_dataset_yaml())
    if not _check_dataset(data_path):
        sys.exit(1)

    model_ref = _resolve_base_model(args.model)
    print("Base model:", model_ref)
    try:
        model = YOLO(model_ref)
    except Exception as e:
        print("Cannot load base model:", e)
        print("If it is a remote name, check the network or pre-download it:")
        print("  python tools/setup_redline_yolo.py --download-base")
        sys.exit(1)
    model.train(
        data=data_path,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        project=args.project,
        name=args.name,
        task="segment",
        patience=30,
        save=True,
        plots=True,
    )

    best = os.path.join(args.project, args.name, "weights", "best.pt")
    if os.path.exists(best):
        _copy_to_models(best)
        try:
            model = YOLO(best)
            onnx_path = model.export(format="onnx", imgsz=args.imgsz, simplify=True, opset=12)
            print("Exported ONNX:", onnx_path)
            _copy_to_models(onnx_path)
        except Exception as e:
            print("ONNX export failed (optional):", e)
    else:
        print("Training finished but best.pt was not found:", best)


if __name__ == "__main__":
    main()
