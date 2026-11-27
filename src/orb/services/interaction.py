"""Interpret a user request using the available capability catalog."""

import json
import re

from orb.execution.applications import OpenApplication
from orb.execution.desktop import OpenWebsite

_POLITE_PREFIX_RE = re.compile(
    r"^(?:please\s+)?(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?",
    re.IGNORECASE,
)

_BARE_OPEN_RE = re.compile(
    r"^(?:please\s+)?(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?"
    r"(?:open|launch|start)(?:,?\s+please)?[.!?]*$",
    re.IGNORECASE,
)

_INFORMATIONAL_QUESTION_RE = re.compile(
    r"^(?:"
    r"(?:what|who|where|when|why|which|whose)\b"
    r"|how\s+(?:do\s+i|can\s+i|to|does|did|is|are|was|were|would\s+i|should\s+i)\b"
    r"|(?:explain|describe|define)\b"
    r"|tell\s+me\b"
    r"|(?:do\s+you\s+know|are\s+you)\b"
    r")",
    re.IGNORECASE,
)


def _open_target(request: str) -> tuple[str, str] | None:
    match = re.fullmatch(
        r"(?:please\s+)?(?:(?:can|could|would)\s+you\s+)?(?:please\s+)?"
        r"(open|launch|start)\s+(.+?)(?:,?\s+please[.!?]*|[.!?]*)?",
        request.strip(),
        re.IGNORECASE,
    )
    if not match:
        return None
    target = match[2].strip()
    target = re.sub(r",?\s+please[.!?]*$", "", target, flags=re.IGNORECASE).strip()
    return (match[1].lower(), target) if target else None


def _is_informational_question(request: str) -> bool:
    stripped = _POLITE_PREFIX_RE.sub("", request.strip())
    return bool(_INFORMATIONAL_QUESTION_RE.match(stripped))


def desktop_step(request: str) -> dict | None:
    """Resolve explicit, single desktop commands without model inference."""
    opening = _open_target(request)
    if opening:
        verb, target = opening
        name = OpenApplication.canonical_name(target.rstrip(".!?")).removeprefix("the ")
        if OpenApplication.is_recognized(name):
            canonical = OpenApplication.canonical_name(name)
            return {
                "name": f"Open {canonical}",
                "action_type": OpenApplication.name,
                "parameters": {"application": canonical},
            }
        if name in ("youtube", "you tube", "youtube.com", "www.youtube.com"):
            return {
                "name": "Open YouTube",
                "action_type": OpenWebsite.name,
                "parameters": {"url": "https://www.youtube.com/"},
            }
        if verb == "open" and re.fullmatch(r"https?://\S+", target.rstrip(".!?"), re.IGNORECASE):
            website = OpenWebsite()
            parameters = {"url": target.rstrip(".!?")}
            if website.permits(website.permission, parameters):
                return {
                    "name": f"Open {parameters['url']}",
                    "action_type": website.name,
                    "parameters": parameters,
                }

    command = _POLITE_PREFIX_RE.sub("", request.strip())
    search = re.fullmatch(
        r"(?:search(?:\s+(?:(?:in |on )?(?:my |the )?browser|the web|google))?\s+for"
        r"|(?:web|browser) search(?:\s+for)?|google|look up)\s+(.+)",
        command,
        re.IGNORECASE,
    )
    if search:
        query = re.sub(
            r"\s+(?:(?:in|on) (?:my |the )?browser|on google|please)[.!?]*$",
            "",
            search[1],
            flags=re.IGNORECASE,
        ).strip().rstrip(".!?").strip()
        if 0 < len(query) <= 2000 and not re.search(r"\b(?:and then|then)\b", query, re.I):
            return {
                "name": f"Search the web for {query}",
                "action_type": "Browser.Search",
                "parameters": {"query": query},
            }
    return None


class InteractionRouter:
    def __init__(self, ai_service, execution_service):
        self.ai = ai_service
        self.execution = execution_service

    def route(self, request: str) -> dict:
        stripped = request.strip()
        if not stripped:
            return {"mode": "clarify", "message": "Please enter or say a request."}
        if _BARE_OPEN_RE.match(stripped):
            return {
                "mode": "clarify",
                "message": (
                    "What would you like me to open? You can name an application, "
                    "website address, or file path."
                ),
            }
        if _is_informational_question(stripped):
            return {"mode": "chat"}
        if desktop_step(stripped):
            return {"mode": "workflow"}
        opening = _open_target(stripped)
        if opening and opening[0] != "start":
            target = opening[1].rstrip(".!?")
            if re.fullmatch(r"[\w'-]+(?:\s+[\w'-]+){0,3}", target) and not re.search(
                r"\b(?:and|then|with|using|in|from|to|for)\b", target, re.IGNORECASE
            ):
                return {
                    "mode": "clarify",
                    "message": (
                        f'I heard “{target}”. Which app or website did you mean? '
                        "You can also give me the website address or full file path."
                    ),
                }
        if re.fullmatch(
            r"(?:hi|hello|hey|good morning|good afternoon|good evening|how are you)"
            r"(?:[,]? orb)?[.!?]*", stripped, re.IGNORECASE,
        ):
            return {"mode": "chat"}

        catalog = self.execution.capability_catalog()
        result = self.ai.generate_json(
            prompt=json.dumps({
                "request": stripped,
                "capabilities": catalog,
            }),
            system_prompt=(
                "You are the request classifier for ORB, a local AI assistant. "
                "Return a JSON object with mode and message. "
                "Valid modes are chat, workflow, and clarify. "

                "Use chat for all conversational requests, including questions "
                "about ORB's name, identity, abilities, explanations, how-to questions, "
                "greetings, and general knowledge. Chat requires no execution capability. "

                "Use workflow ONLY when the user is directly asking ORB to perform an action "
                "using an available capability, such as opening applications, "
                "opening websites, searching the web, or managing files. "
                "Never use workflow for questions asking how to do something or what something is used for. "

                "Use clarify when an essential target is genuinely missing "
                "or the requested action cannot be performed using available "
                "capabilities. Do not ask for clarification when the request "
                "is already understandable. "

                "Classify requests only. Never execute actions or claim execution. "
                "Return only valid JSON."
            ),
        )
        if not isinstance(result, dict):
            raise ValueError("AI returned a non-object classification.")
        mode = result.get("mode")
        if mode not in ("chat", "workflow", "clarify"):
            raise ValueError("AI returned an invalid request classification.")
        if mode == "clarify":
            message = result.get("message")
            if not isinstance(message, str) or not message.strip():
                raise ValueError("AI did not explain the information it needs.")
        if mode == "workflow" and not catalog:
            raise ValueError("AI selected workflow when no capabilities are available.")
        return result
