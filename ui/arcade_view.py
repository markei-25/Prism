"""Embedded Arcade games adapted from PyBox under the MIT License."""

import random

from PyQt6.QtCore import QSize, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class SnakeBoard(QWidget):
    score_changed = pyqtSignal(int)
    state_changed = pyqtSignal(str)

    GRID_SIZE = 28
    STEP_MS = 100

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("snake_board")
        self.setAccessibleName("Snake game board")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.timer = QTimer(self)
        self.timer.setInterval(self.STEP_MS)
        self.timer.timeout.connect(self._advance)
        self.reset_game()

    def sizeHint(self) -> QSize:
        return self.minimumSizeHint()

    def minimumSizeHint(self) -> QSize:
        return QSize(420, 420)

    def reset_game(self):
        center = self.GRID_SIZE // 2
        self.snake: list[tuple[int, int]] = [(center - 1, center), (center, center)]
        self.direction: tuple[int, int] = (1, 0)
        self.next_direction = self.direction
        self.food: tuple[int, int] | None = self._new_food()
        self.score = 0
        self.state = "ready"
        self.timer.stop()
        self.score_changed.emit(self.score)
        self.state_changed.emit(self.state)
        self.update()

    def start_game(self):
        if self.state in ("over", "won"):
            self.reset_game()
        if self.state != "running":
            self.state = "running"
            self.timer.start()
            self.state_changed.emit(self.state)
            self.setFocus(Qt.FocusReason.OtherFocusReason)
            self.update()

    def toggle_pause(self):
        if self.state == "running":
            self.timer.stop()
            self.state = "paused"
        elif self.state in ("ready", "paused"):
            self.start_game()
            return
        else:
            return
        self.state_changed.emit(self.state)
        self.update()

    def pause_game(self):
        if self.state == "running":
            self.toggle_pause()

    def focusInEvent(self, event):
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        self.update()
        super().focusOutEvent(event)

    def _new_food(self) -> tuple[int, int] | None:
        occupied = set(getattr(self, "snake", ()))
        available = [
            (x, y)
            for x in range(self.GRID_SIZE)
            for y in range(self.GRID_SIZE)
            if (x, y) not in occupied
        ]
        return random.choice(available) if available else None

    def _advance(self):
        self.direction = self.next_direction
        head_x, head_y = self.snake[-1]
        dx, dy = self.direction
        next_head = (head_x + dx, head_y + dy)

        ate_food = next_head == self.food
        collidable = self.snake if ate_food else self.snake[1:]
        if (
            not 0 <= next_head[0] < self.GRID_SIZE
            or not 0 <= next_head[1] < self.GRID_SIZE
            or next_head in collidable
        ):
            self.timer.stop()
            self.state = "over"
            self.state_changed.emit(self.state)
            self.update()
            return

        self.snake.append(next_head)
        if ate_food:
            self.score += 1
            self.score_changed.emit(self.score)
            self.food = self._new_food()
            if self.food is None:
                self.timer.stop()
                self.state = "won"
                self.state_changed.emit(self.state)
        else:
            self.snake.pop(0)
        self.update()

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Space, Qt.Key.Key_Escape):
            self.toggle_pause()
            event.accept()
            return

        directions = {
            Qt.Key.Key_Left: (-1, 0),
            Qt.Key.Key_A: (-1, 0),
            Qt.Key.Key_Right: (1, 0),
            Qt.Key.Key_D: (1, 0),
            Qt.Key.Key_Up: (0, -1),
            Qt.Key.Key_W: (0, -1),
            Qt.Key.Key_Down: (0, 1),
            Qt.Key.Key_S: (0, 1),
        }
        requested = directions.get(key)
        if requested is not None:
            current_x, current_y = self.direction
            if requested != (-current_x, -current_y):
                self.next_direction = requested
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#101015"))

        side = max(0, min(self.width(), self.height()) - 20)
        board = self.rect().adjusted(
            (self.width() - side) // 2,
            (self.height() - side) // 2,
            -(self.width() - side) // 2,
            -(self.height() - side) // 2,
        )
        outline = QColor("#00D2FF") if self.hasFocus() else QColor("#343440")
        painter.setPen(QPen(outline, 2 if self.hasFocus() else 1))
        painter.setBrush(QColor("#141419"))
        painter.drawRoundedRect(board, 8, 8)

        inset = 10
        cell = (side - inset * 2) / self.GRID_SIZE
        left = board.left() + inset
        top = board.top() + inset
        painter.setPen(QPen(QColor("#24242D"), 1))
        for index in range(1, self.GRID_SIZE):
            offset = round(index * cell)
            painter.drawLine(
                round(left + offset),
                round(top),
                round(left + offset),
                round(top + cell * self.GRID_SIZE),
            )
            painter.drawLine(
                round(left),
                round(top + offset),
                round(left + cell * self.GRID_SIZE),
                round(top + offset),
            )

        if self.food is not None:
            x, y = self.food
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(
                round(left + x * cell + cell * 0.19),
                round(top + y * cell + cell * 0.19),
                max(1, round(cell * 0.62)),
                max(1, round(cell * 0.62)),
            )

        painter.setPen(Qt.PenStyle.NoPen)
        for index, (x, y) in enumerate(self.snake):
            inset_cell = max(1, round(cell * 0.12))
            painter.setBrush(QColor("#00D2FF") if index == len(self.snake) - 1 else QColor("#1689A3"))
            painter.drawRoundedRect(
                round(left + x * cell + inset_cell),
                round(top + y * cell + inset_cell),
                max(1, round(cell) - inset_cell * 2),
                max(1, round(cell) - inset_cell * 2),
                3,
                3,
            )

        if self.state != "running":
            if self.state != "paused":
                return
            painter.fillRect(board, QColor(15, 15, 18, 185))
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(board, Qt.AlignmentFlag.AlignCenter, "Paused")


