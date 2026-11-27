import unittest
from unittest.mock import Mock

from orb.execution.service import ExecutionService, ExecutionStatus


class ExecutionServiceTests(unittest.TestCase):

    def setUp(self):
        self.handler = Mock()
        self.handler.execute.return_value = {"path": "test.docx"}
        self.handler.verify.return_value = True

    def make_service(self, permission=True, approval=True):
        return ExecutionService(
            permission_checker=lambda permission_name, params: permission,
            approval_handler=lambda action, params: approval,
        )

    def register_word_capability(self, service):
        service.register_capability(
            "Office.Word.Create",
            self.handler,
            required_permission="File.Write",
            requires_approval=True,
        )

    def test_unknown_capability_is_rejected(self):
        service = self.make_service()

        result = service.execute("Unknown.Action", {})

        self.assertEqual(
            result.status,
            ExecutionStatus.CAPABILITY_NOT_FOUND,
        )
        self.handler.execute.assert_not_called()

    def test_permission_denial_blocks_execution(self):
        service = self.make_service(permission=False)
        self.register_word_capability(service)

        result = service.execute("Office.Word.Create", {})

        self.assertEqual(result.status, ExecutionStatus.PERMISSION_DENIED)
        self.handler.execute.assert_not_called()

    def test_approval_is_required(self):
        service = ExecutionService(
            permission_checker=lambda permission, params: True
        )
        self.register_word_capability(service)

        result = service.execute("Office.Word.Create", {})

        self.assertEqual(result.status, ExecutionStatus.APPROVAL_REQUIRED)
        self.handler.execute.assert_not_called()

    def test_denied_approval_blocks_execution(self):
        service = self.make_service(approval=False)
        self.register_word_capability(service)

        result = service.execute("Office.Word.Create", {})

        self.assertEqual(result.status, ExecutionStatus.APPROVAL_DENIED)
        self.handler.execute.assert_not_called()

    def test_execution_requires_successful_verification(self):
        service = self.make_service()
        self.register_word_capability(service)
        self.handler.verify.return_value = False

        result = service.execute("Office.Word.Create", {})

        self.assertEqual(result.status, ExecutionStatus.VERIFICATION_FAILED)

    def test_authorized_execution_and_verification_succeed(self):
        service = self.make_service()
        self.register_word_capability(service)

        result = service.execute("Office.Word.Create", {})

        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        self.assertTrue(result.success)
        self.handler.execute.assert_called_once()
        self.handler.verify.assert_called_once()


if __name__ == "__main__":
    unittest.main()
