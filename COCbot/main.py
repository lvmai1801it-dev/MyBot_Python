"""MVVM application composition root.

Run with ``python -m COCbot.main``. The legacy ``run.py`` entry point is kept
until the remaining features reach parity.
"""

from __future__ import annotations

import ctypes
import os
import sys

import COCbot.qt_startup  # noqa: F401  (torch before PyQt5)

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from COCbot.app.orchestrator import BotOrchestrator
from COCbot.app import state as legacy_state
from COCbot.core.adb import AdbClient
from COCbot.core.config import ConfigStore, load_config
from COCbot.core.config.paths import get_project_paths
from COCbot.core.logging import build_logger
from COCbot.core.vision import (
    NumberOcr,
    RedlineDetector,
    ScreenCapture,
    TemplateMatcher,
    YoloDetector,
)
from COCbot.features.accounts.model import AccountsModel
from COCbot.features.accounts.view import AccountsView
from COCbot.features.accounts.viewmodel import AccountsViewModel
from COCbot.features.attack.army_bar import ArmyBarScanner
from COCbot.features.attack.battle import BattleService, FullAttackStep
from COCbot.features.attack.executor import AttackExecutor
from COCbot.features.attack.model import AttackModel
from COCbot.features.attack.view import AttackView
from COCbot.features.attack.viewmodel import AttackViewModel
from COCbot.features.clan.model import ClanModel
from COCbot.features.clan.view import ClanView
from COCbot.features.clan.viewmodel import ClanViewModel
from COCbot.features.logs.model import LogsModel
from COCbot.features.logs.view import LogsView
from COCbot.features.logs.viewmodel import LogsViewModel
from COCbot.features.settings.model import SettingsModel
from COCbot.features.settings.view import SettingsView
from COCbot.features.settings.viewmodel import SettingsViewModel
from COCbot.features.statistics.model import StatisticsModel
from COCbot.features.statistics.view import StatisticsView
from COCbot.features.statistics.viewmodel import StatisticsViewModel
from COCbot.features.village.model import VillageActions, VillageModel, VillageStep
from COCbot.features.village.view import VillageView
from COCbot.features.village.viewmodel import VillageViewModel
from COCbot.game.account.shared_prefs import SharedPrefsManager
from COCbot.models.bot_state import BotEvent
from COCbot.models.enums import LogLevel
from COCbot.ui_components import apply_theme
from COCbot.viewmodels.main_viewmodel import MainViewModel
from COCbot.views.main_window import MainWindow


def _enable_dpi_awareness() -> None:
    """Enable crisp rendering on high-DPI Windows displays."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _configure_ssl() -> None:
    """Use certifi's CA bundle for the updater and HTTP calls."""
    try:
        import certifi

        ca_bundle = certifi.where()
        os.environ.setdefault("SSL_CERT_FILE", ca_bundle)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", ca_bundle)
    except Exception:
        pass


def main() -> int:
    """Build the object graph and run the Qt event loop."""
    _enable_dpi_awareness()
    _configure_ssl()

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    application = QApplication(sys.argv)
    apply_theme(application)

    config = load_config()
    config_store = ConfigStore(config)
    paths = get_project_paths()
    paths.ensure_runtime_dirs()
    logger = build_logger("mybot", config.logging)
    logger.info("Starting MVVM shell")

    # Transitional bridge for the shared_prefs manager, which still reads this.
    legacy_state.host = config.emulator.host
    legacy_state.emulator_key = config.emulator.emulator_type.value
    legacy_state.ld_index = config.emulator.ld_index

    adb = AdbClient(host=config.emulator.host, logger=logger)
    if not adb.connect(config.emulator.host, timeout=3.0):
        logger.warning("ADB is not connected; attack scans will fail until it is")
    adb_ready = adb.is_connected()

    logs_viewmodel = LogsViewModel()
    logs_viewmodel.append_event(
        BotEvent(level=LogLevel.INFO, message="MVVM shell started")
    )
    logs_viewmodel.append_event(
        BotEvent(
            level=LogLevel.SUCCESS if adb_ready else LogLevel.WARNING,
            message=(
                f"ADB {config.emulator.host} connected"
                if adb_ready
                else f"ADB {config.emulator.host} offline"
            ),
        )
    )
    logs_view = LogsView(logs_viewmodel)

    capture = ScreenCapture(adb, logger=logger)
    detector = YoloDetector(logger=logger)
    matcher = TemplateMatcher(logger=logger)
    redline = RedlineDetector(
        model_path=config.vision.redline_model,
        confidence=config.vision.confidence,
        offset_ratio=config.vision.redline_offset_ratio,
        logger=logger,
    )
    attack_model = AttackModel(
        capture=capture,
        detector=detector,
        redline=redline,
        adb=adb,
        config=config,
        config_store=config_store,
        logger=logger,
        allow_input=False,
    )
    ocr = NumberOcr(logger=logger)
    army_scanner = ArmyBarScanner(ocr=ocr, logger=logger)
    battle = BattleService(
        adb,
        capture,
        matcher,
        ocr=ocr,
        logger=logger,
        execute=False,
    )
    attack_executor = AttackExecutor(adb, logger=logger, execute=False)
    attack_viewmodel = AttackViewModel(attack_model)
    attack_view = AttackView(attack_viewmodel)

    accounts_model = AccountsModel(SharedPrefsManager())
    accounts_viewmodel = AccountsViewModel(accounts_model)
    accounts_view = AccountsView(accounts_viewmodel)

    settings_model = SettingsModel()
    settings_viewmodel = SettingsViewModel(settings_model, store=config_store)
    settings_view = SettingsView(settings_viewmodel)

    village_model = VillageModel(config_store, settings_model)
    village_viewmodel = VillageViewModel(village_model)
    village_view = VillageView(village_viewmodel)

    clan_model = ClanModel(config_store, settings_model)
    clan_viewmodel = ClanViewModel(clan_model)
    clan_view = ClanView(clan_viewmodel)

    statistics_model = StatisticsModel()
    statistics_viewmodel = StatisticsViewModel(statistics_model)
    statistics_view = StatisticsView(statistics_viewmodel)

    orchestrator = BotOrchestrator(
        [
            VillageStep(
                VillageActions(
                    adb,
                    capture,
                    matcher,
                    logger=logger,
                    execute=False,
                )
            ),
            FullAttackStep(
                attack_model,
                battle,
                army_scanner,
                attack_executor,
                execute=False,
            ),
        ],
        config=config,
        logger=logger,
        cycle_delay=1.0,
    )
    main_viewmodel = MainViewModel(orchestrator)
    main_viewmodel.event_emitted.connect(logs_viewmodel.append_event)

    def _reload_config_views(*_args: object) -> None:
        settings_viewmodel.reload()
        village_viewmodel.load()
        clan_viewmodel.load()

    settings_viewmodel.saved.connect(_reload_config_views)
    village_viewmodel.saved.connect(_reload_config_views)
    clan_viewmodel.saved.connect(_reload_config_views)

    window = MainWindow(
        logs_view,
        settings_view,
        village_view,
        accounts_view,
        clan_view,
        attack_view,
        statistics_view,
        main_viewmodel,
    )
    window.show()

    application.aboutToQuit.connect(main_viewmodel.shutdown)
    application.aboutToQuit.connect(accounts_viewmodel.shutdown)
    application.aboutToQuit.connect(attack_viewmodel.shutdown)

    if os.environ.get("MYBOT_SMOKE_TEST") == "1":
        from PyQt5.QtCore import QTimer

        QTimer.singleShot(1500, application.quit)

    return application.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
