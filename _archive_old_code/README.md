# Archived legacy code

This directory stores source files removed from the active runtime but kept for
reference during the MVVM / feature-driven migration.

Nothing here is imported by `run.py` or by `COCbot/**`. Do not add this folder
to `sys.path` and do not ship it in the built executable.

## Purge batch 1 — 2026-11-11

Base commit: `ee12a94` (`assets: add new troop and spell templates`)

| Archived file | Original path | Lines | Reason |
|---|---|---:|---|
| `COCbot/platform/ahk.py` | `COCbot/platform/ahk.py` | 30 | AutoHotkey interaction is no longer used; ADB is the only input backend. Zero imports found. |
| `COCbot/vision/read_text/gold.py` | `COCbot/vision/read_text/gold.py` | 17 | Orphan wrapper around `read_text.numbers.read_number`; never imported. |
| `COCbot/vision/read_text/elixir.py` | `COCbot/vision/read_text/elixir.py` | 17 | Orphan wrapper around `read_text.numbers.read_number`; never imported. |
| `COCbot/vision/read_text/dark_elixir.py` | `COCbot/vision/read_text/dark_elixir.py` | 17 | Orphan wrapper around `read_text.numbers.read_number`; never imported. |

### Evidence

Import reachability was scanned with an AST walker starting from `run.py`
(`COCbot.gui.app`). The four files above were not reachable and had no static
importer. All remaining "unreachable" modules were `__init__.py` files that
Python imports implicitly.

### Restore a file

```powershell
# Example: restore gold.py
Move-Item _archive_old_code/COCbot/vision/read_text/gold.py COCbot/vision/read_text/gold.py
```

Only restore a file after re-checking that a live module imports it. Restoring
`ahk.py` also requires re-adding the AutoHotkey paths to the active config.
