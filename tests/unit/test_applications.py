import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from orb.execution import ExecutionService, ExecutionStatus
from orb.execution.applications import ApplicationNotInstalledError, OpenApplication
from orb.workflow.engine import WorkflowEngine


def test_open_application_recognizes_aliases_and_rejects_arbitrary_binaries():
    capability = OpenApplication()

    assert capability.permits(capability.permission, {"application": "Excel"})
    assert capability.permits(capability.permission, {"application": "Microsoft Excel"})
    assert capability.permits(capability.permission, {"application": "Brave"})
    assert capability.permits(capability.permission, {"application": "Brave Browser"})
    assert capability.permits(capability.permission, {"application": "Notepad"})
    assert not capability.permits(capability.permission, {"application": "powershell"})
    assert not capability.permits(capability.permission, {"application": "cmd.exe"})


def test_unrecognized_application_is_denied_before_discovery():
    capability = OpenApplication()
    service = ExecutionService(permission_checker=capability.permits)
    service.register_capability(
        capability.name,
        capability,
        required_permission=capability.permission,
        requires_approval=False,
    )

    result = service.execute("App.Open", {"application": "powershell"})
    assert result.status is ExecutionStatus.PERMISSION_DENIED


def test_recognized_but_not_installed_application_reports_not_available_without_needs_review(tmp_path):
    capability = OpenApplication()
    service = ExecutionService(permission_checker=capability.permits)
    service.register_capability(
        capability.name,
        capability,
        required_permission=capability.permission,
        requires_approval=False,
    )
    ai = Mock()
    engine = WorkflowEngine(ai, service)

    with patch.object(
        capability,
        "executable",
        side_effect=ApplicationNotInstalledError("brave is recognized, but it is not installed on this system."),
    ):
        assert not engine.run("Open Brave")

    assert engine.current_plan is not None
    assert engine.current_plan.status == "failed"
    assert engine.current_plan.steps[0].execution_status == ExecutionStatus.NOT_AVAILABLE.value
    assert "not installed" in (engine.current_plan.steps[0].error or "")


def test_executable_discovery_expands_env_vars_and_checks_vendor_dirs(tmp_path, monkeypatch):
    if sys.platform != "win32":
        pytest.skip("Windows-specific executable discovery")

    brave_dir = tmp_path / "BraveSoftware" / "Brave-Browser" / "Application"
    brave_dir.mkdir(parents=True)
    brave_exe = brave_dir / "brave.exe"
    brave_exe.write_bytes(b"")

    capability = OpenApplication()
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path / "missing86"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "missinglocal"))

    with patch("winreg.OpenKey", side_effect=OSError("missing key")), patch("shutil.which", return_value=None):
        found = capability.executable("Brave")

    assert found == brave_exe


def test_application_launch_uses_shell_false_and_verifies_process(tmp_path):
    exe_path = tmp_path / "brave.exe"
    exe_path.write_bytes(b"")
    capability = OpenApplication()
    service = ExecutionService(permission_checker=capability.permits)
    service.register_capability(
        capability.name,
        capability,
        required_permission=capability.permission,
        requires_approval=False,
    )

    running_proc = Mock()
    running_proc.wait.side_effect = subprocess.TimeoutExpired(cmd=str(exe_path), timeout=0.5)

    with (
        patch.object(capability, "executable", return_value=exe_path),
        patch("subprocess.Popen", return_value=running_proc) as popen,
    ):
        result = service.execute("App.Open", {"application": "brave"})

    assert result.success
    popen.assert_called_once_with([str(exe_path)], shell=False)

    failed_proc = Mock()
    failed_proc.wait.return_value = 1
    with (
        patch.object(capability, "executable", return_value=exe_path),
        patch("subprocess.Popen", return_value=failed_proc),
    ):
        failed = service.execute("App.Open", {"application": "brave"})

    assert failed.status is ExecutionStatus.VERIFICATION_FAILED
