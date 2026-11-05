"""
ORB Platform
Modernized Main Window & Control Center[cite: 2]
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from orb.gui.application import ORBGuiApplication
from orb.models.goal import Goal


GLOBAL_STYLESHEET = """
QMainWindow {
    background-color: #0f172a;
}
QWidget {
    color: #e2e8f0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
}
#Sidebar {
    background-color: #1e293b;
    border-right: 1px solid #334155;
}
#Sidebar QPushButton {
    text-align: left;
    padding: 10px 16px;
    border-radius: 8px;
    border: none;
    font-size: 14px;
    font-weight: 500;
    color: #94a3b8;
    background-color: transparent;
}
#Sidebar QPushButton:hover {
    background-color: #334155;
    color: #f8fafc;
}
#Sidebar QPushButton:disabled {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: 600;
}
.StatCard {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 16px;
}
.GoalCard {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 14px;
}
.GoalCard:hover {
    border: 1px solid #475569;
}
QPushButton.PrimaryButton {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: 600;
    border-radius: 8px;
    padding: 8px 16px;
    border: none;
}
QPushButton.PrimaryButton:hover {
    background-color: #2563eb;
}
QPushButton.SuccessButton {
    background-color: #10b981;
    color: #ffffff;
    font-weight: 600;
    border-radius: 8px;
    padding: 10px 20px;
    border: none;
}
QPushButton.SuccessButton:hover {
    background-color: #059669;
}
QPushButton.SuccessButton:disabled {
    background-color: #1e293b;
    color: #64748b;
    border: 1px solid #334155;
}
QPushButton.DangerButton {
    background-color: #ef4444;
    color: #ffffff;
    font-weight: 600;
    border-radius: 8px;
    padding: 10px 20px;
    border: none;
}
QPushButton.DangerButton:hover {
    background-color: #dc2626;
}
QPushButton.DangerButton:disabled {
    background-color: #1e293b;
    color: #64748b;
    border: 1px solid #334155;
}
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 10px;
    color: #f8fafc;
    selection-background-color: #3b82f6;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #3b82f6;
}
QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 4px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #475569;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""


