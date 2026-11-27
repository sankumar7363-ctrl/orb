"""Launch installed Windows desktop applications by registered name."""

import os
import shutil
import subprocess
import sys
from pathlib import Path


class ApplicationNotInstalledError(FileNotFoundError):
    """Raised when a recognized application is not installed on this system."""


class OpenApplication:
    """Open a supported Windows application."""

    name = "App.Open"
    permission = "desktop.open_application"
    applications = {
        "excel": "excel.exe",
        "word": "winword.exe",
        "powerpoint": "powerpnt.exe",
        "vs code": "Code.exe",
        "chrome": "chrome.exe",
        "brave": "brave.exe",
        "edge": "msedge.exe",
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "file explorer": "explorer.exe",
    }
    aliases = {
        "microsoft excel": "excel",
        "ms excel": "excel",
        "microsoft word": "word",
        "ms word": "word",
        "microsoft powerpoint": "powerpoint",
        "ms powerpoint": "powerpoint",
        "vscode": "vs code",
        "visual studio code": "vs code",
        "google chrome": "chrome",
        "brave browser": "brave",
        "microsoft edge": "edge",
        "ms edge": "edge",
        "calc": "calculator",
        "explorer": "file explorer",
        "file manager": "file explorer",
        "windows explorer": "file explorer",
    }
    _SYSTEM_EXECUTABLES = frozenset({"explorer.exe", "notepad.exe", "calc.exe"})
    _INSTALL_DIRECTORIES = {
        "Code.exe": (Path("Programs/Microsoft VS Code"), Path("Microsoft VS Code")),
        "chrome.exe": (Path("Google/Chrome/Application"),),
        "brave.exe": (Path("BraveSoftware/Brave-Browser/Application"),),
        "msedge.exe": (Path("Microsoft/Edge/Application"),),
        "excel.exe": (
            Path("Microsoft Office/root/Office16"),
            Path("Microsoft Office/Office16"),
            Path("Microsoft Office/root/Office15"),
            Path("Microsoft Office/Office15"),
        ),
        "winword.exe": (
            Path("Microsoft Office/root/Office16"),
            Path("Microsoft Office/Office16"),
            Path("Microsoft Office/root/Office15"),
            Path("Microsoft Office/Office15"),
        ),
        "powerpnt.exe": (
            Path("Microsoft Office/root/Office16"),
            Path("Microsoft Office/Office16"),
            Path("Microsoft Office/root/Office15"),
            Path("Microsoft Office/Office15"),
        ),
    }
    parameters = {"application": ", ".join(applications)}

    @classmethod
    def canonical_name(cls, application: str) -> str:
        name = " ".join(application.lower().split())
        return cls.aliases.get(name, name)

    @classmethod
    def is_recognized(cls, application: object) -> bool:
        return isinstance(application, str) and cls.canonical_name(application) in cls.applications

    def is_installed(self, application: str) -> bool:
        """Return True if a recognized application's executable is found."""
        if not self.is_recognized(application):
            return False
        try:
            self.executable(application)
            return True
        except ApplicationNotInstalledError:
            return False

    def permits(self, permission, parameters):
        return (
            permission == self.permission
            and self.is_recognized(parameters.get("application"))
        )

    def executable(self, application: str) -> Path:
        if sys.platform != "win32":
            raise NotImplementedError("App.Open is supported only on Windows.")

        if not self.is_recognized(application):
            raise ValueError(f"Unrecognized application: {application}")

        canonical = self.canonical_name(application)
        executable = self.applications[canonical]

        if executable in self._SYSTEM_EXECUTABLES:
            if system_root := os.environ.get("SystemRoot"):
                for folder in (Path(system_root), Path(system_root) / "System32"):
                    candidate = folder / executable
                    if candidate.is_file():
                        return candidate

        import winreg

        key = rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{executable}"
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
                try:
                    with winreg.OpenKey(hive, key, 0, winreg.KEY_READ | view) as entry:
                        value, _ = winreg.QueryValueEx(entry, None)
                    if isinstance(value, str) and value.strip():
                        expanded = os.path.expandvars(value.strip().strip('"'))
                        path = Path(expanded)
                        if path.is_file():
                            return path
                except OSError:
                    continue

        for relative_dir in self._INSTALL_DIRECTORIES.get(executable, ()):
            for variable in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
                if root := os.getenv(variable):
                    path = Path(root) / relative_dir / executable
                    if path.is_file():
                        return path

        if found := shutil.which(executable):
            path = Path(found)
            if path.is_file():
                return path

        raise ApplicationNotInstalledError(
            f"{canonical} is recognized, but it is not installed on this system."
        )

    def execute(self, parameters):
        executable = self.executable(parameters["application"])
        if executable.name.lower() == "explorer.exe":
            # The shell may reuse an existing Explorer process.
            os.startfile(str(executable))
            return True
        return subprocess.Popen([str(executable)], shell=False)

    def verify(self, parameters, output):
        if self.canonical_name(parameters["application"]) == "file explorer":
            return output is True
        if output is None:
            return False
        try:
            code = output.wait(timeout=0.5)
            return code == 0
        except subprocess.TimeoutExpired:
            return True