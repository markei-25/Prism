"""Prism sign-in and account creation window."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

import auth


class LoginWindow(QWidget):
    login_successful = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setObjectName("login_window")
        self.setWindowTitle("Prism | Sign in")
        self.setMinimumSize(390, 540)
        self.resize(440, 590)
        self.setStyleSheet("""
            QWidget#login_window {
                background-color: #0F0F12;
                color: #FFFFFF;
                font-family: "Segoe UI";
            }
            QLabel#brand {
                color: #FFFFFF;
                font-size: 30px;
                font-weight: 700;
            }
            QLabel#tagline {
                color: #B7B7C7;
                font-size: 13px;
            }
            QLabel#form_label {
                color: #D7D7E0;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#status {
                color: #FF9B9B;
                font-size: 12px;
            }
            QLineEdit {
                background-color: #1A1A24;
                border: 1px solid #3A3A49;
                border-radius: 7px;
                padding: 11px 12px;
                color: #FFFFFF;
                font-size: 14px;
                selection-background-color: #00D2FF;
                selection-color: #0F0F12;
            }
            QLineEdit:focus {
                border: 2px solid #00D2FF;
            }
            QPushButton {
                min-height: 44px;
                border-radius: 7px;
                padding: 0 16px;
                font-size: 14px;
                font-weight: 650;
            }
            QPushButton#primary {
                background-color: #00D2FF;
                border: 1px solid #00D2FF;
                color: #0F0F12;
            }
            QPushButton#primary:hover {
                background-color: #39DFFF;
                border-color: #39DFFF;
            }
            QPushButton#secondary {
                background-color: #1A1A24;
                border: 1px solid #454554;
                color: #FFFFFF;
            }
            QPushButton#secondary:hover {
                border-color: #00D2FF;
                color: #FFFFFF;
            }
            QPushButton:focus {
                border: 2px solid #FFFFFF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 38, 42, 34)
        layout.setSpacing(11)

        brand = QLabel("PRISM")
        brand.setObjectName("brand")
        layout.addWidget(brand)

        accent = QFrame()
        accent.setFixedSize(46, 3)
        accent.setStyleSheet("background-color: #00D2FF; border: none;")
        layout.addWidget(accent)

        tagline = QLabel("Music, stories, and play in one place.")
        tagline.setObjectName("tagline")
        layout.addWidget(tagline)
        layout.addSpacing(15)

        heading = QLabel("Welcome back")
        heading.setStyleSheet("font-size: 22px; font-weight: 650;")
        layout.addWidget(heading)

        self.status_label = QLabel("")
        self.status_label.setObjectName("status")
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(18)
        self.status_label.setAccessibleName("Sign-in status")
        layout.addWidget(self.status_label)

        email_label = QLabel("Email")
        email_label.setObjectName("form_label")
        layout.addWidget(email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("you@example.com")
        self.email_input.setAccessibleName("Email")
        self.email_input.setInputMethodHints(Qt.InputMethodHint.ImhEmailCharactersOnly)
        layout.addWidget(self.email_input)

        password_label = QLabel("Password")
        password_label.setObjectName("form_label")
        layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Your password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setAccessibleName("Password")
        self.password_input.returnPressed.connect(self.handle_login)
        self.email_input.returnPressed.connect(self.password_input.setFocus)
        layout.addWidget(self.password_input)

        layout.addSpacing(8)

        self.login_btn = QPushButton("Sign in")
        self.login_btn.setObjectName("primary")
        self.login_btn.clicked.connect(self.handle_login)
        layout.addWidget(self.login_btn)

        self.signup_btn = QPushButton("Create an account")
        self.signup_btn.setObjectName("secondary")
        self.signup_btn.clicked.connect(self.handle_signup)
        layout.addWidget(self.signup_btn)

        layout.addStretch(1)

        footer = QLabel("Your Prism account keeps your listening library connected.")
        footer.setObjectName("tagline")
        footer.setWordWrap(True)
        layout.addWidget(footer)

    def handle_login(self):
        email = self.email_input.text()
        password = self.password_input.text()

        success, message, user_id = auth.login_user(email, password)
        if success and user_id:
            self.status_label.clear()
            self.login_successful.emit(user_id)
        else:
            self.status_label.setStyleSheet("color: #FF9B9B; font-size: 12px;")
            self.status_label.setText(message)

    def handle_signup(self):
        email = self.email_input.text()
        password = self.password_input.text()

        success, message = auth.register_user(email, password)
        self.status_label.setStyleSheet(
            "color: #9DECC0; font-size: 12px;" if success else "color: #FF9B9B; font-size: 12px;"
        )
        self.status_label.setText(message)
