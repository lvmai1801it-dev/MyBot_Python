"""Cross-reference every Templates file against actual code usage.

Referenced = basename appears in a template-name string literal under
COCbot/ or tools/ (with or without the extension — find_template_path
callers pass bare names), OR the file lives in a directory the code
scans wholesale:

    Smart_Auto_train/{Army Troops,Spells,Siege Machines,Train_Tab,to_train}
    Clan Capital/{Scenery,Spells,Troops}
    Clan Games
    upgrade{,/hero}
    buildings

Everything else is printed as a deletion candidate.
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TPL = ROOT / "Templates"

SCANNED_DIRS = {
    "Smart_Auto_train/Army Troops",
    "Smart_Auto_train/Spells",
    "Smart_Auto_train/Siege Machines",
    "Smart_Auto_train/Train_Tab",
    "Smart_Auto_train/to_train",
    "Clan Capital/Scenery",
    "Clan Capital/Spells",
    "Clan Capital/Troops",
    "Clan Games",
    "upgrade",
    "upgrade/hero",
    "buildings",
}

literal_re = re.compile(r"[\w \-+&./]+\.(?:png|ico|jpg|jpeg|webp)\b")
# Names referenced WITHOUT the extension (find_template_path / match
# callers). Keep in sync with the code when a new bare-name lookup is
# added - see Templates/README.md.
BARE_NAMES = {
    "edit_army_btn",   # smart_train_validators (Smart_Auto_train walk)
    "use_button",      # quick_train (referenced with .png, listed for clarity)
}

referenced: set[str] = set()
for base in (ROOT / "COCbot", ROOT / "tools"):
    for path in base.rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in literal_re.findall(text):
            referenced.add(Path(match.strip()).name.lower())
        # Bare names passed to find_template_path()/match() get the
        # extension appended by the loader.
        for bare in BARE_NAMES:
            referenced.add(f"{bare}.png")

candidates: list[Path] = []
kept = 0
IMAGE_EXTS = {".png", ".ico", ".jpg", ".jpeg", ".webp"}
for path in sorted(p for p in TPL.rglob("*") if p.is_file()):
    if path.suffix.lower() not in IMAGE_EXTS:
        continue  # documentation and other non-template files
    rel = path.relative_to(TPL).as_posix()
    in_scanned = any(rel.startswith(d + "/") for d in SCANNED_DIRS)
    if in_scanned or path.name.lower() in referenced:
        kept += 1
        continue
    candidates.append(path)

size = sum(p.stat().st_size for p in candidates)
print(f"referenced/kept: {kept}   deletion candidates: {len(candidates)}   "
      f"reclaim: {size / 1e6:.2f} MB\n")
for p in candidates:
    print(f"{p.stat().st_size / 1024:8.0f} KB  {p.relative_to(TPL)}")
