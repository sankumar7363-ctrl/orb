"""Bounded context from the project folder selected by the user."""

from pathlib import Path


class ProjectContext:
    def __init__(self):
        self.root: Path | None = None

    def select(self, directory: str):
        path = Path(directory).resolve(strict=True)
        if not path.is_dir():
            raise ValueError("Choose a project directory.")
        self.root = path

    def snapshot(self) -> dict:
        if self.root is None:
            return {}
        files = []
        for index, path in enumerate(self.root.iterdir()):
            if index >= 200:
                break
            if not path.name.startswith(".") and not path.is_symlink():
                files.append(path.name)
        documents = {}
        for name in ("README.md", "pyproject.toml", "package.json"):
            path = self.root / name
            if path.is_file() and not path.is_symlink():
                with path.open("r", encoding="utf-8", errors="replace") as stream:
                    documents[name] = stream.read(6000)
        return {"directory": str(self.root), "entries": sorted(files), "documents": documents}
