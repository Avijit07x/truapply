import json
from collections.abc import Sequence
from dataclasses import dataclass
from html import escape
from importlib import resources
from pathlib import Path

from satyaapply.ai.tasks import revise_structured, rewrite_structured
from satyaapply.browser.pdf import print_html
from satyaapply.core.codec import decode, encode
from satyaapply.core.documents import ResumeData, ResumeEntry
from satyaapply.core.models import Job
from satyaapply.resume.contract import Draft, Rendered


def to_json(data: ResumeData) -> str:
    return json.dumps(encode(data), indent=2, ensure_ascii=False)


def from_json(source: str) -> ResumeData:
    return decode(ResumeData, json.loads(source))


def _entry_html(entry: ResumeEntry) -> str:
    bullets = "".join(f"<li>{escape(bullet)}</li>" for bullet in entry.bullets)
    return (
        "<article>"
        f"<div class='row'><strong>{escape(entry.heading)}</strong>"
        f"<span>{escape(entry.dates)}</span></div>"
        f"<div class='row sub'><em>{escape(entry.subheading)}</em>"
        f"<span>{escape(entry.location)}</span></div>"
        f"{f'<ul>{bullets}</ul>' if bullets else ''}"
        "</article>"
    )


def to_html(data: ResumeData) -> str:
    style = resources.files("satyaapply.resume").joinpath("style.css").read_text("utf-8")
    sections = "".join(
        f"<section><h2>{escape(section.title)}</h2>"
        + "".join(f"<p>{escape(line)}</p>" for line in section.lines)
        + "".join(_entry_html(entry) for entry in section.entries)
        + "</section>"
        for section in data.sections
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{escape(data.name)}</title><style>{style}</style></head><body>"
        f"<header><h1>{escape(data.name)}</h1>"
        f"<p class='contact'>{' · '.join(escape(item) for item in data.contact)}</p>"
        f"<p class='headline'>{escape(data.headline)}</p></header>"
        f"{sections}</body></html>"
    )


def _headings(data: ResumeData) -> set[str]:
    return {entry.heading for section in data.sections for entry in section.entries}


@dataclass(frozen=True)
class StructuredResume:
    data: ResumeData
    suffix: str = ".json"

    @property
    def source(self) -> str:
        return to_json(self.data)

    def readable(self, source: str) -> str:
        return "\n".join(from_json(source).as_lines())

    def draft(self, job: Job, notes: Sequence[str]) -> Draft:
        rewrite = rewrite_structured(self.data, job, notes)
        return Draft(to_json(rewrite.resume), rewrite.changes)

    def revise(self, draft: Draft, problems: Sequence[str]) -> Draft:
        rewrite = revise_structured(self.data, from_json(draft.source), problems)
        return Draft(to_json(rewrite.resume), rewrite.changes)

    def problems(self, draft: Draft) -> list[str]:
        tailored = from_json(draft.source)
        problems = []
        if (tailored.name, tailored.contact) != (self.data.name, self.data.contact):
            problems.append("the name or contact details changed")
        removed = sorted(_headings(self.data) - _headings(tailored))
        added = sorted(_headings(tailored) - _headings(self.data))
        if removed:
            problems.append("removed entries: " + ", ".join(removed))
        if added:
            problems.append("new entries: " + ", ".join(added))
        return problems

    def render(self, source: str, target: Path) -> Rendered:
        return Rendered(target, print_html(to_html(from_json(source)), target))
