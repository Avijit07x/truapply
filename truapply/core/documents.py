from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ResumeFormat(StrEnum):
    LATEX = "latex"
    STRUCTURED = "structured"


@dataclass(frozen=True)
class ResumeDocument:
    path: Path
    text: str | None

    @property
    def needs_reading(self) -> bool:
        return self.text is None


@dataclass(frozen=True)
class ResumeEntry:
    heading: str
    subheading: str
    dates: str
    location: str
    bullets: tuple[str, ...]


@dataclass(frozen=True)
class ResumeSection:
    title: str
    lines: tuple[str, ...]
    entries: tuple[ResumeEntry, ...]


@dataclass(frozen=True)
class ResumeData:
    name: str
    headline: str
    contact: tuple[str, ...]
    sections: tuple[ResumeSection, ...]

    def as_lines(self) -> list[str]:
        lines = [self.name, self.headline, " | ".join(self.contact)]
        for section in self.sections:
            lines.append(section.title.upper())
            lines.extend(section.lines)
            for entry in section.entries:
                lines.append(
                    " | ".join(
                        filter(None, (entry.heading, entry.subheading, entry.dates, entry.location))
                    )
                )
                lines.extend(f"- {bullet}" for bullet in entry.bullets)
        return lines
