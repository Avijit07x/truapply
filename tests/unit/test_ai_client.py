import json
from dataclasses import dataclass

import pytest

from satyaapply.ai import client
from satyaapply.ai.client import Model, Request, ask, command, parse
from satyaapply.core.errors import AIError, ClaudeUnavailableError, UsageLimitError

REQUEST = Request(prompt="hi", system="be safe", model=Model.HAIKU)


@dataclass(frozen=True)
class Answer:
    value: int


def reply(structured: object, **extra: object) -> str:
    return json.dumps({"is_error": False, "structured_output": structured, **extra})


def test_every_call_is_locked_down() -> None:
    args = command("/bin/claude", REQUEST, {"type": "object"})
    for flag in ("--safe-mode", "--strict-mcp-config", "--no-session-persistence"):
        assert flag in args
    assert args[args.index("--tools") + 1] == ""
    assert args[args.index("--permission-prompts") + 1] == "none"
    assert args[args.index("--model") + 1] == "claude-haiku-5-5"


def test_tools_are_passed_only_when_asked_for() -> None:
    args = command("/bin/claude", Request("hi", "s", tools=("Read",)), {})
    assert args[args.index("--tools") + 1] == "Read"


def test_structured_output_is_returned() -> None:
    assert parse(reply({"value": 3}), "") == {"value": 3}


def test_usage_limit_is_recognised() -> None:
    payload = json.dumps({"is_error": True, "result": "Claude AI usage limit reached|1793000000"})
    with pytest.raises(UsageLimitError):
        parse(payload, "")


def test_logged_out_claude_is_recognised() -> None:
    with pytest.raises(ClaudeUnavailableError):
        parse("", "Invalid API key · Please run /login")


def test_reply_without_structured_output_is_rejected() -> None:
    with pytest.raises(AIError, match="structured output"):
        parse(json.dumps({"is_error": False, "result": "sure!"}), "")


def test_an_unusable_reply_is_retried_once(monkeypatch: pytest.MonkeyPatch) -> None:
    replies = iter([{"value": "three"}, {"value": 3}])
    monkeypatch.setattr(client, "_run", lambda _request, _schema: next(replies))
    assert ask(Answer, REQUEST) == Answer(3)


def test_two_unusable_replies_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(client, "_run", lambda _request, _schema: {"value": "three"})
    with pytest.raises(AIError, match="unusable"):
        ask(Answer, REQUEST)


def test_usage_limit_is_never_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    def limited(_request: Request, _schema: dict[str, object]) -> dict[str, object]:
        calls.append(1)
        raise UsageLimitError("limit")

    monkeypatch.setattr(client, "_run", limited)
    with pytest.raises(UsageLimitError):
        ask(Answer, REQUEST)
    assert len(calls) == 1


def test_missing_claude_binary_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("satyaapply.ai.client.shutil.which", lambda _name: None)
    with pytest.raises(ClaudeUnavailableError, match="isn't installed"):
        ask(Answer, REQUEST)
