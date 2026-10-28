import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

HOME_ENV = "TRUAPPLY_HOME"
DEFAULT_HOME = "~/.truapply"
PRIVATE_DIR_MODE = 0o700
RUN_LOG_STAMP = "%Y%m%d-%H%M%S-%f"
AUTOMATIC_RUN = "Automatic run"
MANUAL_RUN = "Manual run"


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def profile(self) -> Path:
        return self.root / "profile.json"

    @property
    def database(self) -> Path:
        return self.root / "truapply.db"

    @property
    def resume_dir(self) -> Path:
        return self.root / "resume"

    @property
    def master_pdf(self) -> Path:
        return self.resume_dir / "master.pdf"

    @property
    def master_pdf_meta(self) -> Path:
        return self.resume_dir / "master.pdf.json"

    @property
    def previews(self) -> Path:
        return self.root / "previews"

    @property
    def resumes(self) -> Path:
        return self.root / "resumes"

    def job_dir(self, job_id: int) -> Path:
        return self.resumes / str(job_id)

    @property
    def log(self) -> Path:
        return self.root / "run.log"

    @property
    def lock(self) -> Path:
        return self.root / "run.lock"

    @property
    def runs(self) -> Path:
        return self.root / "runs"

    def run_log(self, started: datetime) -> Path:
        return self.runs / f"{started.strftime(RUN_LOG_STAMP)}.log"

    @property
    def summaries(self) -> Path:
        return self.root / "summaries"

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.root.chmod(PRIVATE_DIR_MODE)
        self.resume_dir.mkdir(exist_ok=True)


def default_paths() -> Paths:
    return Paths(Path(os.environ.get(HOME_ENV, DEFAULT_HOME)).expanduser())
