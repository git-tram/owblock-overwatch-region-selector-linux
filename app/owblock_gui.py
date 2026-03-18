#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from owblock import OWBlockError, OWBlockManager

PRESETS: dict[str, list[str]] = {
    "Asia": ["Singapore", "Tokyo", "South Korea", "Taiwan", "Saudi Arabia"],
    "Europe": ["Finland", "Netherlands"],
    "Americas": ["USA - Central", "USA - East", "USA - West", "Brazil"],
    "Oceania": ["Australia"],
}


def default_regions_path() -> str:
    base = Path(sys.argv[0]).resolve().parent
    candidate = base / "regions.json"
    if candidate.exists():
        return str(candidate)
    candidate = Path(__file__).resolve().with_name("regions.json")
    if candidate.exists():
        return str(candidate)
    return "regions.json"


def default_icon_path() -> Path | None:
    base = Path(sys.argv[0]).resolve().parent
    candidate = base / "owblock.png"
    if candidate.exists():
        return candidate
    candidate = Path(__file__).resolve().with_name("owblock.png")
    if candidate.exists():
        return candidate
    return None


class MainWindow(QMainWindow):
    def __init__(self, regions_file: str) -> None:
        super().__init__()
        self.setWindowTitle("Overwatch Region Blocker")
        self.resize(860, 680)

        icon_path = default_icon_path()
        if icon_path is not None:
            self.setWindowIcon(QIcon(str(icon_path)))

        self.regions_file = regions_file
        self.manager = OWBlockManager(regions_file)
        self.initial_status: dict[str, bool] = {}

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        self.info_label = QLabel()
        layout.addWidget(self.info_label)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter regions or descriptions...")
        self.search.textChanged.connect(self.apply_filter)
        layout.addWidget(self.search)

        self.region_tree = QTreeWidget()
        self.region_tree.setColumnCount(2)
        self.region_tree.setHeaderLabels(["Region", "Description / Counts"])
        self.region_tree.setRootIsDecorated(False)
        self.region_tree.setAlternatingRowColors(True)
        self.region_tree.header().setStretchLastSection(True)
        self.region_tree.setUniformRowHeights(True)
        layout.addWidget(self.region_tree)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Presets:"))
        self.preset_asia_btn = QPushButton("Block Asia")
        self.preset_europe_btn = QPushButton("Block Europe")
        self.preset_americas_btn = QPushButton("Block Americas")
        self.preset_oceania_btn = QPushButton("Block Oceania")
        self.clear_checks_btn = QPushButton("Clear All Checks")
        for btn in [
            self.preset_asia_btn,
            self.preset_europe_btn,
            self.preset_americas_btn,
            self.preset_oceania_btn,
            self.clear_checks_btn,
        ]:
            preset_row.addWidget(btn)
        preset_row.addStretch(1)
        layout.addLayout(preset_row)

        row = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.apply_btn = QPushButton("Apply Changes")
        self.unblock_all_btn = QPushButton("Unblock All")
        row.addWidget(self.refresh_btn)
        row.addWidget(self.apply_btn)
        row.addWidget(self.unblock_all_btn)
        layout.addLayout(row)

        layout.addWidget(QLabel("Activity log"))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self.refresh_btn.clicked.connect(self.refresh_regions)
        self.apply_btn.clicked.connect(self.apply_changes)
        self.unblock_all_btn.clicked.connect(self.unblock_all)
        self.preset_asia_btn.clicked.connect(lambda: self.apply_preset("Asia"))
        self.preset_europe_btn.clicked.connect(lambda: self.apply_preset("Europe"))
        self.preset_americas_btn.clicked.connect(lambda: self.apply_preset("Americas"))
        self.preset_oceania_btn.clicked.connect(lambda: self.apply_preset("Oceania"))
        self.clear_checks_btn.clicked.connect(self.clear_all_checks)

        self.refresh_regions()

    def append_log(self, text: str) -> None:
        self.log.appendPlainText(text)

    def update_info(self) -> None:
        region_count = len(self.manager.list_regions())
        self.info_label.setText(
            f"regions file: {self.regions_file} | privilege: running as root | loaded regions: {region_count}"
        )

    def region_details(self, region: str) -> str:
        data = self.manager.regions[region]
        desc = data.get("description", "").strip() or "No code"
        ipv4_count = len(data.get("ipv4", []))
        ipv6_count = len(data.get("ipv6", []))
        total = ipv4_count + ipv6_count
        return f"{desc} • {total} ranges (IPv4: {ipv4_count}, IPv6: {ipv6_count})"

    def refresh_regions(self) -> None:
        try:
            self.manager = OWBlockManager(self.regions_file)
            self.initial_status = self.manager.get_status_map()
            self.populate_from_status(self.initial_status)
            self.update_info()
            self.append_log("Refreshed region status.")
        except Exception as e:
            self.show_error(str(e))

    def populate_from_status(self, status_map: dict[str, bool]) -> None:
        filter_text = self.search.text().strip().lower()
        self.region_tree.clear()

        for region in self.manager.list_regions():
            details = self.region_details(region)
            desc = self.manager.regions[region].get("description", "")
            match_text = f"{region} {details} {desc}".lower()
            if filter_text and filter_text not in match_text:
                continue

            item = QTreeWidgetItem([region, details])
            item.setData(0, Qt.UserRole, region)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            item.setCheckState(0, Qt.Checked if status_map.get(region, False) else Qt.Unchecked)
            self.region_tree.addTopLevelItem(item)

        self.region_tree.resizeColumnToContents(0)

    def apply_filter(self) -> None:
        self.populate_from_status(self.wanted_status_map())

    def wanted_status_map(self) -> dict[str, bool]:
        wanted = dict(self.initial_status)
        for i in range(self.region_tree.topLevelItemCount()):
            item = self.region_tree.topLevelItem(i)
            region = item.data(0, Qt.UserRole)
            wanted[region] = item.checkState(0) == Qt.Checked
        return wanted

    def set_regions_checked(self, regions: list[str], checked: bool) -> int:
        targets = set(regions)
        changed = 0
        for i in range(self.region_tree.topLevelItemCount()):
            item = self.region_tree.topLevelItem(i)
            region = item.data(0, Qt.UserRole)
            if region in targets:
                item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
                changed += 1
        return changed

    def apply_preset(self, preset_name: str) -> None:
        regions = PRESETS.get(preset_name, [])
        changed = self.set_regions_checked(regions, True)
        self.append_log(
            f"Preset selected: {preset_name} ({changed} visible regions checked). Click Apply Changes to enforce."
        )

    def clear_all_checks(self) -> None:
        for i in range(self.region_tree.topLevelItemCount()):
            item = self.region_tree.topLevelItem(i)
            item.setCheckState(0, Qt.Unchecked)
        self.append_log("Cleared all visible checkboxes. Click Apply Changes to enforce.")

    def apply_changes(self) -> None:
        try:
            self.manager = OWBlockManager(self.regions_file)
            actual = self.manager.get_status_map()
            wanted = self.wanted_status_map()

            blocked = 0
            unblocked = 0
            for region in self.manager.list_regions():
                old = actual.get(region, False)
                new = wanted.get(region, False)
                if new and not old:
                    self.manager.block_region(region)
                    self.append_log(f"Blocked {region}")
                    blocked += 1
                elif not new and old:
                    self.manager.unblock_region(region)
                    self.append_log(f"Unblocked {region}")
                    unblocked += 1

            self.refresh_regions()
            QMessageBox.information(
                self,
                "Done",
                f"Applied firewall changes.\nBlocked: {blocked}\nUnblocked: {unblocked}"
            )
        except subprocess.CalledProcessError as e:
            self.show_error(e.stderr or str(e))
        except Exception as e:
            self.show_error(str(e))

    def unblock_all(self) -> None:
        try:
            self.manager.unblock_all()
            self.append_log("Unblocked all regions.")
            self.refresh_regions()
        except Exception as e:
            self.show_error(str(e))

    def show_error(self, message: str) -> None:
        self.append_log(f"ERROR: {message}")
        QMessageBox.critical(self, "Error", message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--regions-file", default=default_regions_path())
    args = parser.parse_args()

    app = QApplication(sys.argv)

    icon_path = default_icon_path()
    if icon_path is not None:
        app.setWindowIcon(QIcon(str(icon_path)))

    if hasattr(os, "geteuid") and os.geteuid() != 0:
        QMessageBox.critical(
            None,
            "Administrator privileges required",
            "OWBlock must be launched with administrator privileges.\n\n"
            "Use the installed launcher 'OWBlock (Admin)' or run:\n"
            "owblock-admin"
        )
        sys.exit(1)

    try:
        window = MainWindow(args.regions_file)
    except OWBlockError as e:
        QMessageBox.critical(None, "Error", str(e))
        sys.exit(1)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
