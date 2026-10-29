from collections.abc import Sequence
from pathlib import Path


class TruApplyError(Exception):
    hint = ""


class DecodeError(TruApplyError):
    def __init__(self, path: str, problem: str) -> None:
        super().__init__(f"{path or 'value'} {problem}")
        self.path = path
        self.problem = problem


class ProfileMissingError(TruApplyError):
    hint = "Run: truapply setup"


class ProfileInvalidError(TruApplyError):
    hint = "Fix it in profile.json, or run: truapply setup"

    def __init__(self, path: Path, problems: Sequence[str]) -> None:
        super().__init__(f"{path} has problems: " + "; ".join(problems))
        self.problems = tuple(problems)


class DatabaseTooNewError(TruApplyError):
    hint = "Update TruApply: pip install --upgrade truapply"


class ClaudeUnavailableError(TruApplyError):
    hint = "Install Claude Code, then run `claude` once to log in."


class AIError(TruApplyError):
    pass


class UsageLimitError(AIError):
    hint = "Your Claude usage limit was reached. TruApply picks up again on the next run."


class LatexMissingError(TruApplyError):
    hint = "Run `truapply setup` to install TinyTeX, or install LaTeX yourself."


class LatexFailedError(TruApplyError):
    hint = "Check that the resume builds on its own with pdflatex."

    def __init__(self, excerpt: str, missing_file: str | None) -> None:
        super().__init__(f"pdflatex failed: {excerpt}")
        self.excerpt = excerpt
        self.missing_file = missing_file


class ResumeUnreadableError(TruApplyError):
    hint = "Use a .tex, .pdf, .docx, .md or .txt resume."


class BrowserUnavailableError(TruApplyError):
    hint = "Install Google Chrome, or run: playwright install chromium"


class SetupCancelledError(TruApplyError):
    hint = "Run `truapply setup` again whenever you're ready."


class RunAlreadyGoingError(TruApplyError):
    hint = "Wait for it to finish, or stop it on the tracker's Run page."


class ArchiveCheckGoingError(TruApplyError):
    hint = "Wait for it to finish; new companies show on the tracker's Companies page."


class DailyBudgetError(UsageLimitError):
    hint = (
        "The run stopped and picks up again tomorrow. To allow more, change Settings → "
        "Applying → Claude calls per day."
    )


class ScheduleError(TruApplyError):
    hint = "Run `truapply schedule` again, or `truapply unschedule` to stop it."


class DataFolderError(TruApplyError):
    hint = "Run `truapply setup`, or check the folder's owner and permissions."


class DatabaseBrokenError(TruApplyError):
    hint = "Move truapply.db out of the data folder to start fresh, or restore a backup."


class AppNotBuiltError(TruApplyError):
    hint = "Build it once: cd web && npm ci && npm run build"
