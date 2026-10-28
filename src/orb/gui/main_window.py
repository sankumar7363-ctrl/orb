"""
ORB Platform
Main Window
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QMessageBox,
    QTextEdit,
)

from orb.models.goal import Goal

from orb.gui.application import ORBGuiApplication

class CreateGoalDialog(QDialog):
    """Dialog used to create a new ORB goal."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Create Goal")
        self.resize(450, 300)

        layout = QVBoxLayout(self)

        title_label = QLabel("Goal Title")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText(
            "Example: Build the login system"
        )

        description_label = QLabel("Description")
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText(
            "Describe what you want ORB to accomplish..."
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(title_label)
        layout.addWidget(self.title_input)
        layout.addWidget(description_label)
        layout.addWidget(self.description_input)
        layout.addWidget(buttons)

    def _accept(self) -> None:
        """Validate and accept the dialog."""

        if not self.title_input.text().strip():
            QMessageBox.warning(
                self,
                "Missing Goal Title",
                "Please enter a goal title.",
            )
            return

        self.accept()

    @property
    def title(self) -> str:
        """Return the entered goal title."""
        return self.title_input.text().strip()

    @property
    def description(self) -> str:
        """Return the entered goal description."""
        return self.description_input.toPlainText().strip()

class ORBMainWindow(QMainWindow):
    """Main window for the ORB Control Center."""

    def __init__(self, application: ORBGuiApplication) -> None:
        super().__init__()

        self.application = application

        self.setWindowTitle("ORB — Operational Reasoning Bot")
        self.resize(1200, 750)

        self._navigation_buttons: dict[str, QPushButton] = {}

        self._build_ui()
        self._update_status()

    def _create_goals_page(self) -> QWidget:
        """Create the ORB goals page."""

        page = QWidget()
        layout = QVBoxLayout(page)

        header = QHBoxLayout()

        title = QLabel("Goals")
        title.setStyleSheet(
            "font-size: 26px; font-weight: bold;"
        )

        new_goal_button = QPushButton("+ New Goal")
        new_goal_button.clicked.connect(
            self._create_goal
        )

        header.addWidget(title)
        header.addStretch()
        header.addWidget(new_goal_button)

        layout.addLayout(header)

        self.goals_container = QVBoxLayout()

        layout.addLayout(self.goals_container)
        layout.addStretch()

        self._refresh_goals()

        return page

    def _refresh_goals(self) -> None:
        """Refresh the goals displayed on the page."""

        while self.goals_container.count():
            item = self.goals_container.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        if not self.application.goals:
            empty_label = QLabel(
                "No goals yet.\n\n"
                "Create a goal and ORB will eventually "
                "plan the work required to accomplish it."
            )

            empty_label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            self.goals_container.addWidget(empty_label)
            return

        for goal in self.application.goals:
            self.goals_container.addWidget(
                self._create_goal_card(goal)
            )

    def _create_goal(self) -> None:
        """Open the create-goal dialog and create a goal."""

        dialog = CreateGoalDialog(self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        goal = self.application.create_goal(
            title=dialog.title,
            description=dialog.description,
        )

        self._refresh_goals()
        self._update_status()

        QMessageBox.information(
            self,
            "Goal Created",
            f"Goal created successfully:\n\n{goal.title}",
        )

    def _create_goal_card(self, goal: Goal) -> QFrame:
        """Create a visual card for an ORB goal."""

        card = QFrame()
        card.setFrameStyle(QFrame.Shape.Box)

        layout = QVBoxLayout(card)

        title = QLabel(goal.title)
        title.setStyleSheet(
            "font-size: 18px; font-weight: bold;"
        )

        status = QLabel(
            f"Status: {goal.status.value}"
        )

        description = QLabel(
            goal.description or "No description provided."
        )

        description.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(status)
        layout.addWidget(description)

        return card

    def _build_ui(self) -> None:
        """Build the Control Center interface."""

        root = QWidget()
        root_layout = QHBoxLayout(root)

        sidebar = self._create_sidebar()

        self.pages = QStackedWidget()

        self.dashboard_page = self._create_dashboard_page()

        self.goals_page = self._create_goals_page()

        self.tasks_page = self._create_placeholder_page(
            "Tasks",
            "Task management will be implemented here.",
        )

        self.workflows_page = self._create_placeholder_page(
            "Workflows",
            "Workflow management will be implemented here.",
        )

        self.activity_page = self._create_activity_page()

        self.settings_page = self._create_placeholder_page(
            "Settings",
            "ORB configuration and settings will be implemented here.",
        )

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
        """Create the navigation sidebar."""

        sidebar = QFrame()
        sidebar.setFixedWidth(220)

        layout = QVBoxLayout(sidebar)

        title = QLabel("ORB")
        title.setStyleSheet(
            "font-size: 28px; font-weight: bold;"
        )

        subtitle = QLabel("Operational Reasoning Bot")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(30)

        navigation_items = (
            "Dashboard",
            "Goals",
            "Tasks",
            "Workflows",
            "Activity",
            "Settings",
        )

        for name in navigation_items:
            button = QPushButton(name)
            button.setMinimumHeight(40)

            button.clicked.connect(
                lambda checked=False, page=name: self._select_page(page)
            )

            self._navigation_buttons[name] = button
            layout.addWidget(button)

        layout.addStretch()

        return sidebar

    def _create_dashboard_page(self) -> QWidget:
        """Create the main dashboard page."""

        page = QWidget()
        layout = QVBoxLayout(page)

        header_layout = QHBoxLayout()

        header = QLabel("Control Center")
        header.setStyleSheet(
            "font-size: 26px; font-weight: bold;"
        )

        self.status_label = QLabel()
        self.status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
        )

        header_layout.addWidget(header)
        header_layout.addWidget(self.status_label)

        layout.addLayout(header_layout)

        cards = QHBoxLayout()

        self.kernel_card = self._create_card(
            "Kernel",
            "Unknown",
        )

        self.services_card = self._create_card(
            "Services",
            "0",
        )

        self.plugins_card = self._create_card(
            "Plugins",
            "0",
        )

        cards.addWidget(self.kernel_card)
        cards.addWidget(self.services_card)
        cards.addWidget(self.plugins_card)

        layout.addLayout(cards)

        activity_title = QLabel("Recent Activity")
        activity_title.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )

        layout.addWidget(activity_title)

        self.activity_label = QLabel(
            "Waiting for ORB activity..."
        )

        self.activity_label.setFrameStyle(
            QFrame.Shape.Box
        )

        self.activity_label.setMinimumHeight(150)

        layout.addWidget(self.activity_label)

        controls = QHBoxLayout()

        self.start_button = QPushButton("Start ORB")
        self.stop_button = QPushButton("Stop ORB")

        self.start_button.clicked.connect(
            self._start_orb
        )

        self.stop_button.clicked.connect(
            self._stop_orb
        )

        controls.addWidget(self.start_button)
        controls.addWidget(self.stop_button)

        layout.addLayout(controls)

        return page

    def _create_activity_page(self) -> QWidget:
        """Create the full activity page."""

        page = QWidget()
        layout = QVBoxLayout(page)

        title = QLabel("Activity")
        title.setStyleSheet(
            "font-size: 26px; font-weight: bold;"
        )

        layout.addWidget(title)

        self.full_activity_label = QLabel(
            "No ORB activity yet."
        )

        self.full_activity_label.setFrameStyle(
            QFrame.Shape.Box
        )

        self.full_activity_label.setAlignment(
            Qt.AlignmentFlag.AlignTop
            | Qt.AlignmentFlag.AlignLeft
        )

        self.full_activity_label.setMinimumHeight(400)

        layout.addWidget(self.full_activity_label)

        return page

    @staticmethod
    def _create_placeholder_page(
        title: str,
        description: str,
    ) -> QWidget:
        """Create a temporary page."""

        page = QWidget()
        layout = QVBoxLayout(page)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            "font-size: 26px; font-weight: bold;"
        )

        description_label = QLabel(description)
        description_label.setStyleSheet(
            "font-size: 16px;"
        )

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addStretch()

        return page

    @staticmethod
    def _create_card(
        title: str,
        value: str,
    ) -> QFrame:
        """Create a dashboard information card."""

        card = QFrame()
        card.setFrameStyle(QFrame.Shape.Box)

        layout = QVBoxLayout(card)

        title_label = QLabel(title)
        value_label = QLabel(value)

        value_label.setStyleSheet(
            "font-size: 22px; font-weight: bold;"
        )

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        return card

    def _select_page(self, page_name: str) -> None:
        """Switch the visible page."""

        page_indexes = {
            "Dashboard": 0,
            "Goals": 1,
            "Tasks": 2,
            "Workflows": 3,
            "Activity": 4,
            "Settings": 5,
        }

        index = page_indexes[page_name]

        self.pages.setCurrentIndex(index)

        for name, button in self._navigation_buttons.items():
            button.setEnabled(name != page_name)

        if page_name == "Activity":
            self._update_activity_page()

    def _update_status(self) -> None:
        """Update dashboard status from ORB."""

        state = self.application.state

        self.status_label.setText(
            f"ORB State: {state}"
        )

        self.kernel_card.layout().itemAt(1).widget().setText(
            state
        )

        self.services_card.layout().itemAt(1).widget().setText(
            str(self.application.service_count)
        )

        self.plugins_card.layout().itemAt(1).widget().setText(
            str(self.application.plugin_count)
        )

        activity = self.application.activity

        if activity:
            self.activity_label.setText(
                "\n".join(activity)
            )
        else:
            self.activity_label.setText(
                "Waiting for ORB activity..."
            )

        self._update_activity_page()

    def _update_activity_page(self) -> None:
        """Update the full activity page."""

        activity = self.application.activity

        if activity:
            self.full_activity_label.setText(
                "\n".join(activity)
            )
        else:
            self.full_activity_label.setText(
                "No ORB activity yet."
            )

    def _start_orb(self) -> None:
        """Start ORB through the application boundary."""

        self.application.start_orb()
        self._update_status()

    def _stop_orb(self) -> None:
        """Stop ORB through the application boundary."""

        self.application.stop_orb()
        self._update_status()