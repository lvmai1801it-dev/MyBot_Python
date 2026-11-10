"""Convert the redline dataset to compact JPEG/WebP to save disk space.

A 860x732 ADB PNG is ~1.4-1.6 MB. JPEG q92 is ~350 KB and WebP q90 is ~300 KB,
with no meaningful loss for redline segmentation.

Usage:
  python tools/compress_dataset.py
  python tools/compress_dataset.py --format webp --quality 90
  python tools/compress_dataset.py --dirs raw,train,val --keep
  python tools/compress_dataset.py --dry-run

Defaults:
  --format jpg  --quality 92  --dirs raw,train,val
  originals are deleted after a successful conversion (use --keep to retain).

Labels are NOT touched: YOLO matches an image and its label by file stem, so
`foo.png` + `foo.txt` becomes `foo.jpg` + `foo.txt` (still valid). Sidecar
`foo.png.json` is renamed to `foo.jpg.json`.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import cv2
import numpy as np

try:  # running as `python tools/compress_dataset.py`
    from redline_common import BASE
except ImportError:  # running as `python -m tools.compress_dataset`
    from tools.redline_common import BASE

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def _imread(path: Path):
    """Unicode-safe cv2.imread for Windows paths."""
    try:
        data = np.fromfile(str(path), dtype=np.uint8)
        if data.size == 0:
            return None
        return cv2.imdecode(data, cv2.IMREAD_COLOR)
    except Exception:
        return None


def _encode(img, fmt: str, quality: int):
    if fmt == "webp":
        ok, buf = cv2.imencode(
            ".webp", img, [cv2.IMWRITE_WEBP_QUALITY, quality])
        return (buf.tobytes(), ".webp") if ok else (None, "")
    if fmt == "png":
        ok, buf = cv2.imencode(
            ".png", img, [cv2.IMWRITE_PNG_COMPRESSION, quality])
        return (buf.tobytes(), ".png") if ok else (None, "")
    ok, buf = cv2.imencode(
        ".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return (buf.tobytes(), ".jpg") if ok else (None, "")


def _convert_dir(directory: Path, fmt: str, quality: int, keep: bool,
                 overwrite: bool, dry_run: bool, reencode: bool):
    if not directory.is_dir():
        return 0, 0, 0, 0

    before = after = converted = skipped = 0
    for src in sorted(directory.iterdir()):
        if not src.is_file() or src.suffix.lower() not in IMAGE_EXTS:
            continue

        src_size = src.stat().st_size
        before += src_size

        target_suffix = "." + fmt
        same = src.suffix.lower() == target_suffix
        if same and not reencode:
            after += src_size
            skipped += 1
            continue

        dst = src.with_suffix(target_suffix)
        if dst.exists() and dst != src and not overwrite:
            print(f"  skip (target exists): {dst.name}")
            after += src_size
            skipped += 1
            continue

        img = _imread(src)
        if img is None:
            print(f"  skip (unreadable): {src.name}")
            after += src_size
            skipped += 1
            continue

        data, ext = _encode(img, fmt, quality)
        if not data:
            print(f"  skip (encode failed): {src.name}")
            after += src_size
            skipped += 1
            continue

        dst = src.with_suffix(ext)
        after += len(data)
        converted += 1

        if dry_run:
            print(f"  {src.name} -> {dst.name}: "
                  f"{src_size / 1024:.0f} KB -> {len(data) / 1024:.0f} KB")
            continue

        if dst == src:
            tmp = src.with_suffix(src.suffix + ".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, src)
        else:
            dst.write_bytes(data)

        # Rename the metadata sidecar (if any).
        sidecar = Path(str(src) + ".json")
        if sidecar.exists():
            new_sidecar = Path(str(dst) + ".json")
            try:
                if new_sidecar.exists() and not overwrite:
                    pass
                else:
                    os.replace(sidecar, new_sidecar)
            except OSError:
                pass

        if not keep and dst != src:
            try:
                src.unlink()
            except OSError:
                pass

        if converted % 50 == 0:
            print(f"  ... {converted} converted")

    return before, after, converted, skipped


def main():
    parser = argparse.ArgumentParser(description="Compress redline dataset images")
    parser.add_argument("--format", default="jpg", choices=["jpg", "jpeg", "webp", "png"])
    parser.add_argument("--quality", type=int, default=0,
                        help="jpeg/webp quality (default 92/90); png compression 0-9")
    parser.add_argument("--dirs", default="raw,train,val",
                        help="comma-separated subdirs of datasets/redline/images")
    parser.add_argument("--keep", action="store_true", help="Keep original files")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing targets")
    parser.add_argument("--reencode", action="store_true",
                        help="Re-encode files already in the target format")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    fmt = "jpg" if args.format == "jpeg" else args.format
    if args.quality:
        quality = args.quality
    elif fmt == "webp":
        quality = 90
    elif fmt == "png":
        quality = 9
    else:
        quality = 92

    dirs = [BASE / "images" / name.strip() for name in args.dirs.split(",") if name.strip()]

    print(f"dataset : {BASE}")
    print(f"format  : {fmt} (quality={quality})")
    print(f"dirs    : {', '.join(d.name for d in dirs)}")
    print(f"mode    : {'dry-run' if args.dry_run else ('keep originals' if args.keep else 'replace originals')}")
    print()

    total_before = total_after = total_converted = total_skipped = 0
    for d in dirs:
        print(f"[{d.name}]")
        before, after, converted, skipped = _convert_dir(
            d, fmt, quality, args.keep, args.overwrite, args.dry_run, args.reencode)
        total_before += before
        total_after += after
        total_converted += converted
        total_skipped += skipped
        print(f"  converted={converted} skipped={skipped} "
              f"{before / 1e6:.1f} MB -> {after / 1e6:.1f} MB")

    print()
    print(f"TOTAL: converted={total_converted} skipped={total_skipped} "
          f"{total_before / 1e6:.1f} MB -> {total_after / 1e6:.1f} MB")
    if total_before > 0:
        saved = 100.0 * (1 - total_after / total_before)
        print(f"Saved : {saved:.1f}%")
    if args.dry_run:
        print("(dry-run: no files were written)")


if __name__ == "__main__":
    main()
