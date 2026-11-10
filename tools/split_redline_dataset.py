"""Split labeled redline images into train/val for YOLO-seg.

Expected input:
  datasets/redline/images/raw/*.png
  datasets/redline/labels/raw/*.txt   (YOLO-seg polygon labels)

Output:
  datasets/redline/images/train, images/val
  datasets/redline/labels/train, labels/val
  datasets/redline/redline.local.yaml  (absolute path, used by train)

Usage:
  python tools/split_redline_dataset.py --val-ratio 0.2
  python tools/split_redline_dataset.py --val-ratio 0.2 --clean
"""

from __future__ import annotations

import argparse
import random
import shutil
from pathlib import Path

try:  # running as `python tools/split_redline_dataset.py`
    from redline_common import BASE, ensure_dataset_yaml
except ImportError:  # running as `python -m tools.split_redline_dataset`
    from tools.redline_common import BASE, ensure_dataset_yaml

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")


def main():
    parser = argparse.ArgumentParser(description="Split redline dataset into train/val")
    parser.add_argument("--val-ratio", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--clean", action="store_true", help="Delete existing train/val first")
    parser.add_argument("--move", action="store_true", help="Move instead of copy")
    args = parser.parse_args()

    img_raw = BASE / "images" / "raw"
    lbl_raw = BASE / "labels" / "raw"
    if not img_raw.is_dir():
        print("Missing:", img_raw)
        return

    images = sorted(p.name for p in img_raw.iterdir()
                    if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES)
    if not images:
        print("No images in", img_raw)
        print("Run the bot with auto_capture_dataset=true first.")
        return

    # Keep only images that have a matching label.
    pairs = []
    missing = []
    for name in images:
        stem = Path(name).stem
        label_name = stem + ".txt"
        if (lbl_raw / label_name).is_file():
            pairs.append((name, label_name))
        else:
            missing.append(name)

    print(f"images={len(images)} labeled={len(pairs)} missing_label={len(missing)}")
    if missing:
        print("First missing labels:", ", ".join(missing[:5]))
    if not pairs:
        print("No labeled pairs. Label images in labels/raw first.")
        print("Guide: docs/LABELING-GUIDE.md")
        return

    rng = random.Random(args.seed)
    rng.shuffle(pairs)
    val_count = max(1, int(round(len(pairs) * args.val_ratio)))
    val_set = {p[0] for p in pairs[:val_count]}

    dirs = {
        "img_train": BASE / "images" / "train",
        "img_val": BASE / "images" / "val",
        "lbl_train": BASE / "labels" / "train",
        "lbl_val": BASE / "labels" / "val",
    }
    if args.clean:
        for d in dirs.values():
            if d.is_dir():
                shutil.rmtree(d)
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)

    n_train = n_val = 0
    for name, label_name in pairs:
        is_val = name in val_set
        img_dst = dirs["img_val" if is_val else "img_train"] / name
        lbl_dst = dirs["lbl_val" if is_val else "lbl_train"] / label_name
        img_src = img_raw / name
        lbl_src = lbl_raw / label_name
        if args.move:
            shutil.move(str(img_src), str(img_dst))
            shutil.move(str(lbl_src), str(lbl_dst))
        else:
            shutil.copy2(img_src, img_dst)
            shutil.copy2(lbl_src, lbl_dst)
        if is_val:
            n_val += 1
        else:
            n_train += 1

    yaml_path = ensure_dataset_yaml()

    print(f"train={n_train} val={n_val}")
    print("Dataset YAML:", yaml_path)
    print("Next: python tools/train_redline_yolo.py --model yolov8n-seg.pt")


if __name__ == "__main__":
    main()
