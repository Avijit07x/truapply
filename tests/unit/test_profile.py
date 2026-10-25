import json
import stat
from dataclasses import replace
from pathlib import Path

import pytest

from satyaapply.core.codec import encode
from satyaapply.core.errors import ProfileInvalidError, ProfileMissingError
from satyaapply.core.paths import Paths
from satyaapply.core.profile import Salary, Settings, load, problems, save
from tests.unit import samples


@pytest.fixture
def paths(tmp_path: Path) -> Paths:
    home = Paths(tmp_path / "home")
    home.ensure()
    return home


@pytest.fixture
def resume(paths: Paths) -> Path:
    path = paths.resume_dir / "master.tex"
    path.write_text("\\begin{document}x\\end{document}")
    return path


def test_saved_profile_loads_back_identical(paths: Paths, resume: Path) -> None:
    profile = samples.profile(resume)
    save(paths, profile)
    assert load(paths) == profile


def test_profile_file_is_private(paths: Paths, resume: Path) -> None:
    save(paths, samples.profile(resume))
    assert stat.S_IMODE(paths.profile.stat().st_mode) == 0o600
    assert stat.S_IMODE(paths.root.stat().st_mode) == 0o700


def test_missing_profile_says_to_run_setup(paths: Paths) -> None:
    with pytest.raises(ProfileMissingError):
        load(paths)


def test_broken_json_is_reported_with_its_line(paths: Paths) -> None:
    paths.profile.write_text("{\n  oops\n}")
    with pytest.raises(ProfileInvalidError, match="line 2"):
        load(paths)


def test_a_typo_in_a_field_name_is_caught(paths: Paths, resume: Path) -> None:
    raw = encode(samples.profile(resume))
    assert isinstance(raw, dict)
    raw["settings"] = {"min_scroe": 70}
    paths.profile.write_text(json.dumps(raw))
    with pytest.raises(ProfileInvalidError, match=r"settings\.min_scroe is not a known field"):
        load(paths)


def test_inverted_salary_range_is_a_problem(resume: Path) -> None:
    profile = replace(samples.profile(resume), salary=Salary("INR", 20, 10, None))
    assert "salary: need 0 < expected_min <= expected_max" in problems(profile)


def test_min_score_above_strong_score_is_a_problem(resume: Path) -> None:
    profile = replace(samples.profile(resume), settings=Settings(min_score=90, strong_score=80))
    assert any("min_score" in problem for problem in problems(profile))


def test_invalid_profile_is_never_saved(paths: Paths, resume: Path) -> None:
    with pytest.raises(ProfileInvalidError):
        save(paths, replace(samples.profile(resume), roles=()))
    assert not paths.profile.exists()
