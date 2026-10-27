from collections.abc import Sequence
from pathlib import Path


class SatyaApplyError(Exception):
    hint = ""


class DecodeError(SatyaApplyError):
    def __init__(self, path: str, problem: str) -> None:
        super().__init__(f"{path or 'value'} {problem}")
        self.path = path
        self.problem = problem


class ProfileMissingError(SatyaApplyError):
    hint = "Run: satyaapply setup"


class ProfileInvalidError(SatyaApplyError):
    hint = "Fix it in profile.json, or run: satyaapply setup"

    def __init__(self, path: Path, problems: Sequence[str]) -> None:
        super().__init__(f"{path} has problems: " + "; ".join(problems))
        self.problems = tuple(problems)


class DatabaseTooNewError(SatyaApplyError):
    hint = "Update SatyaApply: pip install --upgrade satyaapply"


class ClaudeUnavailableError(SatyaApplyError):
    hint = "Install Claude Code, then run `claude` once to log in."


class AIError(SatyaApplyError):
    pass


class UsageLimitError(AIError):
    hint = "Your Claude usage limit was reached. SatyaApply picks up again on the next run."


class LatexMissingError(SatyaApplyError):
    hint = "Run `satyaapply setup` to install TinyTeX, or install LaTeX yourself."


class LatexFailedError(SatyaApplyError):
    hint = "Check that the resume builds on its own with pdflatex."

    def __init__(self, excerpt: str, missing_file: str | None) -> None:
        super().__init__(f"pdflatex failed: {excerpt}")
        self.excerpt = excerpt
        self.missing_file = missing_file


class ResumeUnreadableError(SatyaApplyError):
    hint = "Use a .tex, .pdf, .docx, .md or .txt resume."


class BrowserUnavailableError(SatyaApplyError):
    hint = "Install Google Chrome, or run: playwright install chromium"


class SetupCancelledError(SatyaApplyError):
    hint = "Run `satyaapply setup` again whenever you're ready."


class RunAlreadyGoingError(SatyaApplyError):
    hint = "Wait for it to finish, or stop it on the tracker's Run page."


class DailyBudgetError(UsageLimitError):
    hint = (
        "Today's Claude call budget is used up, so the run stopped. It picks up again "
        "tomorrow. Change the budget with settings.ai_calls_per_day in profile.json."
    )


class ScheduleError(SatyaApplyError):
    hint = "Run `satyaapply schedule` again, or `satyaapply unschedule` to stop it."


class DataFolderError(SatyaApplyError):
    hint = "Run `satyaapply setup`, or check the folder's owner and permissions."


class DatabaseBrokenError(SatyaApplyError):
    hint = "Move satyaapply.db out of the data folder to start fresh, or restore a backup."


class AppNotBuiltError(SatyaApplyError):
    hint = "Build it once: cd web && npm ci && npm run build"
