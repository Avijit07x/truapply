from dataclasses import replace
from pathlib import Path

import pytest

from satyaapply.ai import tasks
from tests.ai.test_live_jobs import RESUME
from tests.unit import samples

pytestmark = pytest.mark.ai

STAFFING_JOB = (
    "Frontend Engineer, React and TypeScript, Bengaluru (hybrid). 2-4 years of experience.\n"
    "About us: TalentBridge is a staffing and recruitment agency. We are hiring this role on "
    "behalf of our client, a fintech company. You will be employed on our payroll and placed "
    "with the client on a 12-month contract."
)
NO_AGENCIES = "No staffing or recruitment agencies"


def test_a_no_agencies_rule_lowers_the_score_of_an_agency_job(tmp_path: Path) -> None:
    profile = samples.profile(tmp_path / "master.tex")
    job = replace(
        samples.job(), company="TalentBridge", description=STAFFING_JOB, location="Bengaluru"
    )
    plain = tasks.score_job(profile, RESUME, job)
    ruled = tasks.score_job(profile, RESUME, job, (NO_AGENCIES,))
    assert ruled.score < plain.score
    assert ruled.dealbreaker or ruled.score < profile.settings.min_score
