"""Templates audit: exact duplicates + per-directory inventory.

Hashes every file under Templates/ and reports:
- duplicate groups (same MD5, different paths) with reclaimable size
- per-subdirectory file count and size
- root-level files (candidates for categorization)
"""

import hashlib
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "Templates"


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


files = sorted(p for p in TPL.rglob("*") if p.is_file())
groups: dict[str, list[Path]] = defaultdict(list)
for path in files:
    groups[md5(path)].append(path)

dupes = {h: ps for h, ps in groups.items() if len(ps) > 1}
total_reclaim = 0
print(f"files: {len(files)}  unique: {len(groups)}  dup-groups: {len(dupes)}")
print(f"total size: {sum(p.stat().st_size for p in files) / 1e6:.1f} MB")

print("\n=== DUPLICATE GROUPS ===")
for h, paths in sorted(dupes.items(), key=lambda kv: -len(kv[1])):
    size = paths[0].stat().st_size
    total_reclaim += size * (len(paths) - 1)
    print(f"\n[{h[:8]}] {size/1024:.0f} KB x{len(paths)}")
    for p in paths:
        print(f"    {p.relative_to(TPL)}")
print(f"\nreclaimable by exact dedupe: {total_reclaim / 1e6:.2f} MB")

print("\n=== PER-DIRECTORY INVENTORY ===")
by_dir: dict[str, list[Path]] = defaultdict(list)
for p in files:
    by_dir[str(p.parent.relative_to(TPL))].append(p)
for d, ps in sorted(by_dir.items()):
    size = sum(p.stat().st_size for p in ps)
    print(f"{len(ps):4d}  {size/1e6:7.2f} MB  {d}")
