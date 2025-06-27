import sys
import os
import json
import time
import subprocess
from typing import List, Dict
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation, QEasingCurve
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QAction
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QFileDialog, QListWidget, QListWidgetItem, QStackedWidget,
    QLineEdit, QMessageBox, QTabWidget, QFrame, QFormLayout, QDialog,
    QStyle, QProgressBar, QSizePolicy, QSplashScreen
)
def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default
def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
def format_seconds(seconds):
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:d}:{m:02d}:{s:02d}"
def get_icon_pixmap(icon_path):
    if os.path.exists(icon_path):
        return QPixmap(icon_path)
    return QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon).pixmap(48, 48)
class AnimatedSplashScreen(QSplashScreen):
    def __init__(self, pixmap, duration=2000):
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen)
        self.setWindowOpacity(0)
        self.duration = duration
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(700)
        self.anim.setStartValue(0)
        self.anim.setEndValue(1)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
    def showEvent(self, event):
        super().showEvent(event)
        self.anim.start()
        QTimer.singleShot(self.duration, self.fade_out)
    def fade_out(self):
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(500)
        anim.setStartValue(1)
        anim.setEndValue(0)
        anim.finished.connect(self.close)
        anim.start()
class AddGameDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Game")
        self.setFixedSize(400, 220)
        layout = QFormLayout(self)
        self.name_input = QLineEdit(self)
        self.exec_input = QLineEdit(self)
        self.icon_input = QLineEdit(self)
        exec_btn = QPushButton("Browse", self)
        icon_btn = QPushButton("Browse", self)
        exec_btn.clicked.connect(self.browse_exec)
        icon_btn.clicked.connect(self.browse_icon)
        exec_layout = QHBoxLayout()
        exec_layout.addWidget(self.exec_input)
        exec_layout.addWidget(exec_btn)
        icon_layout = QHBoxLayout()
        icon_layout.addWidget(self.icon_input)
        icon_layout.addWidget(icon_btn)
        layout.addRow("Game Name:", self.name_input)
        layout.addRow("Executable:", exec_layout)
        layout.addRow("Icon (optional):", icon_layout)
        btns = QHBoxLayout()
        ok = QPushButton("Add")
        cancel = QPushButton("Cancel")
        ok.clicked.connect(self.accept)
        cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addRow(btns)
    def browse_exec(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Executable")
        if file:
            self.exec_input.setText(file)
    def browse_icon(self):
        file, _ = QFileDialog.getOpenFileName(self, "Select Icon", filter="Icons (*.ico *.png *.jpg)")
        if file:
            self.icon_input.setText(file)
    def get_data(self):
        return (
            self.name_input.text().strip(),
            self.exec_input.text().strip(),
            self.icon_input.text().strip()
        )
class GameProcessWatcher(QThread):
    finished = pyqtSignal(float)
    def __init__(self, exec_path):
        super().__init__()
        self.exec_path = exec_path
        self.start_time = time.time()
        self.proc = None
    def run(self):
        try:
            self.proc = subprocess.Popen([self.exec_path], shell=False)
            self.proc.wait()
        except Exception:
            pass
        duration = time.time() - self.start_time
        self.finished.emit(duration)
class GameWidget(QWidget):
    launch_clicked = pyqtSignal(str)
    def __init__(self, game: dict, playtime: int):
        super().__init__()
        self.game = game
        self.init_ui(playtime)
    def init_ui(self, playtime):
        layout = QHBoxLayout(self)
        icon_label = QLabel(self)
        pixmap = get_icon_pixmap(self.game.get("icon_path", ""))
        icon_label.setPixmap(pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        icon_label.setFixedSize(54, 54)
        info_layout = QVBoxLayout()
        name = QLabel(f"<b>{self.game['name']}</b>")
        name.setStyleSheet("font-size: 18px;")
        pt = QLabel(f"Total Playtime: {format_seconds(playtime)}")
        self.playtime_label = pt
        info_layout.addWidget(name)
        info_layout.addWidget(pt)
        launch_btn = QPushButton("Launch")
        launch_btn.setStyleSheet("""
            QPushButton {
                background-color: #2176FF; color: white; padding: 8px 24px; border-radius: 14px;
                font-weight: bold; font-size: 14px;
            }
            QPushButton:hover { background-color: #3355AA; }
        """)
        launch_btn.clicked.connect(lambda: self.launch_clicked.emit(self.game['name']))
        layout.addWidget(icon_label)
        layout.addLayout(info_layout)
        layout.addStretch()
        layout.addWidget(launch_btn)
    def update_playtime(self, seconds):
        self.playtime_label.setText(f"Total Playtime: {format_seconds(seconds)}")
class GameListTab(QWidget):
    def __init__(self, launcher):
        super().__init__()
        self.launcher = launcher
        self.list_layout = QVBoxLayout(self)
        self.list_layout.setSpacing(18)
        self.list_layout.setContentsMargins(30, 20, 30, 20)
        self.refresh_games()
        add_btn = QPushButton("Add Game")
        add_btn.setIcon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        add_btn.setFixedHeight(36)
        add_btn.setStyleSheet("""
            QPushButton {
                background: #43bccd; color: #fff; border-radius: 18px;
                font-weight: bold; font-size: 15px;
            }
            QPushButton:hover { background: #3699a6; }
        """)
        add_btn.clicked.connect(self.add_game)
        self.list_layout.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignRight)
        self.list_layout.addStretch()
    def refresh_games(self):
        for i in reversed(range(self.list_layout.count() - 2)):
            widget = self.list_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        for game in self.launcher.games:
            playtime = self.launcher.playtimes.get(game["name"], 0)
            widget = GameWidget(game, playtime)
            widget.launch_clicked.connect(self.launcher.launch_game)
            self.list_layout.insertWidget(self.list_layout.count() - 2, widget)
    def add_game(self):
        dlg = AddGameDialog(self)
        if dlg.exec():
            name, exec_path, icon_path = dlg.get_data()
            if not (name and exec_path):
                QMessageBox.warning(self, "Input Error", "Game name and executable are required.")
                return
            if not os.path.isfile(exec_path):
                QMessageBox.warning(self, "Input Error", "Executable not found.")
                return
            if icon_path and not os.path.isfile(icon_path):
                QMessageBox.warning(self, "Input Error", "Icon file not found.")
                return
            for g in self.launcher.games:
                if g["name"] == name:
                    QMessageBox.warning(self, "Duplicate", "Game with this name already exists.")
                    return
            self.launcher.games.append({
                "name": name,
                "exec_path": exec_path,
                "icon_path": icon_path
            })
            self.launcher.save_games()
            self.refresh_games()
class StatsTab(QWidget):
    def __init__(self, launcher):
        super().__init__()
        self.launcher = launcher
        self.layout = QVBoxLayout(self)
        self.refresh_stats()
    def refresh_stats(self):
        for i in reversed(range(self.layout.count())):
            w = self.layout.itemAt(i).widget()
            if w:
                w.deleteLater()
        title = QLabel("<h2>Playtime Statistics</h2>")
        self.layout.addWidget(title)
        total = 0
        for game in self.launcher.games:
            name = game["name"]
            pt = self.launcher.playtimes.get(name, 0)
            self.layout.addWidget(QLabel(f"{name}: <b>{format_seconds(pt)}</b>"))
            total += pt
        self.layout.addWidget(QLabel(f"<hr/>Total Playtime: <b>{format_seconds(total)}</b>"))
        self.layout.addStretch()
class SettingsTab(QWidget):
    def __init__(self, launcher):
        super().__init__()
        self.launcher = launcher
        self.layout = QVBoxLayout(self)
        info = QLabel(
            "<h2>Settings & Help</h2><ul>"
            "<li>Edit or remove games via <b>games.json</b></li>"
            "<li>Data stored in same directory as launcher</li>"
            "<li>If errors occur, check JSON files for corruption</li>"
            "<li>Feedback? Open source at "
            "<a href='https://github.com/driizzyy/custom-game-launcher' style='color:#2176FF;'>"
            "My Github Repo</a></li>"
            "</ul>"
        )
        info.setOpenExternalLinks(True)
        self.layout.addWidget(info)
        self.layout.addStretch()
class GameLauncher(QMainWindow):
    GAMES_FILE = "games.json"
    PLAYTIME_FILE = "playtime.json"
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EXO Launcher V1.0")
        self.setWindowIcon(QIcon(get_icon_pixmap("")))
        self.setMinimumSize(850, 540)
        self.setStyleSheet("""
            QMainWindow { background: #212532; }
            QWidget { color: #e6e9f0; font-family: 'Segoe UI', Arial, sans-serif; }
            QLabel { font-size: 15px; }
        """)
        self.games = load_json(self.GAMES_FILE, [])
        self.playtimes = load_json(self.PLAYTIME_FILE, {})
        self.current_game_process = None
        self.init_ui()
    def init_ui(self):
        main = QWidget()
        root_layout = QHBoxLayout(main)
        self.tab_btns = []
        tabs_layout = QVBoxLayout()
        tabs_layout.setSpacing(18)
        tab_names = [
            ("Games", "SP_ComputerIcon"),
            ("Statistics", "SP_FileDialogInfoView"),
            ("Settings", "SP_FileDialogContentsView")
        ]
        for i, (name, icon) in enumerate(tab_names):
            btn = QPushButton(QIcon(QApplication.style().standardIcon(getattr(QStyle.StandardPixmap, icon))), f"  {name}")
            btn.setFixedHeight(48)
            btn.setStyleSheet("""
                QPushButton {
                    background: #282f45;
                    border: none;
                    border-radius: 15px;
                    padding: 8px;
                    text-align: left;
                    font-weight: 500;
                    font-size: 16px;
                }
                QPushButton:checked, QPushButton:hover {
                    background: #2176FF;
                    color: #fff;
                }
            """)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, idx=i: self.switch_tab(idx))
            self.tab_btns.append(btn)
            tabs_layout.addWidget(btn)
        tabs_layout.addStretch()
        tabs_frame = QFrame()
        tabs_frame.setLayout(tabs_layout)
        tabs_frame.setFixedWidth(140)
        self.tabs = QStackedWidget()
        self.gamelist_tab = GameListTab(self)
        self.stats_tab = StatsTab(self)
        self.settings_tab = SettingsTab(self)
        self.tabs.addWidget(self.gamelist_tab)
        self.tabs.addWidget(self.stats_tab)
        self.tabs.addWidget(self.settings_tab)
        root_layout.addWidget(tabs_frame)
        root_layout.addWidget(self.tabs)
        root_layout.setStretch(1, 1)
        self.setCentralWidget(main)
        self.switch_tab(0)
        self.tabs.currentChanged.connect(self.animate_tab_switch)
    def switch_tab(self, idx):
        for i, btn in enumerate(self.tab_btns):
            btn.setChecked(i == idx)
        self.tabs.setCurrentIndex(idx)
        if idx == 0:
            self.gamelist_tab.refresh_games()
        elif idx == 1:
            self.stats_tab.refresh_stats()
    def animate_tab_switch(self):
        widget = self.tabs.currentWidget()
        widget.setWindowOpacity(0)
        anim = QPropertyAnimation(widget, b"windowOpacity")
        anim.setDuration(350)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.start()
    def launch_game(self, game_name):
        game = next((g for g in self.games if g["name"] == game_name), None)
        if not game:
            QMessageBox.warning(self, "Error", "Game not found.")
            return
        exec_path = game["exec_path"]
        if not os.path.isfile(exec_path):
            QMessageBox.critical(self, "Missing Executable", "Game executable not found.")
            return
        watcher = GameProcessWatcher(exec_path)
        self.current_game_process = watcher
        watcher.finished.connect(lambda dur, name=game_name: self.handle_game_exit(name, dur))
        watcher.start()
        QMessageBox.information(self, "Launching", f"Game '{game_name}' launched!\nPlaytime tracking started.")
    def handle_game_exit(self, name, dur):
        prev = self.playtimes.get(name, 0)
        self.playtimes[name] = prev + int(dur)
        self.save_playtimes()
        self.gamelist_tab.refresh_games()
        self.stats_tab.refresh_stats()
        QMessageBox.information(self, "Game Closed", f"{name} play session ended.\nSession: {format_seconds(int(dur))}\nTotal: {format_seconds(self.playtimes[name])}")
    def save_games(self):
        save_json(self.GAMES_FILE, self.games)
    def save_playtimes(self):
        save_json(self.PLAYTIME_FILE, self.playtimes)
def main():
    app = QApplication(sys.argv)
    splash_pix = QPixmap(220, 220)
    splash_pix.fill(Qt.GlobalColor.transparent)
    splash = AnimatedSplashScreen(splash_pix)
    logo = QLabel(splash)
    logo.setPixmap(QPixmap(48, 48).scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
    logo.setText("<h1 style='color:#2176FF; margin-top:70px;'>EXO Launcher</h1>")
    logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
    logo.setGeometry(20, 40, 180, 160)
    splash.show()
    QTimer.singleShot(1800, lambda: splash.close())
    launcher = GameLauncher()
    QTimer.singleShot(2100, launcher.show)
    sys.exit(app.exec())
if __name__ == "__main__":
    main()