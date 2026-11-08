# ==== COCbot/utils/stats_manager.py ====
import json
from pathlib import Path

import COCbot.core.paths  # noqa: F401
from COCbot.core.config import BASE_DIR, MAX_VILLAGES


def _stats_file_path(village_idx: int) -> Path:
    profiles_dir = Path(BASE_DIR) / 'profiles'
    profiles_dir.mkdir(exist_ok=True)
    return profiles_dir / f'Stats_{village_idx}.json'


def _load_stats_from_disk(village_idx: int) -> dict:
    path = _stats_file_path(village_idx)
    if not path.exists():
        return {
            'gold': 0, 'elixir': 0, 'de': 0, 'attacks': 0,
            'stars': {'0': 0, '1': 0, '2': 0, '3': 0},
            'last_update_ts': 0,
        }
    try:
        with open(path, 'r') as f:
            data = json.load(f)
        data.setdefault('gold', 0)
        data.setdefault('elixir', 0)
        data.setdefault('de', 0)
        data.setdefault('attacks', 0)
        data.setdefault('stars', {'0': 0, '1': 0, '2': 0, '3': 0})
        data.setdefault('last_update_ts', 0)
        return data
    except Exception:
        return {
            'gold': 0, 'elixir': 0, 'de': 0, 'attacks': 0,
            'stars': {'0': 0, '1': 0, '2': 0, '3': 0},
            'last_update_ts': 0,
        }


def zero_all_stats_files() -> None:
    zeroed = {
        'gold': 0, 'elixir': 0, 'de': 0, 'attacks': 0,
        'stars': {'0': 0, '1': 0, '2': 0, '3': 0},
        'last_update_ts': 0,
    }
    profiles_dir = Path(BASE_DIR) / 'profiles'
    profiles_dir.mkdir(parents=True, exist_ok=True)

    for vidx in range(1, MAX_VILLAGES + 1):
        path = profiles_dir / f'Stats_{vidx}.json'
        try:
            with path.open('w') as fh:
                json.dump(zeroed, fh, indent=2)
        except Exception as e:
            print(f'[ERROR] could not reset {path}: {e}')
