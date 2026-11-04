# main.py
"""Prism application entry point."""

import sys
from PyQt6.QtWidgets import QApplication
from ui.login_window import LoginWindow
from ui.main_window import MainWindow

# Reference to keep the dashboard window active in memory
active_main_window = None
active_login_window = None

def launch_main_dashboard(user_id: str, login_win: LoginWindow):
    global active_main_window, active_login_window
    active_login_window = login_win
    login_win.hide()
    active_main_window = MainWindow(user_id)
    active_main_window.show()

def main():
    global active_login_window
    app = QApplication(sys.argv)
    app.setApplicationName("Prism")
    app.setOrganizationName("Prism")

    login_win = LoginWindow()
    active_login_window = login_win
    login_win.login_successful.connect(lambda uid: launch_main_dashboard(uid, login_win))
    login_win.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()