"""Structure audit: map every module's importers and find misfits.

Outputs, for the CURRENT (post-purge) tree:
- broken imports: `from COCbot.x.y import ...` pointing at missing files
- orphans: runtime modules nothing imports (excluding entry points and
  __init__)
- package map: module -> importer count, so each file can be checked
  against the feature it claims to serve
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

COCBOT = ROOT / "COCbot"
TOOLS = ROOT / "tools"


def module_name(path: Path) -> str:
    rel = path.relative_to(ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def own_modules(base: Path) -> dict[str, Path]:
    out = {}
    for path in base.rglob("*.py"):
        out[module_name(path)] = path
    return out


modules = own_modules(COCBOT)
# tools + run.py + tests are importers, not importable modules
importers: dict[str, set[str]] = {name: set() for name in modules}
external_files = [TOOLS / p for p in TOOLS.glob("*.py")]
external_files += [ROOT / "run.py"]
external_files += [p for p in (ROOT / "tests").rglob("*.py")]

broken: list[tuple[str, str]] = []


def scan_imports(source: str, origin: str, is_internal: bool):
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        print(f"SYNTAX ERROR in {origin}: {exc}")
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            pairs = [(alias.name, None) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            pairs = [(node.module, alias.name) for alias in node.names]
        else:
            continue
        for name, symbol in pairs:
            if not (name == "COCbot" or name.startswith("COCbot.")):
                continue
            hits = set()
            # `from COCbot.pkg import mod` -> attribute-style submodule import
            if symbol is not None:
                candidate = f"{name}.{symbol}"
                if candidate in modules:
                    hits.add(candidate)
            # resolve the longest matching module for the dotted name
            for m in modules:
                if name == m or name.startswith(m + "."):
                    hits.add(m)
            if not hits:
                broken.append((origin, name))
                continue
            for hit in hits:
                importers.setdefault(hit, set()).add(origin)
                if is_internal and hit not in modules:
                    broken.append((origin, name))


for name, path in modules.items():
    scan_imports(
        path.read_text(encoding="utf-8-sig", errors="replace"), name, True
    )
for path in external_files:
    if path.exists():
        scan_imports(
            path.read_text(encoding="utf-8-sig", errors="replace"),
            str(path.relative_to(ROOT)),
            False,
        )

ENTRY_POINTS = {
    "COCbot.gui.app",           # run.py target
    "COCbot.app.bootstrap",     # bot_loop / one_cycle
    "COCbot.app.upgrade_hook",
}

print("=== BROKEN IMPORTS ===")
for origin, target in sorted(set(broken)):
    print(f"  {origin} -> {target}")
if not broken:
    print("  none")

print("\n=== ORPHANS (nothing imports them; not entry points) ===")
for name in sorted(modules):
    if name in ENTRY_POINTS or name.endswith("__init__"):
        continue
    users = importers.get(name, set())
    internal = {u for u in users if not u.startswith(("tools", "tests", "run"))}
    if not internal:
        print(f"  {name}   (external users: {sorted(users) or 'none'})")

print("\n=== PACKAGE MAP (module -> internal importer count) ===")
by_pkg: dict[str, list[tuple[str, int]]] = {}
for name in sorted(modules):
    pkg = name.rsplit(".", 1)[0] if "." in name else "(top)"
    by_pkg.setdefault(pkg, []).append((name, len(importers.get(name, set()))))
for pkg in sorted(by_pkg):
    print(f"\n[{pkg}]")
    for name, count in by_pkg[pkg]:
        print(f"  {count:3d}  {name}")
