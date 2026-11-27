"""
=============================================================
ORB Platform
Kernel

Central coordinator of the ORB Platform.

Author: Santosh Kumar
Architecture: ORB Platform
=============================================================
"""

from orb.core.lifecycle import LifecycleManager
from orb.configuration.manager import Configuration, ConfigurationManager
from orb.events import Event, EventBus
from orb.logging import configure_logging, get_logger, shutdown_logging
from orb.plugins import PluginManager
from orb.services import ServiceManager

# Nayi services import ki gayi hain
from orb.execution import ExecutionService
from orb.execution.workspace import WorkspaceCopyFile, WorkspaceTextFile
from orb.execution.applications import OpenApplication
from orb.execution.desktop import OpenLocalFile, OpenWebsite, SearchWeb
from orb.services.ai_service import AIService
from orb.services.workflow_service import WorkflowService
from orb.voice import VoiceService


class ORBKernel:
    """
    Core execution kernel of the ORB Platform.
    """

    def __init__(self, config_path: str | None = None):
        self.lifecycle = LifecycleManager()
        self.configuration_manager = ConfigurationManager(config_path)
        self.configuration: Configuration | None = None
        self.event_bus = EventBus()
        self.service_manager = ServiceManager()
        self.plugin_manager = PluginManager()
        self.logger = get_logger("kernel")

        # Nayi services initialize aur register ho rahi hain
        self.ai_service = AIService()
        self.workspace_file = WorkspaceTextFile()
        self.workspace_copy = WorkspaceCopyFile(self.workspace_file.root)
        self.open_application = OpenApplication()
        self.capabilities = (
            self.workspace_file, self.workspace_copy, self.open_application,
            OpenWebsite(), SearchWeb(), OpenLocalFile(),
        )
        self.execution_service = ExecutionService(
            permission_checker=self.permits_workspace_action
        )
        self.workflow_service = WorkflowService(
            self.ai_service,
            self.execution_service,
        )
        self.voice_service = VoiceService()

        self.service_manager.register("ai_service", self.ai_service)
        self.service_manager.register(
            "execution_service",
            self.execution_service,
        )
        self.service_manager.register(
            "workflow_service",
            self.workflow_service,
            dependencies=["ai_service", "execution_service"],
        )
        self.service_manager.register("voice_service", self.voice_service)

    @property
    def state(self) -> str:
        """Return the current application state."""
        return self.lifecycle.state

    def permits_workspace_action(self, permission, parameters):
        return any(
            capability.permits(permission, parameters)
            for capability in self.capabilities
        )

    def start(self) -> None:
        """
        Start the ORB Platform.
        """
        self.configuration = self.configuration_manager.load()
        self.ai_service.configure(self.configuration.values)
        self.voice_service.configure(self.configuration.values)
        configure_logging(self.configuration.values)
        self.logger.info("ORB kernel starting")

        for capability in self.capabilities:
            self.execution_service.register_capability(
                capability.name,
                capability,
                required_permission=capability.permission,
                requires_approval=True,
            )
        self.service_manager.start()
        self.plugin_manager.load_all()
        self.plugin_manager.start()

        self.lifecycle.start()
        self.event_bus.publish(Event("kernel.started", {"state": self.state}))
        self.logger.info("ORB kernel started")

    def stop(self) -> None:
        """
        Stop the ORB Platform.
        """
        self.lifecycle.stop()
        self.logger.info("ORB kernel stopping")

        self.plugin_manager.shutdown()
        self.service_manager.shutdown()
        self.lifecycle.shutdown()

        self.event_bus.publish(Event("kernel.stopped", {"state": self.state}))
        self.logger.info("ORB kernel stopped")
        shutdown_logging()

    def is_running(self) -> bool:
        """
        Return True if ORB is running.
        """
        return self.lifecycle.is_running()
