import os
from dataclasses import dataclass
from pathlib import Path

HOME_ENV = "SATYAAPPLY_HOME"
DEFAULT_HOME = "~/.satyaapply"
PRIVATE_DIR_MODE = 0o700


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def profile(self) -> Path:
        return self.root / "profile.json"

    @property
    def database(self) -> Path:
        return self.root / "satyaapply.db"

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

    @property
    def shots(self) -> Path:
        return self.root / "shots"

    def job_dir(self, job_id: int) -> Path:
        return self.resumes / str(job_id)

    @property
    def browser(self) -> Path:
        return self.root / "browser"

    @property
    def log(self) -> Path:
        return self.root / "run.log"

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.root.chmod(PRIVATE_DIR_MODE)
        self.resume_dir.mkdir(exist_ok=True)


def default_paths() -> Paths:
    return Paths(Path(os.environ.get(HOME_ENV, DEFAULT_HOME)).expanduser())
