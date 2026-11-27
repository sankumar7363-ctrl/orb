import unittest

from orb.core.kernel import ORBKernel
from orb.execution import ExecutionService


class KernelIntegrationTests(unittest.TestCase):

    def test_execution_service_is_registered_and_injected(self):
        kernel = ORBKernel()

        self.assertIn(
            "execution_service",
            kernel.service_manager.service_names,
        )

        registered_service = kernel.service_manager.get(
            "execution_service"
        )

        self.assertIs(registered_service, kernel.execution_service)
        self.assertIsInstance(registered_service, ExecutionService)
        self.assertIs(
            kernel.workflow_service.execution_service,
            kernel.execution_service,
        )

    def test_workflow_engine_uses_registered_execution_service(self):
        kernel = ORBKernel()

        self.assertIs(
            kernel.workflow_service._engine.execution_service,
            kernel.execution_service,
        )

    def test_voice_service_is_registered_without_starting_microphone(self):
        kernel = ORBKernel()

        self.assertIn("voice_service", kernel.service_manager.service_names)
        self.assertIs(
            kernel.service_manager.get("voice_service"),
            kernel.voice_service,
        )
        self.assertFalse(kernel.voice_service.is_wake_word_active)


if __name__ == "__main__":
    unittest.main()
