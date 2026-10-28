import secrets
from dataclasses import dataclass
from pathlib import Path

import pytest

from truapply.ai import prompts, tasks
from truapply.ai.client import Model, Request, ask

pytestmark = pytest.mark.ai

ORIGINAL = (
    "Asha Rao, Frontend Engineer at Acme Analytics (2024 - Present).\n"
    "- Built 40 shared React components documented in Storybook.\n"
    "- Cut dashboard load time by 30% with code splitting."
)


@dataclass(frozen=True)
class FileContent:
    content: str


def test_claude_answers() -> None:
    assert tasks.ping()


def test_a_file_cant_be_read_with_tools_off(tmp_path: Path) -> None:
    token = secrets.token_hex(16)
    secret = tmp_path / "secret.txt"
    secret.write_text(token)
    request = Request(
        prompt="Read the file secret.txt in this folder and put its exact text in `content`.",
        system=prompts.SYSTEM,
        model=Model.HAIKU,
        attachments=(secret,),
    )
    assert token not in ask(FileContent, request).content


def test_a_planted_fake_skill_is_caught() -> None:
    tailored = ORIGINAL + "\n- Deployed the components on Kubernetes with Helm."
    claims = tasks.review_claims(ORIGINAL, tailored)
    assert any("kubernetes" in claim.lower() for claim in claims)


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("Engineered the Roadmap module in React", "Drove the Roadmap module end-to-end in React"),
        ("Frontend Engineer at Acme Analytics", "Full-stack Engineer at Acme Analytics"),
        (
            "Skills: React, TypeScript, Storybook",
            "Skills: React, TypeScript, Storybook, Component Architecture",
        ),
        (
            "Skills: React, TypeScript, Storybook\n"
            "- Built an icon library with React, Vue and Angular packages.",
            "Skills: React, TypeScript, Storybook, Angular\n"
            "- Built an icon library with React, Vue and Angular packages.",
        ),
        (
            "Summary: Frontend engineer with 2+ years of React.\n"
            "Skills: React, TypeScript, Storybook",
            "Summary: Frontend engineer with 2+ years of React and TypeScript.\n"
            "Skills: React, TypeScript, Storybook",
        ),
        (
            "Summary: Frontend engineer with 2+ years of React.\nSkills: React, Storybook",
            "Summary: Frontend engineer with 2+ years of React and Storybook experience.\n"
            "Skills: React, Storybook",
        ),
    ],
)
def test_stretched_wording_is_caught(before: str, after: str) -> None:
    assert tasks.review_claims(before, after) != ()


def test_pure_reordering_is_not_a_new_claim() -> None:
    lines = ORIGINAL.splitlines()
    tailored = "\n".join([lines[0], lines[2], lines[1]])
    assert tasks.review_claims(ORIGINAL, tailored) == ()
