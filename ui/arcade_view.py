"""Embedded Arcade games adapted from PyBox under the MIT License."""

import random

from PyQt6.QtCore import QRectF, QSize, QTimer, Qt, pyqtSignal
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


class TetrisBoard(QWidget):
    score_changed = pyqtSignal(int)
    state_changed = pyqtSignal(str)

    GRID_WIDTH = 10
    GRID_HEIGHT = 20
    STEP_MS = 420
    SHAPES = {
        "I": [[1, 1, 1, 1]],
        "O": [[1, 1], [1, 1]],
        "T": [[0, 1, 0], [1, 1, 1]],
        "S": [[0, 1, 1], [1, 1, 0]],
        "Z": [[1, 1, 0], [0, 1, 1]],
        "J": [[1, 0, 0], [1, 1, 1]],
        "L": [[0, 0, 1], [1, 1, 1]],
    }
    COLORS = {
        "I": QColor("#58D4FF"),
        "O": QColor("#F9D14A"),
        "T": QColor("#B57DFF"),
        "S": QColor("#63E0A1"),
        "Z": QColor("#FF6B6B"),
        "J": QColor("#5BA7FF"),
        "L": QColor("#FFB367"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("tetris_board")
        self.setAccessibleName("Tetris game board")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(220, 380)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.timer = QTimer(self)
        self.timer.setInterval(self.STEP_MS)
        self.timer.timeout.connect(self._advance)
        self.reset_game()

    def sizeHint(self) -> QSize:
        return QSize(300, 520)

    def minimumSizeHint(self) -> QSize:
        return QSize(220, 380)

    def reset_game(self):
        self.board = [[0 for _ in range(self.GRID_WIDTH)] for _ in range(self.GRID_HEIGHT)]
        self.score = 0
        self.state = "ready"
        self.current_shape = ""
        self.current_matrix = []
        self.current_x = 0
        self.current_y = 0
        self._spawn_piece()
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

    def _spawn_piece(self):
        self.current_shape, matrix = random.choice(list(self.SHAPES.items()))
        self.current_matrix = [list(row) for row in matrix]
        self.current_x = (self.GRID_WIDTH - len(self.current_matrix[0])) // 2
        self.current_y = 0
        if not self._can_place(self.current_matrix, self.current_x, self.current_y):
            self.timer.stop()
            self.state = "over"
            self.state_changed.emit(self.state)
            self.update()

    def _can_place(self, matrix, x, y):
        for row_index, row in enumerate(matrix):
            for col_index, cell in enumerate(row):
                if not cell:
                    continue
                board_x = x + col_index
                board_y = y + row_index
                if board_x < 0 or board_x >= self.GRID_WIDTH or board_y >= self.GRID_HEIGHT:
                    return False
                if board_y >= 0 and self.board[board_y][board_x] != 0:
                    return False
        return True

    def _move(self, dx, dy):
        if self.state != "running":
            return False
        new_x = self.current_x + dx
        new_y = self.current_y + dy
        if self._can_place(self.current_matrix, new_x, new_y):
            self.current_x = new_x
            self.current_y = new_y
            self.update()
            return True
        if dy > 0:
            self._lock_piece()
        return False

    def _lock_piece(self):
        for row_index, row in enumerate(self.current_matrix):
            for col_index, cell in enumerate(row):
                if not cell:
                    continue
                board_x = self.current_x + col_index
                board_y = self.current_y + row_index
                if board_y < 0:
                    self.timer.stop()
                    self.state = "over"
                    self.state_changed.emit(self.state)
                    self.update()
                    return
                self.board[board_y][board_x] = self.current_shape

        self._clear_lines()
        self._spawn_piece()
        self.update()

    def _clear_lines(self):
        rows_cleared = 0
        for row_index in range(self.GRID_HEIGHT - 1, -1, -1):
            if all(self.board[row_index]):
                del self.board[row_index]
                self.board.insert(0, [0 for _ in range(self.GRID_WIDTH)])
                rows_cleared += 1

        if rows_cleared:
            score_values = {1: 100, 2: 300, 3: 500, 4: 800}
            self.score += score_values.get(rows_cleared, 0)
            self.score_changed.emit(self.score)

    def _rotate(self):
        if self.state != "running":
            return
        rotated = [list(row) for row in zip(*self.current_matrix[::-1])]
        for offset in (0, -1, 1, -2, 2):
            if self._can_place(rotated, self.current_x + offset, self.current_y):
                self.current_matrix = rotated
                self.current_x += offset
                self.update()
                return

    def _advance(self):
        if self.state != "running":
            return
        if not self._move(0, 1):
            return

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Space, Qt.Key.Key_Escape):
            self.toggle_pause()
            event.accept()
            return

        if key in (Qt.Key.Key_Left, Qt.Key.Key_A):
            self._move(-1, 0)
            event.accept()
            return
        if key in (Qt.Key.Key_Right, Qt.Key.Key_D):
            self._move(1, 0)
            event.accept()
            return
        if key in (Qt.Key.Key_Down, Qt.Key.Key_S):
            self._move(0, 1)
            event.accept()
            return
        if key in (Qt.Key.Key_Up, Qt.Key.Key_W):
            self._rotate()
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#101015"))

        padding = 16
        cell = min(
            max(0, self.width() - padding) / self.GRID_WIDTH,
            max(0, self.height() - padding) / self.GRID_HEIGHT,
        )
        board_width = cell * self.GRID_WIDTH
        cell = board_width / self.GRID_WIDTH
        board_height = cell * self.GRID_HEIGHT
        left = (self.width() - board_width) / 2
        top = (self.height() - board_height) / 2

        painter.setPen(QPen(QColor("#00D2FF") if self.hasFocus() else QColor("#343440"), 2 if self.hasFocus() else 1))
        painter.setBrush(QColor("#141419"))
        painter.drawRoundedRect(
            QRectF(left, top, board_width, board_height),
            8,
            8,
        )

        for row in range(self.GRID_HEIGHT):
            for col in range(self.GRID_WIDTH):
                cell_x = left + col * cell
                cell_y = top + row * cell
                if self.board[row][col] != 0:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(self.COLORS[self.board[row][col]])
                    painter.drawRoundedRect(
                        QRectF(cell_x + 2, cell_y + 2, cell - 4, cell - 4),
                        3,
                        3,
                    )

        if self.current_shape:
            painter.setPen(Qt.PenStyle.NoPen)
            for row_index, row in enumerate(self.current_matrix):
                for col_index, value in enumerate(row):
                    if not value:
                        continue
                    board_x = self.current_x + col_index
                    board_y = self.current_y + row_index
                    if board_y < 0:
                        continue
                    block_x = left + board_x * cell
                    block_y = top + board_y * cell
                    painter.setBrush(self.COLORS[self.current_shape])
                    painter.drawRoundedRect(
                        QRectF(block_x + 2, block_y + 2, cell - 4, cell - 4),
                        3,
                        3,
                    )

        painter.setPen(QPen(QColor("#24242D"), 1))
        for line in range(1, self.GRID_WIDTH):
            x = round(left + line * cell)
            painter.drawLine(x, round(top), x, round(top + board_height))
        for line in range(1, self.GRID_HEIGHT):
            y = round(top + line * cell)
            painter.drawLine(round(left), y, round(left + board_width), y)

        if self.state not in ("running", "paused"):
            return
        if self.state == "paused":
            painter.fillRect(
                QRectF(left, top, board_width, board_height),
                QColor(15, 15, 18, 185),
            )
            painter.setPen(QColor("#FFFFFF"))
            painter.drawText(
                QRectF(left, top, board_width, board_height),
                Qt.AlignmentFlag.AlignCenter,
                "Paused",
            )


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

        available_label = QLabel("AVAILABLE GAMES")
        available_label.setObjectName("panel_label")
        picker_layout.addWidget(available_label)

        self.snake_choice = QPushButton("Snake")
        self.snake_choice.setObjectName("game_choice")
        self.snake_choice.setCheckable(True)
        self.snake_choice.setChecked(True)
        self.snake_choice.setAccessibleName("Select Snake")
        self.snake_choice.clicked.connect(self._select_snake)
        picker_layout.addWidget(self.snake_choice)

        self.tetris_choice = QPushButton("Tetris")
        self.tetris_choice.setObjectName("game_choice")
        self.tetris_choice.setCheckable(True)
        self.tetris_choice.setAccessibleName("Select Tetris")
        self.tetris_choice.clicked.connect(self._select_tetris)
        picker_layout.addWidget(self.tetris_choice)

        self.picker_hint = QLabel("Guide the snake to each food piece. Avoid the walls and its own trail.")
        self.picker_hint.setObjectName("arcade_hint")
        self.picker_hint.setWordWrap(True)
        picker_layout.addWidget(self.picker_hint)

        controls_label = QLabel("CONTROLS")
        controls_label.setObjectName("panel_label")
        picker_layout.addSpacing(12)
        picker_layout.addWidget(controls_label)

        self.controls_hint = QLabel("Arrow keys or W A S D to steer.\nSpace or Escape to pause.")
        self.controls_hint.setObjectName("arcade_hint")
        self.controls_hint.setWordWrap(True)
        picker_layout.addWidget(self.controls_hint)

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

        self.board_stack = QStackedLayout()
        self.board_stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self.game_surface = QWidget()
        self.game_stack = QStackedLayout(self.game_surface)
        self.game_stack.setStackingMode(QStackedLayout.StackingMode.StackOne)

        self.snake_board = SnakeBoard()
        self.tetris_board = TetrisBoard()
        self.snake_board.score_changed.connect(self._set_score_value)
        self.tetris_board.score_changed.connect(self._set_score_value)
        self.snake_board.state_changed.connect(self._update_game_state)
        self.tetris_board.state_changed.connect(self._update_game_state)

        self.game_stack.addWidget(self.snake_board)
        self.game_stack.addWidget(self.tetris_board)
        self.board_stack.addWidget(self.game_surface)
        self.board = self.snake_board
        self.current_game = "snake"

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
        self.start_button.clicked.connect(self._start_selected_game)
        overlay_layout.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        overlay_layout.addStretch(1)
        self.board_stack.addWidget(self.game_overlay)
        surface_layout.addLayout(self.board_stack)
        game_column.addWidget(surface, stretch=1)
        self._update_controls_hint()
        self._set_active_game("snake")

        attribution = QLabel(
            'Snake gameplay adapted from '
            '<a href="https://github.com/hhhrrrttt222111/PyBox">PyBox</a> (MIT). '
            'Tetris is a built-in Prism arcade game.'
        )
        attribution.setObjectName("source_link")
        attribution.setOpenExternalLinks(True)
        root.addWidget(attribution)

    def _set_score_value(self, score: int):
        self.score_value.setText(str(score))

    def _start_selected_game(self):
        self.board.start_game()
        self.board.setFocus(Qt.FocusReason.OtherFocusReason)

    def _set_active_game(self, game_name: str):
        if game_name != self.current_game and self.board is not None:
            self.board.pause_game()

        if game_name == "snake":
            self.current_game = "snake"
            self.board = self.snake_board
            self.snake_choice.setChecked(True)
            self.tetris_choice.setChecked(False)
            self.picker_hint.setText("Guide the snake to each food piece. Avoid the walls and its own trail.")
            self.controls_hint.setText("Arrow keys or W A S D to steer.\nSpace or Escape to pause.")
        else:
            self.current_game = "tetris"
            self.board = self.tetris_board
            self.snake_choice.setChecked(False)
            self.tetris_choice.setChecked(True)
            self.picker_hint.setText("Stack falling blocks and clear lines before the board fills up.")
            self.controls_hint.setText("Arrow keys or W A S D to move.\nUp/W rotates, Down/S drops, Space pauses.")

        if self.board is not None:
            self.game_stack.setCurrentWidget(self.board)
            self.score_value.setText(str(self.board.score))
            self._update_game_state(self.board.state)

    def _select_snake(self):
        self._set_active_game("snake")
        self.board_reset()
        self.board.setFocus(Qt.FocusReason.OtherFocusReason)

    def _select_tetris(self):
        self._set_active_game("tetris")
        self.board_reset()
        self.board.setFocus(Qt.FocusReason.OtherFocusReason)

    def _update_controls_hint(self):
        if self.current_game == "snake":
            self.controls_hint.setText("Arrow keys or W A S D to steer.\nSpace or Escape to pause.")
        else:
            self.controls_hint.setText("Arrow keys or W A S D to move.\nUp/W rotates, Down/S drops, Space pauses.")

    def board_pause(self):
        self.board.toggle_pause()

    def board_reset(self):
        self.board.reset_game()

    def _update_game_state(self, state: str):
        if self.board is None:
            return
        board_name = "Snake" if self.current_game == "snake" else "Tetris"
        if state == "ready":
            self.status_label.setText("Ready")
            self.overlay_title.setText("Ready to play")
            self.start_button.setText(f"Play {board_name}")
            self.start_button.setAccessibleName(f"Start {board_name} game")
            self.pause_button.setText("Ⅱ")
            self.pause_button.setAccessibleName(f"Pause {board_name}")
            self.pause_button.setToolTip("Pause")
            self.pause_button.setEnabled(False)
            self.board_stack.setCurrentWidget(self.game_overlay)
            self.game_overlay.show()
        elif state == "running":
            self.status_label.setText("Playing")
            self.pause_button.setText("Ⅱ")
            self.pause_button.setAccessibleName(f"Pause {board_name}")
            self.pause_button.setToolTip("Pause")
            self.pause_button.setEnabled(True)
            self.board_stack.setCurrentWidget(self.game_surface)
            self.game_overlay.hide()
        elif state == "paused":
            self.status_label.setText("Paused")
            self.pause_button.setText("▶")
            self.pause_button.setAccessibleName(f"Resume {board_name}")
            self.pause_button.setToolTip("Resume")
            self.pause_button.setEnabled(True)
            self.board_stack.setCurrentWidget(self.game_surface)
            self.game_overlay.hide()
        elif state == "over":
            self.status_label.setText("Game over")
            self.overlay_title.setText(f"{board_name} over")
            self.start_button.setText("Play again")
            self.start_button.setAccessibleName(f"Play {board_name} again")
            self.pause_button.setText("Ⅱ")
            self.pause_button.setAccessibleName(f"Pause {board_name}")
            self.pause_button.setToolTip("Pause")
            self.pause_button.setEnabled(False)
            self.board_stack.setCurrentWidget(self.game_overlay)
            self.game_overlay.show()
        else:
            self.status_label.setText("Board cleared")
            self.overlay_title.setText("Board cleared")
            self.start_button.setText("Play again")
            self.start_button.setAccessibleName(f"Play {board_name} again")
            self.pause_button.setText("Ⅱ")
            self.pause_button.setAccessibleName(f"Pause {board_name}")
            self.pause_button.setToolTip("Pause")
            self.pause_button.setEnabled(False)
            self.board_stack.setCurrentWidget(self.game_overlay)
            self.game_overlay.show()

    def pause_game(self):
        self.board.pause_game()
