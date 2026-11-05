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
from orb.services.ai_service import AIService
from orb.services.workflow_service import WorkflowService


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
        self.workflow_service = WorkflowService(self.ai_service)

        self.service_manager.register("ai_service", self.ai_service)
        self.service_manager.register(
            "workflow_service",
            self.workflow_service,
            dependencies=["ai_service"]
        )

    @property
    def state(self) -> str:
        """Return the current application state."""
        return self.lifecycle.state

    def start(self) -> None:
        """
        Start the ORB Platform.
        """
        self.configuration = self.configuration_manager.load()
        self.ai_service.configure(self.configuration.values)
        configure_logging(self.configuration.values)
        self.logger.info("ORB kernel starting")

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
