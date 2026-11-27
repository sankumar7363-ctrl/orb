"""Desktop handoffs to the user's configured browser and file applications."""

import os
from pathlib import Path
from urllib.parse import urlencode, urlsplit
import webbrowser
import sys


class OpenWebsite:
    """Open an address in the default browser. Does not inspect page contents."""
    name = "Browser.Open"
    permission = "desktop.open_website"
    parameters = {"url": "Complete http or https URL"}

    def permits(self, permission, parameters):
        url = parameters.get("url")
        if permission != self.permission or not isinstance(url, str):
            return False
        try:
            parsed = urlsplit(url)
            return parsed.scheme in ("http", "https") and bool(parsed.hostname) and not parsed.username
        except ValueError:
            return False

    def execute(self, parameters):
        if not webbrowser.open(parameters["url"], new=2):
            raise RuntimeError("Windows could not hand the address to the browser.")
        return True

    def verify(self, parameters, output):
        return output is True


class SearchWeb(OpenWebsite):
    """Open Google search results in the default browser."""
    name = "Browser.Search"
    permission = "desktop.search_web"
    parameters = {"query": "Search text, at most 2000 characters"}

    def permits(self, permission, parameters):
        query = parameters.get("query")
        return (
            permission == self.permission and isinstance(query, str)
            and 0 < len(query.strip()) <= 2000
        )

    def execute(self, parameters):
        url = "https://www.google.com/search?" + urlencode({"q": parameters["query"]})
        return super().execute({"url": url})


class OpenLocalFile:
    """Open an existing local file or folder with its Windows application."""
    name = "File.Open"
    permission = "desktop.open_file"
    parameters = {"path": "Existing absolute file or folder path"}

    def permits(self, permission, parameters):
        value = parameters.get("path")
        if permission != self.permission or not isinstance(value, str):
            return False
        path = Path(value).expanduser()
        return path.is_absolute() and (path.is_file() or path.is_dir())

    def execute(self, parameters):
        if sys.platform != "win32":
            raise NotImplementedError("Opening local files is supported only on Windows.")

        path = Path(parameters["path"]).expanduser().resolve(strict=True)
        os.startfile(str(path))
        return True

    def verify(self, parameters, output):
        return output is True
