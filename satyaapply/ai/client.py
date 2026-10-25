import json
import logging
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TypeVar

from satyaapply.core.codec import decode, json_schema
from satyaapply.core.errors import AIError, ClaudeUnavailableError, DecodeError, UsageLimitError

T = TypeVar("T")

TIMEOUT_S = 300
ATTEMPTS = 2
ERROR_EXCERPT_CHARS = 300
USAGE_LIMIT_MARKERS = ("usage limit", "rate limit", "limit reached", "quota")
AUTH_MARKERS = ("/login", "not logged in", "invalid api key", "authentication", "oauth")

log = logging.getLogger(__name__)


class Model(StrEnum):
    HAIKU = "haiku"
    SONNET = "sonnet"


@dataclass(frozen=True)
class Request:
    prompt: str
    system: str
    model: Model = Model.SONNET
    tools: tuple[str, ...] = ()
    attachments: tuple[Path, ...] = ()


def command(binary: str, request: Request, schema: dict[str, object]) -> list[str]:
    return [
        binary,
        "-p",
        "--safe-mode",
        "--strict-mcp-config",
        "--no-session-persistence",
        "--permission-prompts",
        "none",
        "--output-format",
        "json",
        "--model",
        request.model,
        "--tools",
        ",".join(request.tools),
        *(["--allowedTools", ",".join(request.tools)] if request.tools else []),
        "--system-prompt",
        request.system,
        "--json-schema",
        json.dumps(schema),
    ]


Failure = AIError | ClaudeUnavailableError


def _failure(text: str) -> Failure:
    lowered = text.lower()
    excerpt = text.strip()[:ERROR_EXCERPT_CHARS]
    if any(marker in lowered for marker in USAGE_LIMIT_MARKERS):
        return UsageLimitError(excerpt)
    if any(marker in lowered for marker in AUTH_MARKERS):
        return ClaudeUnavailableError(f"Claude Code isn't logged in: {excerpt}")
    return AIError(excerpt or "Claude returned nothing")


def parse(stdout: str, stderr: str) -> dict[str, object]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        raise _failure(stderr or stdout) from None
    if not isinstance(payload, dict):
        raise AIError("Claude's reply wasn't a JSON object")
    if payload.get("is_error"):
        raise _failure(str(payload.get("result", "")))
    structured = payload.get("structured_output")
    if not isinstance(structured, dict):
        raise AIError("Claude didn't return structured output")
    return structured


def _run(request: Request, schema: dict[str, object]) -> dict[str, object]:
    binary = shutil.which("claude")
    if binary is None:
        raise ClaudeUnavailableError("Claude Code (`claude`) isn't installed.")
    with tempfile.TemporaryDirectory(prefix="satyaapply-ai-") as sandbox:
        for attachment in request.attachments:
            shutil.copy2(attachment, Path(sandbox) / attachment.name)
        try:
            completed = subprocess.run(  # noqa: S603
                command(binary, request, schema),
                input=request.prompt,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_S,
                cwd=sandbox,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise AIError(f"Claude didn't answer within {TIMEOUT_S} s") from None
    return parse(completed.stdout, completed.stderr)


def ask(reply_type: type[T], request: Request) -> T:
    schema = json_schema(reply_type)
    for attempt in range(1, ATTEMPTS + 1):
        try:
            return decode(reply_type, _run(request, schema))
        except UsageLimitError:
            raise
        except (AIError, DecodeError) as error:
            if attempt == ATTEMPTS:
                raise AIError(f"Claude's reply was unusable: {error}") from error
            log.warning("retrying after unusable Claude reply: %s", error)
    raise AssertionError
