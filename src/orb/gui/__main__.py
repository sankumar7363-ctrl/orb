"""
=============================================================
ORB Platform - Operational Reasoning Platform
Direct Ollama LLM-Integrated AI Assistant Dashboard

Author: Santosh Kumar
=============================================================
"""

import sys
import math
import random
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QLineEdit, QGridLayout, QTextEdit
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient
from orb.core.kernel import ORBKernel


class LLMExecutionWorker(QThread):
    """Background worker using ORB's central AI and workflow services."""

    log_signal = Signal(str)
    finished_signal = Signal(str)

    def __init__(self, kernel: ORBKernel, query: str):
        super().__init__()
        self.kernel = kernel
        self.query = query.strip()

    def run(self):
        try:
            q_lower = self.query.lower()

            action_keywords = [
                "create",
                "build",
                "deploy",
                "run",
                "execute",
                "generate code",
                "setup",
            ]

            is_action_task = any(
                q_lower.startswith(keyword)
                for keyword in action_keywords
            )

            if is_action_task:
                self.log_signal.emit(
                    f"⚙️ Processing workflow goal: '{self.query}'..."
                )

                success = self.kernel.workflow_service.run_goal(
                    self.query
                )

                if success:
                    response = (
                        f"Task '{self.query}' successfully completed."
                    )
                else:
                    response = (
                        "Workflow could not be completed. "
                        "Check the execution logs for details."
                    )

            else:
                self.log_signal.emit(
                    "🧠 Processing request through ORB AI Service..."
                )

                response = self.kernel.ai_service.generate(
                    prompt=self.query,
                    system_prompt=(
                        "You are ORB, a helpful local AI assistant. "
                        "Respond clearly, accurately, and concisely. "
                        "Do not claim to have performed actions unless "
                        "they were actually executed and verified."
                    ),
                )

            self.finished_signal.emit(response)

        except Exception as error:
            error_message = f"❌ ORB Error: {error}"
            self.log_signal.emit(error_message)
            self.finished_signal.emit(error_message)

