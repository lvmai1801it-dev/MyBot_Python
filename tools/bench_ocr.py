"""Benchmark OCR engines (Tesseract / PaddleOCR / GLM-OCR) on labeled crops.

The dataset is a folder of images plus a JSON map ``{filename: expected_text}``.
Text is compared after removing everything except letters, digits and ``/``.

Usage:
    python tools/bench_ocr.py --dir local_test/ocr_bench --labels local_test/ocr_bench/labels.json
    python tools/bench_ocr.py --dir ... --engines tesseract,paddle,glm
    python tools/bench_ocr.py --dir ... --engines glm --server http://127.0.0.1:8080
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TESSERACT_WHITELIST = "0123456789/"
GLM_PROMPT = (
    "Read the text in this image and answer with the characters only. "
    "No explanation."
)


def normalize(text: str) -> str:
    """Keep letters, digits and slash, upper-case everything."""
    return re.sub(r"[^0-9A-Za-z/]", "", str(text)).upper()


def read_tesseract(image: np.ndarray) -> str:
    """White-mask digits, same preprocessing as the resource reader."""
    import pytesseract

    upscaled = cv2.resize(image, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    if upscaled.ndim == 3:
        blue, green, red = cv2.split(upscaled)
        mask = ((blue > 190) & (green > 190) & (red > 190)).astype(np.uint8) * 255
    else:
        mask = (upscaled > 190).astype(np.uint8) * 255
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    prepared = cv2.copyMakeBorder(
        255 - mask, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255
    )
    best = ""
    for psm in (7, 8, 6):
        try:
            text = pytesseract.image_to_string(
                prepared,
                config=(
                    f"--oem 1 --psm {psm} "
                    f"-c tessedit_char_whitelist={TESSERACT_WHITELIST}"
                ),
            )
        except Exception:
            continue
        value = normalize(text)
        if len(value) > len(best):
            best = value
    return best


_paddle = None


def read_paddle(image: np.ndarray) -> str:
    """PaddleOCR recognition on the upscaled crop (same as NumberOcr)."""
    global _paddle
    if _paddle is None:
        from paddleocr import PaddleOCR

        _paddle = PaddleOCR(
            text_detection_model_name=None,
            text_recognition_model_name="PP-OCRv6_small_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
            lang="en",
        )
    upscaled = cv2.resize(image, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    texts: list[str] = []
    for item in _paddle.predict(upscaled) or []:
        values = getattr(item, "rec_texts", None)
        if values is None and hasattr(item, "get"):
            values = item.get("rec_texts", [])
        texts.extend(values or [])
    return " ".join(str(text) for text in texts)


def read_glm(image: np.ndarray, server: str, timeout: float = 120.0) -> str:
    """Call a llama.cpp server running GLM-OCR."""
    import urllib.request

    ok, buffer = cv2.imencode(".png", image)
    if not ok:
        return ""
    payload = {
        "model": "glm-ocr",
        "temperature": 0,
        "max_tokens": 32,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": GLM_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64,"
                            + base64.b64encode(buffer.tobytes()).decode("ascii")
                        },
                    },
                ],
            }
        ],
    }
    request = urllib.request.Request(
        server.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    choices = body.get("choices") or []
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content", "")


def main() -> int:
    """Run the selected engines over the labeled crops."""
    parser = argparse.ArgumentParser(description="OCR benchmark")
    parser.add_argument("--dir", required=True, help="Folder with crops")
    parser.add_argument("--labels", required=True, help="JSON {file: expected}")
    parser.add_argument(
        "--engines",
        default="tesseract,paddle,glm",
        help="Comma separated: tesseract,paddle,glm",
    )
    parser.add_argument("--server", default="http://127.0.0.1:8080")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    directory = Path(args.dir)
    labels = json.loads(Path(args.labels).read_text(encoding="utf-8"))
    names = [name for name in labels if (directory / name).is_file()]
    if args.limit:
        names = names[: args.limit]
    engines = [item.strip().lower() for item in args.engines.split(",") if item.strip()]

    columns = {"tesseract": {}, "paddle": {}, "glm": {}}
    totals = {engine: {"ok": 0, "n": 0, "ms": 0.0} for engine in engines}

    for name in names:
        image = cv2.imread(str(directory / name))
        if image is None:
            continue
        expected = normalize(labels[name])
        for engine in engines:
            start = time.perf_counter()
            try:
                if engine == "tesseract":
                    text = read_tesseract(image)
                elif engine == "paddle":
                    text = read_paddle(image)
                elif engine == "glm":
                    text = read_glm(image, args.server)
                else:
                    continue
            except Exception as exc:
                text = f"<error {type(exc).__name__}>"
            elapsed = (time.perf_counter() - start) * 1000
            got = normalize(text)
            ok = got == expected
            totals[engine]["n"] += 1
            totals[engine]["ok"] += int(ok)
            totals[engine]["ms"] += elapsed
            columns[engine][name] = (got, ok, elapsed)

    width = max((len(name) for name in names), default=10) + 2
    header = "file".ljust(width) + "expected".ljust(22)
    for engine in engines:
        header += engine.ljust(20)
    print(header)
    print("-" * len(header))
    for name in names:
        expected = normalize(labels[name])
        line = name.ljust(width) + expected.ljust(22)
        for engine in engines:
            got, ok, elapsed = columns[engine].get(name, ("", False, 0.0))
            mark = "OK " if ok else "XX "
            line += f"{mark}{got[:10]:<12}{elapsed:6.0f}ms".ljust(20)
        print(line)

    print()
    for engine in engines:
        stats = totals[engine]
        if not stats["n"]:
            continue
        accuracy = 100.0 * stats["ok"] / stats["n"]
        print(
            f"{engine:10} exact {stats['ok']}/{stats['n']} "
            f"({accuracy:5.1f}%)  avg {stats['ms'] / stats['n']:7.1f} ms"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
