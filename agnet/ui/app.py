"""Cửa sổ chính của phần mềm quản lý Agnet."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

from ..core import settings as S
from ..env import load_env
from . import i18n, theme
from .page_account import AccountPage
from .page_flows import FlowsPage
from .page_library import LibraryPage
from .page_runs import RunsPage
from .page_settings import SettingsPage


class MainWindow(QMainWindow):
    def __init__(self, flows_path: str | Path, db_path: str | Path,
                 settings_path: str | Path | None = None, env_path: str | Path | None = None,
                 output_root: str | Path | None = None):
        super().__init__()
        self.setWindowTitle("Agnet — quản lý luồng viết kịch bản")
        self.resize(1040, 780)

        self.runs = RunsPage(flows_path, db_path)
        self.library = LibraryPage(output_root)
        self.flows = FlowsPage(flows_path)
        self.general = SettingsPage(settings_path, env_path)
        self.account = AccountPage(flows_path, db_path)
        self.flows.changed.connect(self.runs.refresh)
        self.general.changed.connect(self.apply_settings)

        tabs = QTabWidget()
        tabs.addTab(self.runs, "Bảng điều khiển")
        tabs.addTab(self.library, "Kho kịch bản")
        tabs.addTab(self.flows, "Cài đặt luồng")
        tabs.addTab(self.general, "Cài đặt chung")
        tabs.addTab(self.account, "Tài khoản Claude")
        self.setCentralWidget(tabs)
        self.statusBar().showMessage(f"flows: {flows_path}   ·   db: {db_path}")
        self.apply_settings(S.load(settings_path))

    def apply_settings(self, s: S.Settings) -> None:
        """Áp chủ đề và ngôn ngữ ngay, không cần mở lại ứng dụng."""
        app = QApplication.instance()
        if app is not None:
            theme.apply_theme(app, s.theme)
        i18n.apply(self, s.language)


def run(flows_path: str | Path = "config/flows.yaml", db_path: str | Path = "agnet.db") -> int:
    load_env()
    app = QApplication.instance() or QApplication(sys.argv)
    w = MainWindow(flows_path, db_path)
    w.show()
    return app.exec()
