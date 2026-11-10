# ==== COCbot/app/updater.py ====
import threading
import requests
from packaging import version
from PyQt5.QtCore import QObject, pyqtSignal

import COCbot.app.paths
from COCbot.app.version import __version__

LATEST_JSON_URL = "https://DredHandsome.github.io/mybot-pages/latest.json"


class Updater(QObject):
    update_available = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def check_for_update(self):
        def _worker():
            try:
                resp = requests.get(LATEST_JSON_URL, timeout=5)
                resp.raise_for_status()
                data = resp.json()
                remote = data.get('latest_version')
                url = data.get('download_url')
                if version.parse(remote) > version.parse(__version__):
                    self.update_available.emit(remote, url)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()
