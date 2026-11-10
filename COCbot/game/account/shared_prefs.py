"""Switch Clash of Clans accounts by backing up / restoring Android shared_prefs.

This mirrors MyBot's shared_prefs workflow:

  Profiles/<name>/shared_prefs/*.xml  (folder, not a single archive)
  Pull  = copy the game's current shared_prefs into the selected profile
  Push  = copy a profile's shared_prefs into the game
  Switch = Pull current account, then Push the target account

The game is force-stopped before a pull/push, and restarted afterwards.
Requires root (or an emulator whose adbd runs as root, e.g. MEmu).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tarfile
import time
from datetime import datetime
from pathlib import Path

from COCbot.app.paths import SRC_DIR
from COCbot.platform.adb_config import ADB_BIN

import COCbot.app.state as state

PACKAGE = "com.supercell.clashofclans"
ACCOUNTS_DIR = Path(SRC_DIR) / "profiles" / "accounts"
REMOTE_DIR = "/sdcard/cocbot_shared_prefs"
CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

# MyBot updates these encrypted entries in storage_new.xml before pushing.
# (old value, new value)
STORAGE_TAGS = [
    ("d0h6phQUOxO/uSfvat949w==", "FWCNTu39RUlYoSt0Y6mCwg=="),      # language
    ("MjhxqoFNUV+begGvsz3gkg==", "vJsDdCCIGCzyfC7c1FsIrA=="),      # zoom level
    ("7lJCTt3TmNyzikZuHh9wZQ==", "pmvEzdQuRQuKZob4KB0IeA=="),      # rated
    ("AQ+/D2n+JXPIPpMLdPZcqHpYSGJ5PpF3sOnowks5I5s=",
     "pmvEzdQuRQuKZob4KB0IeA=="),                                   # google disconnected
]


class SharedPrefsError(RuntimeError):
    pass


def _safe_name(name: str) -> str:
    name = (name or "").strip()
    name = re.sub(r"[^A-Za-z0-9._ -]+", "_", name)
    name = re.sub(r"\s+", "_", name).strip("._-")
    return name[:48] or "account"


class SharedPrefsManager:
    def __init__(self, package: str = PACKAGE):
        self.package = package
        self._root_mode = None
        self._host = None
        self.update_storage = True

    # ------------------------------------------------------------------ ADB
    def _get_host(self) -> str:
        if self._host:
            return self._host
        host = getattr(state, "host", None)
        if not host:
            try:
                import COCbot.app.bootstrap as main
                host = getattr(main, "host", None)
            except Exception:
                host = None

        if host and self._host_alive(host):
            self._host = host
            return host

        if host:
            # Try to reconnect the saved host first (ADB server may have dropped it).
            self._adb_connect(host)
            if self._host_alive(host):
                self._host = host
                return host

        detected = self._detect_host()
        if detected:
            print(f"[ACCOUNT] Dùng ADB host tự phát hiện: {detected}")
            self._host = detected
            return detected

        raise SharedPrefsError(
            "Chưa chọn emulator hoặc ADB chưa kết nối. "
            "Hãy bấm Start một lần hoặc kiểm tra adb devices.")

    def _adb_connect(self, host: str):
        try:
            subprocess.run(
                [ADB_BIN, "connect", host],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
                creationflags=CREATE_NO_WINDOW,
            )
            time.sleep(0.5)
        except Exception:
            pass

    def _host_alive(self, host: str) -> bool:
        try:
            p = subprocess.run(
                [ADB_BIN, "-s", host, "get-state"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW,
            )
            return p.returncode == 0 and "device" in (p.stdout or "")
        except Exception:
            return False

    def _detect_host(self) -> str:
        try:
            p = subprocess.run(
                [ADB_BIN, "devices"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                creationflags=CREATE_NO_WINDOW,
            )
            for line in (p.stdout or "").splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    return parts[0]
        except Exception:
            pass

        # Last resort: common emulator ADB ports.
        for host in ("127.0.0.1:21503", "127.0.0.1:5555",
                     "127.0.0.1:5556", "127.0.0.1:62001"):
            self._adb_connect(host)
            if self._host_alive(host):
                return host
        return ""

    def _adb(self, args, timeout=60):
        return subprocess.run(
            [ADB_BIN, "-s", self._get_host()] + list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )

    def _shell(self, cmd, timeout=60):
        return self._adb(["shell", cmd], timeout=timeout)

    def root_mode(self):
        if self._root_mode is not None:
            return self._root_mode
        try:
            p = self._shell("id")
            if p.returncode == 0 and "uid=0" in (p.stdout or ""):
                self._root_mode = "direct"
                return self._root_mode
            p = self._shell("su -c id")
            if p.returncode == 0 and "uid=0" in (p.stdout or ""):
                self._root_mode = "su"
                return self._root_mode
            self._adb(["root"], timeout=25)
            time.sleep(1.0)
            self._adb(["wait-for-device"], timeout=25)
            p = self._shell("id")
            if p.returncode == 0 and "uid=0" in (p.stdout or ""):
                self._root_mode = "direct"
                return self._root_mode
        except Exception as e:
            print(f"[ACCOUNT] root check error: {e}")
        try:
            p = self._shell("id")
            print(f"[ACCOUNT] root check failed: host={self._host} "
                  f"rc={p.returncode} out={(p.stdout or '').strip()!r} "
                  f"err={(p.stderr or '').strip()!r}")
            d = subprocess.run(
                [ADB_BIN, "devices"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, timeout=10,
                creationflags=CREATE_NO_WINDOW,
            )
            print(f"[ACCOUNT] adb devices: {(d.stdout or '').strip()!r}")
        except Exception:
            pass
        self._root_mode = None
        return None

    def root_label(self) -> str:
        mode = self.root_mode()
        if mode == "direct":
            return "quyền: adbd root sẵn có (không cần root thủ công)"
        if mode == "su":
            return "quyền: su"
        return "quyền: không đủ (dùng Supercell ID)"

    def _root_shell(self, cmd, timeout=90):
        mode = self.root_mode()
        if mode == "direct":
            return self._shell(cmd, timeout=timeout)
        if mode == "su":
            return self._shell(f'su -c "{cmd}"', timeout=timeout)
        raise SharedPrefsError(
            "Shared_prefs cần adbd root (MEmu/LDPlayer thường có sẵn). Nếu không có, dùng Supercell ID.")

    def _require_ok(self, proc, what: str):
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()
            raise SharedPrefsError(f"{what} thất bại: {err[:300]}")

    # --------------------------------------------------------------- paths
    @property
    def data_dir(self) -> str:
        return f"/data/data/{self.package}"

    @property
    def prefs_dir(self) -> str:
        return f"{self.data_dir}/shared_prefs"

    def android_id(self) -> str:
        p = self._shell("settings get secure android_id")
        return (p.stdout or "").strip()

    def profile_dir(self, name: str) -> Path:
        return ACCOUNTS_DIR / _safe_name(name)

    def local_prefs(self, name: str) -> Path:
        return self.profile_dir(name) / "shared_prefs"

    # ------------------------------------------------------------- profiles
    def list_profiles(self):
        ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)
        out = []
        for d in sorted(ACCOUNTS_DIR.iterdir()):
            if not d.is_dir():
                continue
            self._migrate_archive(d)
            prefs = d / "shared_prefs"
            files = len(list(prefs.glob("*"))) if prefs.is_dir() else 0
            meta = {}
            try:
                meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
            except Exception:
                pass
            out.append({
                "safe_name": d.name,
                "name": meta.get("name", d.name),
                "saved_at": meta.get("saved_at", ""),
                "android_id": meta.get("android_id", ""),
                "files": files,
                "exists": files >= 5,
            })
        return out

    def profile_names(self):
        return [p["name"] for p in self.list_profiles()]

    def has_profile(self, name: str) -> bool:
        prefs = self.local_prefs(name)
        return prefs.is_dir() and len(list(prefs.glob("*"))) >= 5

    def delete_profile(self, name: str):
        d = self._find_profile(name)
        shutil.rmtree(d, ignore_errors=True)
        print(f"[ACCOUNT] Deleted {d}")

    def _find_profile(self, name: str) -> Path:
        safe = _safe_name(name)
        direct = ACCOUNTS_DIR / safe
        if direct.is_dir():
            return direct
        for d in ACCOUNTS_DIR.glob("*"):
            try:
                meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
                if meta.get("name") == name or d.name == name:
                    return d
            except Exception:
                continue
        raise SharedPrefsError(f"Không tìm thấy profile '{name}'.")

    def _migrate_archive(self, d: Path):
        """Migrate old tar.gz layout to the folder layout MyBot uses."""
        archive = d / "shared_prefs.tar.gz"
        prefs = d / "shared_prefs"
        if archive.is_file() and not prefs.is_dir():
            try:
                with tarfile.open(archive, "r:gz") as tar:
                    try:
                        tar.extractall(d, filter="data")
                    except TypeError:
                        tar.extractall(d)
                print(f"[ACCOUNT] Migrated archive -> {prefs}")
            except Exception as e:
                print(f"[ACCOUNT] Migrate failed: {e}")

    # --------------------------------------------------------------- actions
    def pull_profile(self, name: str, close_game: bool = True):
        """Save the game's current shared_prefs into profile `name`."""
        if self.root_mode() is None:
            raise SharedPrefsError("Emulator không có adbd root. Dùng Supercell ID hoặc bật adb root.")

        pdir = self.profile_dir(name)
        pdir.mkdir(parents=True, exist_ok=True)
        tmp = pdir / "_pull_tmp"
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)

        print(f"[ACCOUNT] Pull -> {name}")
        if close_game:
            self._stop()
            time.sleep(0.6)

        try:
            self._pull_remote_to_local(self.prefs_dir, tmp)

            files = list(tmp.glob("*")) if tmp.is_dir() else []
            if len(files) < 5:
                raise SharedPrefsError(
                    f"Chỉ lấy được {len(files)} file shared_prefs (cần >=5).")

            prefs = pdir / "shared_prefs"
            old = pdir / "_old_shared_prefs"
            if old.exists():
                shutil.rmtree(old, ignore_errors=True)
            if prefs.exists():
                prefs.rename(old)
            tmp.rename(prefs)
            shutil.rmtree(old, ignore_errors=True)

            meta = {
                "name": name,
                "safe_name": pdir.name,
                "package": self.package,
                "saved_at": datetime.now().isoformat(timespec="seconds"),
                "android_id": self.android_id(),
                "host": self._get_host(),
                "files": len(files),
            }
            (pdir / "meta.json").write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[ACCOUNT] Pulled {len(files)} files -> {prefs}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            if close_game:
                self._launch()

    def push_profile(self, name: str, current_profile: str = "",
                     close_game: bool = True):
        """Restore profile `name` into the game.

        If `current_profile` is given, the current account is pulled first so
        its progress is not lost.
        """
        if self.root_mode() is None:
            raise SharedPrefsError("Emulator không có adbd root. Dùng Supercell ID hoặc bật adb root.")
        if not self.has_profile(name):
            raise SharedPrefsError(f"Profile '{name}' không có shared_prefs.")

        print(f"[ACCOUNT] Push -> {name}")
        if close_game:
            self._stop()
            time.sleep(0.8)

        try:
            if current_profile and _safe_name(current_profile) != _safe_name(name):
                try:
                    self._pull_without_launch(current_profile)
                except Exception as e:
                    print(f"[ACCOUNT] Không pull được account hiện tại: {e}")

            prefs = self.local_prefs(name)
            if self.update_storage:
                self._update_storage_new(prefs)
            self._push_local_to_remote(prefs, self.prefs_dir)
            print(f"[ACCOUNT] Pushed profile '{name}'")
        finally:
            if close_game:
                self._launch()
    def switch_profile(self, current_profile: str, target_profile: str):
        """Pull current account, then push the target account."""
        self.push_profile(target_profile, current_profile=current_profile,
                          close_game=True)

    # ------------------------------------------------------------- internals
    def _pull_without_launch(self, name: str):
        pdir = self.profile_dir(name)
        pdir.mkdir(parents=True, exist_ok=True)
        tmp = pdir / "_pull_tmp"
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)
        self._pull_remote_to_local(self.prefs_dir, tmp)
        files = list(tmp.glob("*")) if tmp.is_dir() else []
        if len(files) < 5:
            shutil.rmtree(tmp, ignore_errors=True)
            raise SharedPrefsError("Pull account hiện tại thất bại.")
        prefs = pdir / "shared_prefs"
        if prefs.exists():
            shutil.rmtree(prefs, ignore_errors=True)
        tmp.rename(prefs)
        meta = {
            "name": name,
            "safe_name": pdir.name,
            "package": self.package,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "android_id": self.android_id(),
            "host": self._get_host(),
            "files": len(files),
        }
        (pdir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[ACCOUNT] Auto-pulled {len(files)} files -> {prefs}")

    def _pull_remote_to_local(self, remote_prefs: str, local_dir: Path):
        # 1) direct adb pull from /data/data (works when adbd is root)
        p = self._adb(["pull", remote_prefs, str(local_dir)], timeout=180)
        if p.returncode == 0 and local_dir.is_dir() and any(local_dir.iterdir()):
            return
        # 2) fallback: copy to /sdcard, then pull
        shutil.rmtree(local_dir, ignore_errors=True)
        p = self._root_shell(
            f"rm -rf {REMOTE_DIR} && cp -r {remote_prefs} {REMOTE_DIR}")
        self._require_ok(p, "Copy shared_prefs")
        p = self._adb(["pull", REMOTE_DIR, str(local_dir)], timeout=180)
        self._root_shell(f"rm -rf {REMOTE_DIR}")
        self._require_ok(p, "Pull shared_prefs")

    def _push_local_to_remote(self, local_prefs: Path, remote_prefs: str):
        remote_parent = f"{REMOTE_DIR}_restore"
        self._shell(f"rm -rf {remote_parent} && mkdir -p {remote_parent}")
        p = self._adb(["push", str(local_prefs), remote_parent], timeout=180)
        self._require_ok(p, "Push shared_prefs")

        owner = (self._root_shell(
            f"stat -c %u:%g {self.data_dir}").stdout or "").strip() or "1000:1000"
        cmd = (
            f"rm -rf {remote_prefs} && "
            f"cp -r {remote_parent}/shared_prefs {remote_prefs} && "
            f"chown -R {owner} {remote_prefs} && "
            f"chmod 770 {remote_prefs} && "
            f"find {remote_prefs} -type f -exec chmod 660 {{}} \\; ; "
            f"restorecon -R {remote_prefs} 2>/dev/null || true"
        )
        p = self._root_shell(cmd, timeout=120)
        if "cp: " in (p.stderr or ""):
            raise SharedPrefsError(f"Restore thất bại: {p.stderr.strip()[:300]}")
        self._shell(f"rm -rf {remote_parent}")

    def _update_storage_new(self, local_prefs: Path):
        """Apply MyBot's storage_new.xml resets (language/zoom/rated)."""
        path = local_prefs / "storage_new.xml"
        if not path.is_file():
            return
        try:
            text = path.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            return

        updated = text
        for old, new in STORAGE_TAGS:
            tag = f'<string name="{old}">'
            pattern = re.compile(
                r'<string name="' + re.escape(old) + r'">.*?</string>',
                re.DOTALL,
            )
            replacement = f'<string name="{old}">{new}</string>'
            if pattern.search(updated):
                updated = pattern.sub(replacement, updated, count=1)
            elif "</map>" in updated:
                updated = updated.replace(
                    "</map>", "    " + replacement + "\n</map>", 1)

        if updated != text:
            path.write_text(updated, encoding="utf-8")
            print("[ACCOUNT] Updated storage_new.xml (language/zoom/rated)")

    def _stop(self):
        self._shell(f"am force-stop {self.package}")

    def _launch(self):
        self._shell(
            f"monkey -p {self.package} -c android.intent.category.LAUNCHER 1")