class UltronNeuralCoreWidget(QWidget):
    """Cinematic Golden Ultron Holographic Neural Network Core."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(180, 180)
        self.angle1 = 0
        self.angle2 = 0
        self.pulse = 0

        random.seed(42)
        self.nodes = []
        for _ in range(24):
            r = random.randint(25, 75)
            theta = random.uniform(0, 2 * math.pi)
            self.nodes.append((r, theta))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_core)
        self.timer.start(25)

    def animate_core(self):
        self.angle1 = (self.angle1 + 1.5) % 360
        self.angle2 = (self.angle2 - 2.0) % 360
        self.pulse = (self.pulse + 0.1) % (2 * math.pi)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        cx, cy = self.width() / 2, self.height() / 2

        pulse_val = 50 + int(15 * math.sin(self.pulse))
        bg_gradient = QRadialGradient(cx, cy, pulse_val)
        bg_gradient.setColorAt(0, QColor(255, 140, 0, 100))
        bg_gradient.setColorAt(1, QColor(255, 100, 0, 0))
        painter.setBrush(QBrush(bg_gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(int(cx - pulse_val), int(cy - pulse_val), int(pulse_val * 2), int(pulse_val * 2))

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle1)
        pen1 = QPen(QColor(255, 170, 50, 180), 1.5, Qt.DashLine)
        painter.setPen(pen1)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(-75, -75, 150, 150)
        painter.restore()

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle2 * 1.3)
        pen2 = QPen(QColor(255, 200, 100, 220), 2, Qt.SolidLine)
        painter.setPen(pen2)
        painter.drawEllipse(-55, -55, 110, 110)
        painter.restore()

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(self.angle1 * 0.5)

        node_coords = []
        for (r, theta) in self.nodes:
            current_theta = theta + math.radians(self.angle1 * 0.8)
            nx = r * math.cos(current_theta)
            ny = r * math.sin(current_theta)
            node_coords.append((nx, ny))

        net_pen = QPen(QColor(255, 150, 0, 70), 0.8)
        painter.setPen(net_pen)
        for i in range(len(node_coords)):
            for j in range(i + 1, len(node_coords)):
                x1, y1 = node_coords[i]
                x2, y2 = node_coords[j]
                if math.hypot(x2 - x1, y2 - y1) < 45:
                    painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(255, 220, 100, 255)))
        for (nx, ny) in node_coords:
            painter.drawEllipse(int(nx - 2), int(ny - 2), 4, 4)

        painter.restore()

        core_gradient = QRadialGradient(cx, cy, 25)
        core_gradient.setColorAt(0, QColor(255, 255, 255, 255))
        core_gradient.setColorAt(0.4, QColor(255, 180, 50, 240))
        core_gradient.setColorAt(1, QColor(200, 80, 0, 150))
        painter.setBrush(QBrush(core_gradient))
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.drawEllipse(int(cx - 20), int(cy - 20), 40, 40)


class ORBLLMDashboard(QMainWindow):
    """LLM-Integrated Dashboard Window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ORB — Operational Reasoning Platform (Direct Ollama Connected)")
        self.resize(1360, 780)

        try:
            self.kernel = ORBKernel()
            self.kernel.start()
        except Exception as e:
            print(f"Kernel init warning: {e}")

        self.init_ui()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet("background-color: #0b0f19; color: #ffffff; font-family: 'Segoe UI', sans-serif;")

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(16)

        # COL 1: LEFT SIDEBAR
        sidebar = QFrame()
        sidebar.setStyleSheet("background-color: #111827; border-radius: 12px;")
        sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 20)
        sidebar_layout.setSpacing(8)

        brand_layout = QHBoxLayout()
        logo_icon = QLabel("🔵")
        logo_icon.setStyleSheet("font-size: 16px;")
        brand_title = QLabel("AI Assistant")
        brand_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        brand_layout.addWidget(logo_icon)
        brand_layout.addWidget(brand_title)
        brand_layout.addStretch()
        sidebar_layout.addLayout(brand_layout)

        sidebar_layout.addSpacing(15)

        nav_items = [
            ("AI Assistant", "💬"),
            ("Dashboard", "🏠"),
            ("Tasks", "📋"),
            ("Calendar", "📅"),
            ("Notes", "📝"),
            ("Integrations", "🔌"),
            ("Settings", "⚙️")
        ]

        btn_style = (
            "QPushButton {"
            "  text-align: left;"
            "  padding: 10px 14px;"
            "  border-radius: 8px;"
            "  color: #9ca3af;"
            "  background-color: transparent;"
            "  font-size: 13px;"
            "  font-weight: 500;"
            "}"
            "QPushButton:hover {"
            "  background-color: #1f2937;"
            "  color: #ffffff;"
            "}"
            "QPushButton:checked {"
            "  background-color: #2563eb;"
            "  color: #ffffff;"
            "  font-weight: bold;"
            "}"
        )

        self.nav_buttons = {}
        for idx, (name, icon) in enumerate(nav_items):
            btn = QPushButton(f"  {icon}     {name}")
            btn.setCheckable(True)
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda checked, i=idx, n=name: self.switch_page(i, n))
            sidebar_layout.addWidget(btn)
            self.nav_buttons[name] = btn

        sidebar_layout.addStretch()

        dark_mode_frame = QHBoxLayout()
        dm_label = QLabel("Dark Mode")
        dm_label.setStyleSheet("font-size: 12px; color: #9ca3af;")
        dm_toggle = QLabel("🟢")
        dark_mode_frame.addWidget(dm_label)
        dark_mode_frame.addStretch()
        dark_mode_frame.addWidget(dm_toggle)
        sidebar_layout.addLayout(dark_mode_frame)

        sidebar_layout.addSpacing(10)

        profile_frame = QFrame()
        profile_frame.setStyleSheet("background-color: #1f2937; border-radius: 8px; padding: 6px;")
        profile_layout = QHBoxLayout(profile_frame)
        profile_layout.setContentsMargins(6, 6, 6, 6)

        avatar_lbl = QLabel("👩‍💼")
        avatar_lbl.setStyleSheet("font-size: 18px; background: #374151; border-radius: 14px; padding: 4px;")

        user_info = QVBoxLayout()
        user_info.setSpacing(1)
        name_lbl = QLabel("Jessica Smith")
        name_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #ffffff;")
        plan_lbl = QLabel("Premium Plan")
        plan_lbl.setStyleSheet("font-size: 10px; color: #9ca3af;")
        user_info.addWidget(name_lbl)
        user_info.addWidget(plan_lbl)

        profile_layout.addWidget(avatar_lbl)
        profile_layout.addLayout(user_info)
        sidebar_layout.addWidget(profile_frame)

        root_layout.addWidget(sidebar)

        # COL 2: CENTER WORKSPACE
        center_frame = QFrame()
        center_frame.setStyleSheet("background-color: #111827; border-radius: 12px;")
        center_layout = QVBoxLayout(center_frame)
        center_layout.setContentsMargins(24, 24, 24, 24)
        center_layout.setSpacing(15)

        greeting_layout = QVBoxLayout()
        greeting_layout.setSpacing(2)
        title_lbl = QLabel("Hello, Jessica! 👋")
        title_lbl.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        sub_lbl = QLabel("ORB Direct Ollama Neural Connection Active")
        sub_lbl.setStyleSheet("font-size: 13px; color: #3b82f6; font-weight: bold;")
        greeting_layout.addWidget(title_lbl)
        greeting_layout.addWidget(sub_lbl)
        center_layout.addLayout(greeting_layout)

        self.stack = QStackedWidget()

        chat_page = QWidget()
        chat_layout = QVBoxLayout(chat_page)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(12)

        banner_card = QFrame()
        banner_card.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1e1b4b, stop:1 #0f172a); border-radius: 16px; border: 1px solid #312e81;")
        banner_layout = QHBoxLayout(banner_card)
        banner_layout.setContentsMargins(15, 15, 15, 15)

        left_prompts = QVBoxLayout()
        left_prompts.setSpacing(8)
        p1 = QLabel("💬  Create a content plan\n      for this month")
        p2 = QLabel("📄  Summarize this\n      PDF document")
        for p in [p1, p2]:
            p.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); color: #e2e8f0; padding: 10px; border-radius: 8px; font-size: 11px;")
            left_prompts.addWidget(p)

        self.ultron_core = UltronNeuralCoreWidget()

        right_prompts = QVBoxLayout()
        right_prompts.setSpacing(8)
        r1 = QLabel("⛅  What's the weather like\n      tomorrow?")
        r2 = QLabel("✉️  Help me write an email\n      to my team")
        for r in [r1, r2]:
            r.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); color: #e2e8f0; padding: 10px; border-radius: 8px; font-size: 11px;")
            right_prompts.addWidget(r)

        banner_layout.addLayout(left_prompts)
        banner_layout.addWidget(self.ultron_core, alignment=Qt.AlignCenter)
        banner_layout.addLayout(right_prompts)

        chat_layout.addWidget(banner_card)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("background-color: #0f172a; color: #00ffcc; font-family: Consolas; font-size: 12px; border: 1px solid #1e293b; border-radius: 8px; padding: 10px;")
        self.chat_display.append("🤖 ORB Direct Ollama Stream Connected. Type a prompt below...")
        chat_layout.addWidget(self.chat_display)

        input_card = QFrame()
        input_card.setStyleSheet("background-color: #1f2937; border-radius: 12px; padding: 4px;")
        input_layout = QHBoxLayout(input_card)

        mic_btn = QPushButton("🎙️")
        mic_btn.setStyleSheet("background: transparent; font-size: 16px; border: none; padding: 6px;")

        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Ask anything or enter a task...")
        self.msg_input.setStyleSheet("background: transparent; color: #ffffff; border: none; font-size: 14px; padding: 6px;")
        self.msg_input.returnPressed.connect(self.send_message)

        send_btn = QPushButton("➤")
        send_btn.setStyleSheet("background-color: #2563eb; color: white; font-weight: bold; border-radius: 8px; padding: 8px 14px;")
        send_btn.clicked.connect(self.send_message)

        input_layout.addWidget(mic_btn)
        input_layout.addWidget(self.msg_input)
        input_layout.addWidget(send_btn)

        chat_layout.addWidget(input_card)

        chat_page.setLayout(chat_layout)
        self.stack.addWidget(chat_page)

        for name in ["Dashboard", "Tasks", "Calendar", "Notes", "Integrations", "Settings"]:
            p_widget = QWidget()
            p_layout = QVBoxLayout(p_widget)
            lbl = QLabel(f"{name} Module View")
            lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
            desc = QLabel(f"Manage and configure {name.lower()} operations integrated with ORB kernel.")
            desc.setStyleSheet("color: #9ca3af; font-size: 13px;")
            p_layout.addWidget(lbl)
            p_layout.addWidget(desc)
            p_layout.addStretch()
            self.stack.addWidget(p_widget)

        center_layout.addWidget(self.stack)
        root_layout.addWidget(center_frame, stretch=4)

        # COL 3: RIGHT SIDEBAR
        right_frame = QFrame()
        right_frame.setStyleSheet("background-color: #111827; border-radius: 12px;")
        right_frame.setFixedWidth(280)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(16, 20, 16, 20)
        right_layout.setSpacing(20)

        integ_header = QHBoxLayout()
        integ_title = QLabel("Integrations")
        integ_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        integ_view = QLabel("View all")
        integ_view.setStyleSheet("font-size: 11px; color: #3b82f6;")
        integ_header.addWidget(integ_title)
        integ_header.addStretch()
        integ_header.addWidget(integ_view)
        right_layout.addLayout(integ_header)

        grid_layout = QGridLayout()
        grid_layout.setSpacing(10)
        apps = [("💬", "Slack"), ("🟢", "WhatsApp"), ("✉️", "Gmail"), ("📓", "Notion"),
                ("🐦", "Twitter"), ("📸", "Instagram"), ("🔗", "LinkedIn"), ("➕", "Add New")]
        for idx, (icon, name) in enumerate(apps):
            r, c = divmod(idx, 4)
            btn = QPushButton(icon)
            btn.setStyleSheet("background-color: #1f2937; border-radius: 8px; font-size: 16px; padding: 8px;")
            grid_layout.addWidget(btn, r, c)
        right_layout.addLayout(grid_layout)

        task_header = QHBoxLayout()
        task_title = QLabel("Today's Tasks")
        task_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        task_view = QLabel("View all")
        task_view.setStyleSheet("font-size: 11px; color: #3b82f6;")
        task_header.addWidget(task_title)
        task_header.addStretch()
        task_header.addWidget(task_view)
        right_layout.addLayout(task_header)

        tasks_list = QVBoxLayout()
        tasks_list.setSpacing(8)
        t1 = QLabel("⭕  Team Standup                 10:00 AM")
        t2 = QLabel("⭕  Review Marketing Plan      01:00 PM")
        t3 = QLabel("✅  Client Presentation           03:30 PM")
        for t in [t1, t2, t3]:
            t.setStyleSheet("font-size: 11px; color: #9ca3af; background-color: #1f2937; padding: 8px; border-radius: 6px;")
            tasks_list.addWidget(t)
        right_layout.addLayout(tasks_list)

        prod_header = QHBoxLayout()
        prod_title = QLabel("Productivity")
        prod_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #ffffff;")
        prod_filter = QLabel("This Week ▾")
        prod_filter.setStyleSheet("font-size: 11px; color: #9ca3af;")
        prod_header.addWidget(prod_title)
        prod_header.addStretch()
        prod_header.addWidget(prod_filter)
        right_layout.addLayout(prod_header)

        stats_card = QFrame()
        stats_card.setStyleSheet("background-color: #1f2937; border-radius: 8px; padding: 12px;")
        stats_layout = QVBoxLayout(stats_card)
        stats_layout.setSpacing(6)

        s1 = QLabel("📊  87% Completed")
        s2 = QLabel("📋  Tasks Completed: 24")
        s3 = QLabel("⏱️  Focus Time: 18h 45m")
        s4 = QLabel("🎯  Goals Achieved: 6")
        for s in [s1, s2, s3, s4]:
            s.setStyleSheet("font-size: 11px; color: #e2e8f0;")
            stats_layout.addWidget(s)

        right_layout.addWidget(stats_card)
        right_layout.addStretch()

        root_layout.addWidget(right_frame)

        self.nav_buttons["AI Assistant"].setChecked(True)
        self.switch_page(0, "AI Assistant")

    def send_message(self):
        text = self.msg_input.text().strip()
        if not text:
            return
        self.msg_input.clear()

        self.chat_display.append(f"👤 You: {text}")

        self.worker = LLMExecutionWorker(self.kernel, text)
        self.worker.log_signal.connect(self.append_log)
        self.worker.finished_signal.connect(self.on_response_finished)
        self.worker.start()

    def append_log(self, message: str):
        """Append an execution log to the chat display."""
        self.chat_display.append(message)

    def on_response_finished(self, response: str):
        """Handle completion of an AI response."""
        self.chat_display.append(f"🤖 ORB: {response}")

    def switch_page(self, index: int, name: str):
        for btn_name, btn in self.nav_buttons.items():
            if btn_name != name:
                btn.setChecked(False)
        self.nav_buttons[name].setChecked(True)
        self.stack.setCurrentIndex(index)

    def closeEvent(self, event):
        try:
            self.kernel.stop()
        except Exception:
            pass
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ORBLLMDashboard()
    window.show()
    sys.exit(app.exec())
