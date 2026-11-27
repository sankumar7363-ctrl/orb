"""Qt presentation for the ORB assistant dashboard."""

import sqlite3

from PySide6.QtCore import QDateTime, QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (
    QColor, QConicalGradient, QFont, QIcon, QLinearGradient, QPainter,
    QPalette, QPen, QPixmap, QRadialGradient, QTextCursor,
)
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMenu, QProgressBar, QPushButton, QFileDialog, QInputDialog,
    QStackedWidget, QTextEdit, QVBoxLayout, QWidget,
)
from orb.storage.memory import MemoryStore

CENTER = Qt.AlignmentFlag.AlignCenter

STYLE = """
* { font-family: "Segoe UI"; font-size: 14px; }
QLabel { color: #f5f7ff; }
QLabel#Muted { color: #b0bbd0; }
QLabel#Heading { font-size: 18px; font-weight: 600; }
QLabel#Brand { font-size: 24px; font-weight: 700; }
QLabel#Greeting { font-size: 36px; font-weight: 600; }
QLabel#Subtitle { font-size: 20px; color: #adb9cf; }
QFrame#Rail { background: rgba(200, 212, 255, 31); }
QFrame#Card, QTextEdit {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 rgba(209,222,255,42),stop:0.52 rgba(170,188,238,28),
                stop:1 rgba(220,232,255,47));
    border: 1px solid rgba(201, 219, 255, 65); border-radius: 20px;
}
QFrame#Composer {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 rgba(212,224,255,65), stop:0.46 rgba(190,205,244,39),
                stop:1 rgba(194,218,255,58));
    border: 1px solid rgba(213,225,255,105); border-radius: 34px;
}
QFrame#Composer[focused="true"] { border-color: #9bb8ff; }
QLineEdit, QTextEdit { color: #f4f7ff; selection-background-color: #416de4; }
QListWidget { color: #f4f7ff; background: #253650; border: 1px solid #62769a; }
QLineEdit { background: rgba(198,218,255,24); border: 1px solid #62769a;
            border-radius: 14px; padding: 12px; }
QLineEdit#HomeInput { background: transparent; border: 0; font-size: 16px; padding: 0; }
QTextEdit { padding: 12px; }
QPushButton { background: rgba(193,211,255,26); color: #eff3ff;
              border: 1px solid rgba(200,217,255,56); border-radius: 17px;
              padding: 8px 13px; min-height: 17px; }
QPushButton::menu-indicator { subcontrol-position: right center; right: 8px; }
QPushButton:hover, QPushButton:focus { background: rgba(175,200,255,63); border-color: #8aa9ff; }
QPushButton:disabled { color: #9caac5; }
QPushButton#Nav { text-align: left; border: 1px solid transparent;
                  background: transparent; padding: 8px 12px; color: #c1cce0; }
QPushButton#Nav:hover { background: rgba(197,216,255,29); color: white; }
QPushButton#Nav:checked { background: rgba(185,207,255,64);
                         border-color: rgba(196,217,255,99); color: white; }
QPushButton#Link { background: transparent; border: 0; padding: 3px; color: #a1bcff; font-size: 13px; }
QPushButton#Link:hover, QPushButton#Link:focus { color: white; }
QPushButton#Mic { border-radius: 24px; padding: 0;
                  background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                              stop:0 #82baff,stop:0.53 #4d78f7,stop:1 #4358d8);
                  border: 1px solid #87aaff; }
QPushButton#Mic:hover, QPushButton#Mic:focus { background: #6e96fa; }
QPushButton#Mic:disabled { background: #526894; }
QProgressBar { background: rgba(160,183,234,49); border: none; border-radius: 3px; }
QProgressBar::chunk { background: #638bff; border-radius: 3px; }
QMenu { color: #eff3ff; background: #263954; border: 1px solid #657a9f; }
QMenu::item:selected { background: #465f91; }
"""


def label(text, name=None):
    widget = QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    if name:
        widget.setObjectName(name)
    return widget


def button(text, callback, name=None):
    widget = QPushButton(text)
    if name:
        widget.setObjectName(name)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.clicked.connect(callback)
    return widget


def glow(painter, x, y, width, height, color):
    painter.save()
    painter.translate(x, y)
    painter.scale(width, height)
    gradient = QRadialGradient(QPointF(0, 0), 1)
    gradient.setColorAt(0, color)
    edge = QColor(color)
    edge.setAlpha(0)
    gradient.setColorAt(1, edge)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    painter.drawEllipse(QRectF(-1, -1, 2, 2))
    painter.restore()