class ArcadeView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("arcade_view")
        self.setStyleSheet("""
            QWidget#arcade_view {
                background-color: #0F0F12;
                color: #FFFFFF;
                font-family: "Segoe UI";
            }
            QLabel#arcade_eyebrow {
                color: #00D2FF;
                font-size: 11px;
                font-weight: 700;
            }
            QLabel#arcade_title {
                color: #FFFFFF;
                font-size: 28px;
                font-weight: 700;
            }
            QLabel#arcade_copy, QLabel#arcade_hint {
                color: #B7B7C7;
                font-size: 13px;
            }
            QFrame#game_picker, QFrame#game_surface {
                background-color: #1A1A24;
                border: 1px solid #2E2E3E;
                border-radius: 8px;
            }
            QLabel#panel_label {
                color: #B7B7C7;
                font-size: 11px;
                font-weight: 650;
            }
            QLabel#score_value {
                color: #FFFFFF;
                font-size: 22px;
                font-weight: 700;
            }
            QPushButton#game_choice, QPushButton#icon_button {
                background-color: #1A1A24;
                border: 1px solid #454554;
                border-radius: 6px;
                color: #FFFFFF;
                min-height: 44px;
                padding: 0 12px;
                text-align: left;
            }
            QPushButton#icon_button {
                font-size: 21px;
                min-width: 44px;
                max-width: 44px;
                min-height: 44px;
                max-height: 44px;
                padding: 0;
                text-align: center;
            }
            QPushButton#game_choice:checked {
                border-left: 4px solid #00D2FF;
                background-color: #202027;
            }
            QPushButton#icon_button:hover:enabled, QPushButton#game_choice:hover {
                border-color: #00D2FF;
            }
            QPushButton#icon_button:focus, QPushButton#game_choice:focus {
                border: 2px solid #FFFFFF;
            }
            QPushButton#icon_button:disabled {
                color: #A8A8BA;
                border-color: #343440;
            }
            QPushButton#start_button {
                background-color: #00D2FF;
                border: 1px solid #00D2FF;
                border-radius: 6px;
                color: #0F0F12;
                font-weight: 700;
                min-height: 42px;
                padding: 0 14px;
            }
            QPushButton#start_button:hover {
                background-color: #55DFFF;
            }
            QPushButton#start_button:focus {
                border: 2px solid #FFFFFF;
            }
            QLabel#overlay_title {
                color: #FFFFFF;
                font-size: 18px;
                font-weight: 650;
                background-color: transparent;
            }
            QWidget#game_overlay {
                background-color: rgba(15, 15, 18, 190);
            }
            QLabel#source_link {
                color: #B7B7C7;
                font-size: 11px;
            }
            QLabel#source_link a {
                color: #B7B7C7;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(8)

        eyebrow = QLabel("PRISM  /  ARCADE")
        eyebrow.setObjectName("arcade_eyebrow")
        root.addWidget(eyebrow)

        title = QLabel("Arcade")
        title.setObjectName("arcade_title")
        root.addWidget(title)

        description = QLabel("Pick a game and play without leaving Prism.")
        description.setObjectName("arcade_copy")
        root.addWidget(description)
        content = QHBoxLayout()
        content.setSpacing(12)
        root.addLayout(content, stretch=1)

        picker = QFrame()
        picker.setObjectName("game_picker")
        picker.setMinimumWidth(140)
        picker.setMaximumWidth(165)
        picker_layout = QVBoxLayout(picker)
        picker_layout.setContentsMargins(14, 16, 14, 16)
        picker_layout.setSpacing(10)

        available_label = QLabel("AVAILABLE GAME")
        available_label.setObjectName("panel_label")
        picker_layout.addWidget(available_label)

        self.snake_choice = QPushButton("Snake")
        self.snake_choice.setObjectName("game_choice")
        self.snake_choice.setCheckable(True)
        self.snake_choice.setChecked(True)
        self.snake_choice.setAccessibleName("Select Snake")
        self.snake_choice.clicked.connect(self._select_snake)
        picker_layout.addWidget(self.snake_choice)

        picker_hint = QLabel("Guide the snake to each food piece. Avoid the walls and its own trail.")
        picker_hint.setObjectName("arcade_hint")
        picker_hint.setWordWrap(True)
        picker_layout.addWidget(picker_hint)

        controls_label = QLabel("CONTROLS")
        controls_label.setObjectName("panel_label")
        picker_layout.addSpacing(12)
        picker_layout.addWidget(controls_label)

        controls_hint = QLabel("Arrow keys or W A S D to steer.\nSpace or Escape to pause.")
        controls_hint.setObjectName("arcade_hint")
        controls_hint.setWordWrap(True)
        picker_layout.addWidget(controls_hint)

        picker_layout.addStretch(1)
        content.addWidget(picker)

        game_column = QVBoxLayout()
        game_column.setSpacing(10)
        content.addLayout(game_column, stretch=1)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(10)
        score_label = QLabel("SCORE")
        score_label.setObjectName("panel_label")
        toolbar.addWidget(score_label)
        self.score_value = QLabel("0")
        self.score_value.setObjectName("score_value")
        toolbar.addWidget(self.score_value)
        toolbar.addStretch(1)

        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("arcade_copy")
        self.status_label.setAccessibleName("Game status")
        toolbar.addWidget(self.status_label)

        self.pause_button = QPushButton("Ⅱ")
        self.pause_button.setObjectName("icon_button")
        self.pause_button.setAccessibleName("Pause Snake")
        self.pause_button.setToolTip("Pause")
        self.pause_button.clicked.connect(self.board_pause)
        toolbar.addWidget(self.pause_button)

        self.reset_button = QPushButton("↻")
        self.reset_button.setObjectName("icon_button")
        self.reset_button.setAccessibleName("Restart Snake")
        self.reset_button.setToolTip("Restart")
        self.reset_button.clicked.connect(self.board_reset)
        toolbar.addWidget(self.reset_button)
        game_column.addLayout(toolbar)

        surface = QFrame()
        surface.setObjectName("game_surface")
        surface_layout = QVBoxLayout(surface)
        surface_layout.setContentsMargins(8, 8, 8, 8)
        board_stack = QStackedLayout()
        board_stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self.board = SnakeBoard()
        self.board.score_changed.connect(lambda score: self.score_value.setText(str(score)))
        self.board.state_changed.connect(self._update_game_state)
        board_stack.addWidget(self.board)

        self.game_overlay = QWidget()
        self.game_overlay.setObjectName("game_overlay")
        self.game_overlay.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        overlay_layout = QVBoxLayout(self.game_overlay)
        overlay_layout.addStretch(1)
        self.overlay_title = QLabel("Ready to play")
        self.overlay_title.setObjectName("overlay_title")
        self.overlay_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        overlay_layout.addWidget(self.overlay_title)
        overlay_layout.addSpacing(10)
        self.start_button = QPushButton("Play Snake")
        self.start_button.setObjectName("start_button")
        self.start_button.setAccessibleName("Start Snake game")
        self.start_button.setDefault(True)
        self.start_button.setMinimumWidth(150)
        self.start_button.clicked.connect(self.board.start_game)
        overlay_layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        overlay_layout.addStretch(1)
        board_stack.addWidget(self.game_overlay)
        surface_layout.addLayout(board_stack)
        game_column.addWidget(surface, stretch=1)
        self._update_game_state("ready")

        attribution = QLabel(
            'Snake gameplay adapted from '
            '<a href="https://github.com/hhhrrrttt222111/PyBox">PyBox</a> (MIT).'
        )
        attribution.setObjectName("source_link")
        attribution.setOpenExternalLinks(True)
        root.addWidget(attribution)

    def _select_snake(self):
        self.board_reset()
        self.board.setFocus(Qt.FocusReason.OtherFocusReason)

    def board_pause(self):
        self.board.toggle_pause()

    def board_reset(self):
        self.board.reset_game()

    def _update_game_state(self, state: str):
        if state == "ready":
            self.status_label.setText("Ready")
            self.overlay_title.setText("Ready to play")
            self.start_button.setText("Play Snake")
            self.start_button.setAccessibleName("Start Snake game")
            self.pause_button.setText("Ⅱ")
            self.pause_button.setAccessibleName("Pause Snake")
            self.pause_button.setToolTip("Pause")
            self.pause_button.setEnabled(False)
            self.game_overlay.show()
        elif state == "running":
            self.status_label.setText("Playing")
            self.pause_button.setText("Ⅱ")
            self.pause_button.setAccessibleName("Pause Snake")
            self.pause_button.setToolTip("Pause")
            self.pause_button.setEnabled(True)
            self.game_overlay.hide()
        elif state == "paused":
            self.status_label.setText("Paused")
            self.pause_button.setText("▶")
            self.pause_button.setAccessibleName("Resume Snake")
            self.pause_button.setToolTip("Resume")
            self.pause_button.setEnabled(True)
            self.game_overlay.hide()
        elif state == "over":
            self.status_label.setText("Game over")
            self.overlay_title.setText("Round over")
            self.start_button.setText("Play again")
            self.start_button.setAccessibleName("Play Snake again")
            self.pause_button.setText("Ⅱ")
            self.pause_button.setAccessibleName("Pause Snake")
            self.pause_button.setToolTip("Pause")
            self.pause_button.setEnabled(False)
            self.game_overlay.show()
        else:
            self.status_label.setText("Board cleared")
            self.overlay_title.setText("Board cleared")
            self.start_button.setText("Play again")
            self.start_button.setAccessibleName("Play Snake again")
            self.pause_button.setText("Ⅱ")
            self.pause_button.setAccessibleName("Pause Snake")
            self.pause_button.setToolTip("Pause")
            self.pause_button.setEnabled(False)
            self.game_overlay.show()

    def pause_game(self):
        self.board.pause_game()