class CreateGoalDialog(QDialog):
    """Modern modal dialog used to create a new ORB goal[cite: 2]."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Create New Goal")
        self.resize(500, 360)
        self.setStyleSheet("background-color: #1e293b; color: #f8fafc;")

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Add Operational Goal")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #f8fafc;")
        layout.addWidget(header)

        title_label = QLabel("Title")
        title_label.setStyleSheet("font-weight: 600; color: #94a3b8;")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g., Optimize Database Indices")

        desc_label = QLabel("Description")
        desc_label.setStyleSheet("font-weight: 600; color: #94a3b8;")
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Describe the high-level intent...")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Create Goal")
        buttons.setStyleSheet("""
            QPushButton {
                padding: 8px 18px;
                border-radius: 6px;
                font-weight: 600;
            }
        """)

        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(title_label)
        layout.addWidget(self.title_input)
        layout.addWidget(desc_label)
        layout.addWidget(self.description_input)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        if not self.title_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Goal title cannot be empty.")
            return
        self.accept()

    @property
    def title(self) -> str:
        return self.title_input.text().strip()

    @property
    def description(self) -> str:
        return self.description_input.toPlainText().strip()


class ORBMainWindow(QMainWindow):
    """Refined Main Window for the ORB Control Center[cite: 2]."""

    def __init__(self, application: ORBGuiApplication) -> None:
        super().__init__()
        self.application = application

        self.setWindowTitle("ORB — Operational Reasoning Platform")
        self.resize(1240, 800)
        self.setStyleSheet(GLOBAL_STYLESHEET)

        self._navigation_buttons: dict[str, QPushButton] = {}

        # 1. Build UI first so widgets exist
        self._build_ui()

        # 2. Wire signals to UI slots
        self._wire_signals()

        # 3. Synchronize initial state
        self._update_status()

    def _wire_signals(self) -> None:
        """Connect reactive signals from ORBGuiApplication if available."""
        if hasattr(self.application, "activity_recorded"):
            self.application.activity_recorded.connect(self._append_activity_entry)
        if hasattr(self.application, "orb_state_changed"):
            self.application.orb_state_changed.connect(lambda _: self._update_status())
        if hasattr(self.application, "goal_created_signal"):
            self.application.goal_created_signal.connect(lambda _: self._refresh_goals())

    def _append_activity_entry(self, entry: str) -> None:
        """Append a newly recorded activity line to the console views."""
        if hasattr(self, "dashboard_console"):
            self.dashboard_console.appendPlainText(entry)
            self.dashboard_console.verticalScrollBar().setValue(
                self.dashboard_console.verticalScrollBar().maximum()
            )
        if hasattr(self, "full_console"):
            self.full_console.appendPlainText(entry)
            self.full_console.verticalScrollBar().setValue(
                self.full_console.verticalScrollBar().maximum()
            )

    def _build_ui(self) -> None:
        """Build the responsive Control Center layout[cite: 2]."""
        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = self._create_sidebar()
        self.pages = QStackedWidget()
        self.pages.setContentsMargins(28, 28, 28, 28)

        # Pages
        self.dashboard_page = self._create_dashboard_page()
        self.goals_page = self._create_goals_page()
        self.tasks_page = self._create_placeholder_page("Tasks", "Task dispatching and agent queues.")
        self.workflows_page = self._create_placeholder_page("Workflows", "DAG and automated step triggers.")
        self.activity_page = self._create_activity_page()
        self.settings_page = self._create_placeholder_page("Settings", "Platform configuration and kernel toggles.")

        self.pages.addWidget(self.dashboard_page)
        self.pages.addWidget(self.goals_page)
        self.pages.addWidget(self.tasks_page)
        self.pages.addWidget(self.workflows_page)
        self.pages.addWidget(self.activity_page)
        self.pages.addWidget(self.settings_page)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.pages, 1)

        self.setCentralWidget(root)
        self._select_page("Dashboard")

    def _create_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(240)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(18, 24, 18, 24)
        layout.setSpacing(8)

        brand_layout = QVBoxLayout()
        logo_label = QLabel("⚡ ORB")
        logo_label.setStyleSheet("font-size: 24px; font-weight: 800; color: #38bdf8;")
        sub_label = QLabel("Autonomous Reasoning Engine")
        sub_label.setStyleSheet("font-size: 11px; font-weight: 500; color: #64748b;")

        brand_layout.addWidget(logo_label)
        brand_layout.addWidget(sub_label)
        layout.addLayout(brand_layout)
        layout.addSpacing(24)

        nav_items = ("Dashboard", "Goals", "Tasks", "Workflows", "Activity", "Settings")
        for name in nav_items:
            btn = QPushButton(f"  {name}")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, p=name: self._select_page(p))
            self._navigation_buttons[name] = btn
            layout.addWidget(btn)

        layout.addStretch()

        version_label = QLabel("v2.4.0 • Local Host")
        version_label.setStyleSheet("color: #475569; font-size: 11px;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        return sidebar

    def _create_dashboard_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        layout.setContentsMargins(0, 0, 0, 0)

        header_layout = QHBoxLayout()
        title_box = QVBoxLayout()
        header = QLabel("Control Center")
        header.setStyleSheet("font-size: 28px; font-weight: 700; color: #f8fafc;")
        desc = QLabel("Real-time operational status and metrics")
        desc.setStyleSheet("color: #94a3b8; font-size: 14px;")
        title_box.addWidget(header)
        title_box.addWidget(desc)

        self.status_badge = QLabel("● ORB OFFLINE")
        self.status_badge.setStyleSheet(
            "background-color: #334155; color: #94a3b8; padding: 6px 14px; "
            "border-radius: 14px; font-weight: 600; font-size: 12px;"
        )
        self.status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout.addLayout(title_box)
        header_layout.addStretch()
        header_layout.addWidget(self.status_badge)
        layout.addLayout(header_layout)

        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(16)
        self.kernel_card, self.kernel_val = self._create_card("Engine State", "Inactive", "#38bdf8")
        self.services_card, self.services_val = self._create_card("Loaded Services", "0", "#a855f7")
        self.plugins_card, self.plugins_val = self._create_card("Active Plugins", "0", "#ec4899")

        metrics_layout.addWidget(self.kernel_card)
        metrics_layout.addWidget(self.services_card)
        metrics_layout.addWidget(self.plugins_card)
        layout.addLayout(metrics_layout)

        activity_title = QLabel("Recent Event Stream")
        activity_title.setStyleSheet("font-size: 17px; font-weight: 600; color: #f8fafc; margin-top: 10px;")
        layout.addWidget(activity_title)

        self.dashboard_console = QPlainTextEdit()
        self.dashboard_console.setReadOnly(True)
        self.dashboard_console.setFont(QFont("JetBrains Mono, Menlo, Consolas", 11))
        self.dashboard_console.setMinimumHeight(180)
        layout.addWidget(self.dashboard_console)

        controls = QHBoxLayout()
        self.start_button = QPushButton("Start ORB")
        self.start_button.setProperty("class", "SuccessButton")
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.stop_button = QPushButton("Stop ORB")
        self.stop_button.setProperty("class", "DangerButton")
        self.stop_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.start_button.clicked.connect(self._start_orb)
        self.stop_button.clicked.connect(self._stop_orb)

        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)
        controls.addStretch()
        layout.addLayout(controls)

        return page

    def _create_goals_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        header = QHBoxLayout()
        header_text = QVBoxLayout()
        title = QLabel("Goals")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #f8fafc;")
        subtitle = QLabel("Strategic initiatives orchestrated by ORB agents")
        subtitle.setStyleSheet("color: #94a3b8; font-size: 14px;")
        header_text.addWidget(title)
        header_text.addWidget(subtitle)

        new_goal_btn = QPushButton("+ New Goal")
        new_goal_btn.setProperty("class", "PrimaryButton")
        new_goal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_goal_btn.clicked.connect(self._create_goal)

        header.addLayout(header_text)
        header.addStretch()
        header.addWidget(new_goal_btn)
        layout.addLayout(header)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setStyleSheet("background: transparent;")

        container_widget = QWidget()
        container_widget.setStyleSheet("background: transparent;")
        self.goals_container = QVBoxLayout(container_widget)
        self.goals_container.setSpacing(12)
        self.goals_container.setContentsMargins(0, 0, 0, 0)
        self.goals_container.addStretch()

        scroll_area.setWidget(container_widget)
        layout.addWidget(scroll_area)

        self._refresh_goals()
        return page

    def _refresh_goals(self) -> None:
        """Clear and rebuild the goal card list[cite: 2]."""
        while self.goals_container.count() > 1:
            item = self.goals_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        goals = self.application.goals
        if not goals:
            empty_box = QFrame()
            empty_box.setStyleSheet("background: #1e293b; border-radius: 12px; padding: 40px;")
            box_layout = QVBoxLayout(empty_box)
            empty_lbl = QLabel(
                "No goals found.\n\n"
                "Create your first goal to initiate automatic reasoning and task decomposition."
            )
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet("color: #64748b; font-size: 15px; font-weight: 500;")
            box_layout.addWidget(empty_lbl)
            self.goals_container.insertWidget(0, empty_box)
            return

        for idx, goal in enumerate(goals):
            self.goals_container.insertWidget(idx, self._create_goal_card(goal))

    def _create_goal_card(self, goal: Goal) -> QFrame:
        card = QFrame()
        card.setProperty("class", "GoalCard")

        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        title = QLabel(goal.title)
        title.setStyleSheet("font-size: 16px; font-weight: 700; color: #f8fafc;")

        status_text = (
            goal.status.value if hasattr(goal.status, "value") else str(goal.status)
        ).upper()

        status_badge = QLabel(f"  {status_text}  ")
        status_badge.setStyleSheet(
            "background-color: #064e3b; color: #34d399; border-radius: 4px; font-size: 11px; font-weight: bold; padding: 2px 6px;"
        )

        top_row.addWidget(title)
        top_row.addStretch()
        top_row.addWidget(status_badge)
        layout.addLayout(top_row)

        description = QLabel(goal.description or "No descriptive notes specified for this goal.")
        description.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.4;")
        description.setWordWrap(True)
        layout.addWidget(description)

        return card

    def _create_activity_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        title = QLabel("System Activity Logs")
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #f8fafc;")
        layout.addWidget(title)

        self.full_console = QPlainTextEdit()
        self.full_console.setReadOnly(True)
        self.full_console.setFont(QFont("JetBrains Mono, Menlo, Consolas", 11))
        layout.addWidget(self.full_console)

        return page

    def _create_placeholder_page(self, title_text: str, desc_text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel(title_text)
        title.setStyleSheet("font-size: 28px; font-weight: 700; color: #f8fafc;")
        desc = QLabel(desc_text)
        desc.setStyleSheet("font-size: 14px; color: #64748b; margin-top: 6px;")

        layout.addWidget(title)
        layout.addWidget(desc)
        layout.addStretch()
        return page

    def _create_card(self, title: str, value: str, accent_color: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setProperty("class", "StatCard")

        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px;")

        value_lbl = QLabel(value)
        value_lbl.setStyleSheet(f"font-size: 26px; font-weight: 800; color: {accent_color};")

        layout.addWidget(title_lbl)
        layout.addWidget(value_lbl)

        return card, value_lbl

    def _select_page(self, page_name: str) -> None:
        indexes = {"Dashboard": 0, "Goals": 1, "Tasks": 2, "Workflows": 3, "Activity": 4, "Settings": 5}
        self.pages.setCurrentIndex(indexes[page_name])

        for name, btn in self._navigation_buttons.items():
            btn.setEnabled(name != page_name)

        if page_name == "Activity":
            self._update_activity_consoles()

    def _update_status(self) -> None:
        """Query state and refresh indicators[cite: 2]."""
        state = getattr(self.application, "state", "UNKNOWN").upper()
        is_running = getattr(self.application, "is_running", state == "RUNNING")

        self.kernel_val.setText(state)
        self.services_val.setText(str(self.application.service_count))
        self.plugins_val.setText(str(self.application.plugin_count))

        if is_running:
            self.status_badge.setText("● ORB ONLINE")
            self.status_badge.setStyleSheet(
                "background-color: #064e3b; color: #34d399; padding: 6px 14px; "
                "border-radius: 14px; font-weight: 700; font-size: 12px;"
            )
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
        else:
            self.status_badge.setText("● ORB OFFLINE")
            self.status_badge.setStyleSheet(
                "background-color: #334155; color: #94a3b8; padding: 6px 14px; "
                "border-radius: 14px; font-weight: 700; font-size: 12px;"
            )
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)

        self._update_activity_consoles()

    def _update_activity_consoles(self) -> None:
        activity = "\n".join(self.application.activity)
        if hasattr(self, "dashboard_console"):
            self.dashboard_console.setPlainText(activity)
            self.dashboard_console.verticalScrollBar().setValue(
                self.dashboard_console.verticalScrollBar().maximum()
            )
        if hasattr(self, "full_console"):
            self.full_console.setPlainText(activity)
            self.full_console.verticalScrollBar().setValue(
                self.full_console.verticalScrollBar().maximum()
            )

    def _create_goal(self) -> None:
        dialog = CreateGoalDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            goal = self.application.create_goal(
                title=dialog.title,
                description=dialog.description,
            )
            if goal:
                self._refresh_goals()
                self._update_status()

    def _start_orb(self) -> None:
        self.application.start_orb()
        self._update_status()

    def _stop_orb(self) -> None:
        self.application.stop_orb()
        self._update_status()