def icon(name, color="#c9d5ff"):
    pixmap = QPixmap(48, 48)
    pixmap.fill(Qt.GlobalColor.transparent)
    pixmap.setDevicePixelRatio(2)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color), 1.65, Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    if name == "Mic":
        painter.drawRoundedRect(QRectF(9, 3, 6, 12), 3, 3)
        painter.drawArc(QRectF(6, 6, 12, 12), 180 * 16, 180 * 16)
        painter.drawLine(QPointF(12, 18), QPointF(12, 22))
    elif name == "ORB":
        painter.setPen(QPen(QColor("#529dff"), 3))
        painter.drawEllipse(QRectF(3, 3, 18, 18))
        painter.setPen(QPen(QColor("#83d9ff"), 1.5))
        painter.drawArc(QRectF(4, 4, 16, 16), 60 * 16, 175 * 16)
    else:
        paths = {
            "Home": (((2, 11), (12, 3), (22, 11)), ((5, 9), (5, 21), (10, 21),
                      (10, 15), (14, 15), (14, 21), (19, 21), (19, 9))),
            "Tasks": (((4, 3), (20, 3), (20, 21), (4, 21), (4, 3)),
                      ((7, 12), (10, 15), (17, 8))),
            "Projects": (((3, 6), (9, 6), (11, 9), (21, 9), (21, 20),
                          (3, 20), (3, 6)),),
            "Workflows": (((3, 7), (17, 7), (17, 3), (21, 7), (17, 11)),
                          ((21, 17), (7, 17), (7, 13), (3, 17), (7, 21))),
            "Memory": (((4, 4), (20, 4), (20, 20), (4, 20), (4, 4)),
                       ((8, 9), (16, 9)), ((8, 14), (14, 14))),
            "Plugins": (((6, 6), (18, 6), (18, 12), (14, 17), (10, 17),
                         (6, 12), (6, 6)), ((9, 6), (9, 2)), ((15, 6), (15, 2)),
                        ((12, 17), (12, 22))),
            "Settings": (((3, 6), (21, 6)), ((3, 12), (21, 12)), ((3, 18), (21, 18)),
                         ((8, 4), (8, 8)), ((16, 10), (16, 14)), ((10, 16), (10, 20))),
            "Activity": (((4, 10), (4, 14)), ((8, 6), (8, 18)), ((12, 3), (12, 21)),
                         ((16, 7), (16, 17)), ((20, 10), (20, 14))),
            "Overview": (((3, 18), (9, 11), (13, 14), (21, 5)), ((15, 5), (21, 5), (21, 11))),
        }
        for path in paths[name]:
            painter.drawPolyline([QPointF(*point) for point in path])
    painter.end()
    return QIcon(pixmap)


