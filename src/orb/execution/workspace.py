"""Capabilities for ORB's local workspace."""

import re
from pathlib import Path

from orb.core.constants import USER_DATA_DIRECTORY


def is_workspace_filename(name):
    return isinstance(name, str) and re.fullmatch(
        r"[a-zA-Z0-9_ -]{1,100}\.(?:txt|md|json)", name
    ) is not None


class WorkspaceTextFile:
    """Create and verify a new text file in the ORB workspace."""

    permission = "workspace.create_text"
    name = "File.Write"
    parameters = {
        "path": "New simple workspace filename ending in .txt, .md, or .json",
        "content": "Complete document text, at most 100000 characters",
    }

    def __init__(self, root: Path = USER_DATA_DIRECTORY / "workspace"):
        self.root = root

    def permits(self, permission, parameters):
        name = parameters.get("path")
        content = parameters.get("content")
        return (
            permission == self.permission
            and is_workspace_filename(name)
            and isinstance(content, str)
            and len(content) <= 100_000
        )

    def execute(self, parameters):
        self.root.mkdir(parents=True, exist_ok=True)
        path = self.root / parameters["path"]
        data = parameters["content"].encode("utf-8")
        with path.open("xb") as stream:
            stream.write(data)
        return path

    def verify(self, parameters, output):
        return output.read_bytes() == parameters["content"].encode("utf-8")


class WorkspaceCopyFile:
    """Copy a regular workspace document to a new filename."""

    permission = "workspace.copy_text"
    name = "File.Copy"
    parameters = {
        "source": "Existing simple workspace document filename",
        "path": "New simple workspace filename ending in .txt, .md, or .json",
    }

    def __init__(self, root: Path):
        self.root = root

    def permits(self, permission, parameters):
        return (
            permission == self.permission
            and is_workspace_filename(parameters.get("source"))
            and is_workspace_filename(parameters.get("path"))
        )

    def execute(self, parameters):
        source = self.root / parameters["source"]
        if not source.is_file() or source.resolve().parent != self.root.resolve() or source.is_symlink():
            raise ValueError("The source must be a file in the ORB workspace.")
        with source.open("rb") as stream:
            data = stream.read(400_001)
        if len(data) > 400_000:
            raise ValueError("Workspace documents must be at most 400,000 bytes.")
        path = self.root / parameters["path"]
        with path.open("xb") as stream:
            stream.write(data)
        return path, data

    def verify(self, parameters, output):
        path, expected = output
        return path.read_bytes() == expected