class OrbArt(QWidget):
    """Draw the sphere and its orbit paths at the available resolution."""

    def __init__(self, mini=False):
        super().__init__()
        self.mini = mini
        if mini:
            self.setFixedSize(46, 46)
        else:
            self.setMinimumHeight(190)
            self.setMaximumHeight(340)
        self.setAccessibleName("ORB")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        scale = self.width() / 220 if self.mini else min(self.width() / 545, self.height() / 260)
        painter.scale(scale, scale)

        if not self.mini:
            glow(painter, 0, 9, 230, 119, QColor(49, 112, 248, 116))
            glow(painter, -56, -53, 107, 75, QColor(70, 204, 255, 155))
            self.draw_orbit(painter, -15, 252, 56, False)
            self.draw_orbit(painter, -8, 205, 44, False)

        sphere = QRectF(-104, -104, 208, 208)
        body = QRadialGradient(QPointF(-6, -3), 111, QPointF(-25, -27))
        for stop, color in (
            (0, "#152746"), (0.49, "#1b3765"), (0.72, "#274d93"),
            (0.87, "#4a76d0"), (0.96, "#80aafa"), (1, "#bcd8ff"),
        ):
            body.setColorAt(stop, QColor(color))
        painter.setBrush(body)
        painter.setPen(QPen(QColor("#c7e1ff"), 1.2))
        painter.drawEllipse(sphere)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        rim = QConicalGradient(0, 0, 0)
        for stop, color in (
            (0, QColor(213, 233, 255, 20)), (0.32, QColor(220, 248, 255, 230)),
            (0.53, QColor(186, 211, 255, 40)), (0.77, QColor(76, 130, 255, 70)),
            (0.9, QColor(203, 236, 255, 225)), (1, QColor(213, 233, 255, 20)),
        ):
            rim.setColorAt(stop, color)
        painter.setPen(QPen(rim, 5))
        painter.drawEllipse(sphere.adjusted(3, 3, -3, -3))

        shine = QLinearGradient(-62, -86, -21, -32)
        shine.setColorAt(0, QColor(238, 253, 255, 195))
        shine.setColorAt(1, QColor(182, 221, 255, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shine)
        painter.save()
        painter.rotate(-38)
        painter.drawEllipse(QRectF(-54, -97, 108, 29))
        painter.restore()

        if not self.mini:
            self.draw_orbit(painter, -15, 252, 56, True)
            self.draw_orbit(painter, -8, 205, 44, True)
            font = QFont("Segoe UI")
            font.setPixelSize(35)
            painter.setFont(font)
            painter.setPen(QColor("#f1f6ff"))
            painter.drawText(sphere, CENTER, "ORB")

    @staticmethod
    def draw_orbit(painter, angle, radius, depth, front):
        painter.save()
        painter.translate(0, 12)
        painter.rotate(angle)
        gradient = QLinearGradient(-radius, 0, radius, 0)
        gradient.setColorAt(0, QColor(124, 178, 255, 155))
        gradient.setColorAt(0.55, QColor(76, 129, 255, 80))
        gradient.setColorAt(1, QColor(115, 169, 255, 134))
        painter.setPen(QPen(gradient, 1.25))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(QRectF(-radius, -depth, radius * 2, depth * 2),
                        (180 if front else 0) * 16, 180 * 16)
        painter.restore()


class GoalRing(QWidget):
    def __init__(self):
        super().__init__()
        self.value = None
        self.setFixedSize(86, 86)

    def set_value(self, value):
        self.value = value
        self.setAccessibleName("Progress unavailable" if value is None else f"{value}% complete")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ring = QRectF(6, 6, 74, 74)
        painter.setPen(QPen(QColor(173, 200, 251, 56), 7))
        painter.drawEllipse(ring)
        if self.value:
            gradient = QLinearGradient(ring.bottomLeft(), ring.topRight())
            gradient.setColorAt(0, QColor("#44c5f8"))
            gradient.setColorAt(1, QColor("#42edc5"))
            painter.setPen(QPen(gradient, 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawArc(ring, 90 * 16, -round(self.value / 100 * 360 * 16))
        font = QFont("Segoe UI")
        font.setPixelSize(18)
        painter.setFont(font)
        painter.setPen(QColor("#f5f7ff"))
        painter.drawText(ring, CENTER, "—" if self.value is None else f"{self.value}%")


class DashboardView(QWidget):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.workflow_running = False
        self.setObjectName("Dashboard")
        self.setStyleSheet(STYLE)
        self.nav = {}
        self.pages = {}

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self.make_sidebar())

        workspace = QVBoxLayout()
        workspace.setContentsMargins(23, 14, 23, 24)
        workspace.setSpacing(18)
        root.addLayout(workspace, 1)
        workspace.addLayout(self.make_header())
        body = QHBoxLayout()
        body.setSpacing(23)
        workspace.addLayout(body, 1)
        self.stack = QStackedWidget()
        body.addWidget(self.stack, 5)

        self.add_page("Home", self.make_home())
        self.add_page("Assistant", self.make_assistant())
        self.tasks_text = self.add_module("Tasks", "No workflow steps yet.")
        self.projects_text = self.add_module("Projects", "No projects to display.")
        self.pages["Projects"].layout().addWidget(
            button("Choose project folder", self.select_project)
        )
        self.workflow_text = self.add_module("Workflows", "No saved workflow runs.")
        self.pages["Workflows"].layout().addWidget(
            button("Resume saved workflow", self.resume_saved_workflow)
        )
        self.add_page("Memory", self.make_memory_page())
        self.add_module("Plugins", "No plugin controls are available in this dashboard.")
        self.add_module("Settings", "Use Voice in the conversation to toggle spoken replies.")

        panels = self.make_panels()
        panels.setMinimumWidth(277)
        panels.setMaximumWidth(405)
        body.addWidget(panels, 3)
        self.show_page("Home")
        self.set_activity("Idle", "Ready for a request.")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bounds = QRectF(self.rect())
        base = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
        base.setColorAt(0, QColor("#333f59"))
        base.setColorAt(0.36, QColor("#19263e"))
        base.setColorAt(0.72, QColor("#202d46"))
        base.setColorAt(1, QColor("#354c73"))
        painter.fillRect(bounds, base)
        width, height = self.width(), self.height()
        for x, y, rx, ry, color in (
            (.04, .02, .42, .36, QColor(222, 225, 243, 103)),
            (.69, .00, .30, .34, QColor(112, 174, 245, 123)),
            (.54, .40, .28, .43, QColor(45, 116, 230, 68)),
            (.75, .67, .26, .22, QColor(79, 134, 230, 89)),
            (.98, .40, .26, .25, QColor(234, 217, 193, 53)),
            (.31, .95, .30, .26, QColor(226, 208, 177, 55)),
        ):
            glow(painter, width * x, height * y, width * rx, height * ry, color)

    def make_sidebar(self):
        rail = QFrame()
        rail.setObjectName("Rail")
        rail.setFixedWidth(184)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(13, 25, 13, 15)
        layout.setSpacing(7)
        brand = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(icon("ORB").pixmap(QSize(39, 39)))
        brand.addWidget(mark)
        brand.addWidget(label("ORB", "Brand"))
        brand.addStretch()
        layout.addLayout(brand)
        layout.addSpacing(24)
        for name in ("Home", "Tasks", "Projects", "Workflows", "Memory", "Plugins", "Settings"):
            item = button(name, lambda checked=False, page=name: self.show_page(page), "Nav")
            item.setIcon(icon(name))
            item.setIconSize(QSize(21, 21))
            item.setMinimumHeight(42)
            item.setCheckable(True)
            layout.addWidget(item)
            self.nav[name] = item

        layout.addStretch()
        system = QFrame()
        system.setObjectName("Card")
        status = QVBoxLayout(system)
        status.setContentsMargins(12, 10, 10, 10)
        online = self.window.kernel.is_running()
        state = label("●  System online" if online else "●  System offline")
        state.setStyleSheet("color: #8bf2b0;" if online else "color: #f1bf90;")
        status.addWidget(state)
        status.addWidget(label("Local ORB runtime", "Muted"))
        layout.addWidget(system)
        layout.addSpacing(7)

        profile = QHBoxLayout()
        avatar = label("SK")
        avatar.setAlignment(CENTER)
        avatar.setFixedSize(33, 33)
        avatar.setStyleSheet("background: #566e9c; border-radius: 16px;")
        profile.addWidget(avatar)
        profile.addWidget(label("Santosh Kumar"), 1)
        layout.addLayout(profile)
        return rail

    def make_header(self):
        row = QHBoxLayout()
        clock = label("", "Muted")

        def update_clock():
            clock.setText(QDateTime.currentDateTime().toString("dddd, MMM d, yyyy  •  h:mm AP"))

        update_clock()
        timer = QTimer(clock)
        timer.timeout.connect(update_clock)
        timer.start(15000)
        row.addWidget(clock)
        row.addStretch()
        mic = button("", self.window.start_voice_input)
        mic.setIcon(icon("Mic"))
        mic.setFixedSize(38, 38)
        mic.setAccessibleName("Listen")
        mic.setToolTip("Listen")
        self.header_mic = mic
        row.addWidget(mic)
        row.addWidget(button("Conversation", lambda: self.show_page("Assistant")))
        return row

    def make_home(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(6)
        layout.addStretch(1)
        layout.addWidget(OrbArt(), 7)
        greeting = label("Hello, Santosh!", "Greeting")
        greeting.setAlignment(CENTER)
        layout.addWidget(greeting)
        subtitle = label("What would you like to accomplish today?", "Subtitle")
        subtitle.setAlignment(CENTER)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)
        layout.addSpacing(24)

        composer = QFrame()
        composer.setObjectName("Composer")
        composer.setMinimumHeight(68)
        row = QHBoxLayout(composer)
        row.setContentsMargins(20, 8, 9, 8)
        row.addWidget(label("✦", "Heading"))
        self.home_input = QLineEdit()
        self.home_input.setObjectName("HomeInput")
        self.home_input.setAccessibleName("Ask ORB")
        self.home_input.setPlaceholderText("Plan a project or ask ORB anything…")
        palette = self.home_input.palette()
        palette.setColor(QPalette.ColorRole.PlaceholderText, QColor("#bcc7dc"))
        self.home_input.setPalette(palette)
        self.home_input.returnPressed.connect(self.submit_home)
        row.addWidget(self.home_input, 1)
        send = button("Send", self.submit_home, "Link")
        send.hide()
        self.home_input.textChanged.connect(lambda text: send.setVisible(bool(text.strip())))
        row.addWidget(send)
        self.home_mic = button("", self.window.start_voice_input, "Mic")
        self.home_mic.setIcon(icon("Mic", "#ffffff"))
        self.home_mic.setIconSize(QSize(25, 25))
        self.home_mic.setFixedSize(48, 48)
        self.home_mic.setAccessibleName("Listen")
        self.home_mic.setToolTip("Listen")
        row.addWidget(self.home_mic)
        self.composer = composer
        QApplication.instance().focusChanged.connect(self.update_composer_focus)
        layout.addWidget(composer)
        layout.addSpacing(16)

        shortcuts = QHBoxLayout()
        shortcuts.setSpacing(9)
        shortcuts.addStretch()
        shortcuts.addWidget(button("ϟ  Plan a goal", lambda: self.set_home_prompt("Help me plan a goal.")))
        shortcuts.addWidget(button("✓  Show my tasks", lambda: self.show_page("Tasks")))
        shortcuts.addWidget(button("Ask ORB", lambda: self.home_input.setFocus()))
        more = QPushButton("More    ")
        more.setCursor(Qt.CursorShape.PointingHandCursor)
        menu = QMenu(more)
        menu.addAction("Open conversation", lambda: self.show_page("Assistant"))
        menu.addAction("Build a feature", lambda: self.set_home_prompt("Build a feature for "))
        menu.addAction("View workflows", lambda: self.show_page("Workflows"))
        more.setMenu(menu)
        shortcuts.addWidget(more)
        shortcuts.addStretch()
        layout.addLayout(shortcuts)
        layout.addStretch(2)
        return page

    def update_composer_focus(self, _previous, current):
        focused = current is not None and self.composer.isAncestorOf(current)
        if self.composer.property("focused") != focused:
            self.composer.setProperty("focused", focused)
            self.composer.style().unpolish(self.composer)
            self.composer.style().polish(self.composer)

    def make_assistant(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(label("ORB Assistant", "Heading"))
        layout.addWidget(button("Stop workflow", self.cancel_workflow))
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.append_chat("Ask a question or describe a goal to begin.")
        layout.addWidget(self.chat_display, 1)
        composer = QHBoxLayout()
        self.msg_input = QLineEdit()
        self.msg_input.setAccessibleName("Message ORB")
        self.msg_input.setPlaceholderText("Ask ORB anything…")
        self.msg_input.returnPressed.connect(self.window.send_message)
        composer.addWidget(self.msg_input, 1)
        self.mic_button = button("Listen", self.window.start_voice_input)
        self.mic_button.setIcon(icon("Mic"))
        composer.addWidget(self.mic_button)
        composer.addWidget(button("Send", self.window.send_message))
        self.voice_output_button = button("Voice: ON", self.window.toggle_voice_output)
        composer.addWidget(self.voice_output_button)
        layout.addLayout(composer)
        return page

    def make_panels(self):
        panels = QWidget()
        layout = QVBoxLayout(panels)
        layout.setContentsMargins(0, 37, 0, 12)
        layout.setSpacing(17)

        overview = self.add_card(layout, "Overview", "Your Overview", "Workflows", 5)
        goal_row = QHBoxLayout()
        goal_row.setSpacing(15)
        self.goal_ring = GoalRing()
        self.goal_ring.set_value(None)
        goal_row.addWidget(self.goal_ring)
        goal_details = QVBoxLayout()
        goal_details.setSpacing(4)
        goal_details.addWidget(label("Current goal", "Muted"))
        self.goal_title = label("No goal running")
        self.goal_title.setWordWrap(True)
        goal_details.addWidget(self.goal_title)
        self.goal_status = label("Waiting for a workflow", "Muted")
        goal_details.addWidget(self.goal_status)
        goal_row.addLayout(goal_details, 1)
        overview.addStretch()
        overview.addLayout(goal_row)
        overview.addStretch()

        tasks = self.add_card(layout, "Tasks", "Tasks", "Tasks", 5)
        self.task_preview = label("○  No workflow steps yet.", "Muted")
        self.task_preview.setWordWrap(True)
        tasks.addWidget(self.task_preview, 1)

        activity = self.add_card(layout, "Activity", "AI Activity", "Assistant", 3)
        row = QHBoxLayout()
        row.addWidget(OrbArt(mini=True))
        details = QVBoxLayout()
        self.activity_state = label("")
        self.activity_detail = label("", "Muted")
        self.activity_detail.setWordWrap(True)
        details.addWidget(self.activity_state)
        details.addWidget(self.activity_detail)
        self.activity_bar = QProgressBar()
        self.activity_bar.setTextVisible(False)
        self.activity_bar.setFixedHeight(6)
        details.addWidget(self.activity_bar)
        row.addLayout(details, 1)
        activity.addLayout(row)
        return panels

    def add_card(self, layout, symbol, title, page, stretch):
        card = QFrame()
        card.setObjectName("Card")
        details = QVBoxLayout(card)
        details.setContentsMargins(16, 14, 16, 14)
        details.setSpacing(9)
        header = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(icon(symbol).pixmap(QSize(22, 22)))
        header.addWidget(mark)
        header.addWidget(label(title, "Heading"), 1)
        link = button("View all →" if page != "Assistant" else "Open →",
                      lambda: self.show_page(page), "Link")
        link.setAccessibleName(f"Open {page}")
        header.addWidget(link)
        details.addLayout(header)
        layout.addWidget(card, stretch)
        return details

    def add_page(self, name, page):
        self.pages[name] = page
        self.stack.addWidget(page)

    def add_module(self, name, text):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(label(name, "Heading"))
        detail = QTextEdit()
        detail.setReadOnly(True)
        detail.setPlainText(text)
        layout.addWidget(detail, 1)
        self.add_page(name, page)
        return detail

    def show_page(self, name):
        for key, item in self.nav.items():
            item.setChecked(key == name)
        self.stack.setCurrentWidget(self.pages[name])
        if name == "Memory":
            self.refresh_memory()
        elif name == "Workflows":
            self.refresh_workflows()

    def cancel_workflow(self):
        self.window.kernel.workflow_service.cancel()
        self.set_activity("Stopping", "Current action may finish. Remaining steps will stop.")

    def resume_saved_workflow(self):
        runs = [
            run for run in self.window.kernel.workflow_service.checkpoints()
            if run["plan"] and run["status"] != "completed"
        ]
        if not runs:
            self.workflow_text.setPlainText("No unfinished saved workflows.")
            return
        choices = [
            f"{index + 1}. {run['goal']} · {run['status']}"
            for index, run in enumerate(runs)
        ]
        choice, accepted = QInputDialog.getItem(
            self, "Resume workflow", "Select a saved workflow", choices, editable=False
        )
        if accepted:
            run = runs[choices.index(choice)]
            self.window.resume_workflow(run["run_id"], run["goal"])

    def select_project(self):
        directory = QFileDialog.getExistingDirectory(self, "Choose project folder")
        if not directory:
            return
        try:
            context = self.window.kernel.workflow_service.project_context
            context.select(directory)
            snapshot = context.snapshot()
        except (ValueError, OSError) as error:
            self.projects_text.setPlainText(str(error))
            return
        self.projects_text.setPlainText(
            snapshot["directory"] + "\n\n" + "\n".join(snapshot["entries"])
        )

    def refresh_workflows(self):
        if self.workflow_running:
            return
        runs = self.window.kernel.workflow_service.recent_runs()
        history = "\n\n".join(
            f"{run['goal']}\n{run['status'].capitalize()} · {run['created_at']}"
            for run in runs
        )
        self.workflow_text.setPlainText(history or "No saved workflow runs.")
        checkpoints = self.window.kernel.workflow_service.checkpoints()
        if checkpoints:
            details = []
            for run in checkpoints:
                lines = [f"{run['goal']} · {run['status']}"]
                for step in (run["plan"] or {}).get("steps", []):
                    lines.append(f"  {step['name']} · {step['status']}")
                    if step.get("error"):
                        lines.append(f"  {step['error']}")
                if run.get("error"):
                    lines.append(run["error"])
                details.append("\n".join(lines))
            self.workflow_text.setPlainText("\n\n".join(details))

    def make_memory_page(self):
        self.memory = MemoryStore()
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(label("Memory", "Heading"))
        self.memory_notes = QListWidget()
        self.memory_notes.setAccessibleName("Saved notes")
        layout.addWidget(self.memory_notes, 1)
        self.memory_input = QLineEdit()
        self.memory_input.setPlaceholderText("Write a note to remember…")
        self.memory_input.setMaxLength(4000)
        self.memory_input.returnPressed.connect(self.save_memory)
        layout.addWidget(self.memory_input)
        actions = QHBoxLayout()
        actions.addWidget(button("Save note", self.save_memory))
        actions.addWidget(button("Delete selected note", self.delete_memory))
        layout.addLayout(actions)
        self.memory_status = label("", "Muted")
        layout.addWidget(self.memory_status)
        return page

    def refresh_memory(self):
        try:
            notes = self.memory.notes()
        except (OSError, sqlite3.Error) as error:
            self.memory_status.setText(str(error))
            return
        self.memory_notes.clear()
        for note_id, text in notes:
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, note_id)
            self.memory_notes.addItem(item)
        self.memory_status.setText("" if notes else "No saved notes.")

    def save_memory(self):
        try:
            self.memory.save(self.memory_input.text())
        except (ValueError, OSError, sqlite3.Error) as error:
            self.memory_status.setText(str(error))
            return
        self.memory_input.clear()
        self.refresh_memory()

    def delete_memory(self):
        item = self.memory_notes.currentItem()
        if item is None:
            return
        try:
            self.memory.delete(item.data(Qt.ItemDataRole.UserRole))
        except (OSError, sqlite3.Error) as error:
            self.memory_status.setText(str(error))
            return
        self.refresh_memory()

    def set_home_prompt(self, text):
        self.home_input.setText(text)
        self.home_input.setFocus()

    def submit_home(self):
        text = self.home_input.text().strip()
        if text:
            self.show_page("Assistant")
            self.msg_input.setText(text)
            self.window.send_message()
            self.home_input.clear()

    def append_chat(self, text):
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        if not self.chat_display.document().isEmpty():
            cursor.insertBlock()
        cursor.insertText(text)
        self.chat_display.setTextCursor(cursor)
        self.chat_display.ensureCursorVisible()

    def set_listening(self, listening):
        self.home_mic.setEnabled(not listening)
        self.header_mic.setEnabled(not listening)
        self.home_mic.setToolTip("Listening…" if listening else "Listen")
        if listening:
            self.set_activity("Listening", "Speak now.")
        elif self.activity_state.text() == "Listening":
            self.set_activity("Idle", "Microphone capture finished.")

    def set_activity(self, state, detail):
        self.activity_state.setText(state)
        self.activity_detail.setText(detail)
        busy = state in ("Working", "Listening")
        self.activity_bar.setRange(0, 0 if busy else 1)
        self.activity_bar.setValue(0)

    def start_goal(self, goal):
        self.workflow_running = True
        self.goal_title.setText(goal if len(goal) <= 72 else f"{goal[:69]}…")
        self.goal_title.setToolTip(goal)
        self.goal_status.setText("In progress")
        self.goal_ring.set_value(None)
        self.workflow_text.setPlainText(f"{goal}\n\nIn progress")
        self.task_preview.setText("○  Waiting for workflow steps.")
        self.tasks_text.setPlainText("Waiting for workflow steps.")

    def finish_goal(self, success, steps):
        self.workflow_running = False
        status = "Completed" if success else "Failed"
        self.goal_status.setText(status)
        self.refresh_workflows()
        completed = sum(state.lower() == "completed" for _, state in steps)
        self.goal_ring.set_value(round(completed / len(steps) * 100) if steps else None)
        rows = [f"{name} · {state.capitalize()}" for name, state in steps]
        self.tasks_text.setPlainText("\n".join(rows) or "No steps were generated.")
        preview = []
        for name, state in steps[:3]:
            mark = {"completed": "✓", "failed": "×"}.get(state.lower(), "○")
            preview.append(f"{mark}  {name[:31]}…" if len(name) > 31 else f"{mark}  {name}")
        self.task_preview.setText("\n".join(preview) or "○  No steps were generated.")
