import re

SUMMARY = "Summary"
READY = "Ready for you to apply in your Chrome:"
COMPANIES = re.compile(
    r"^Boards: (?P<checked>[\d,]+) checked · (?P<new>[\d,]+) new · (?P<gone>[\d,]+) gone · "
    r"(?P<unreachable>[\d,]+) unreachable$"
)
JOBS = re.compile(
    r"^Jobs: (?P<open>[\d,]+) open · (?P<fit>[\d,]+) fit your titles and places · "
    r"(?P<new>[\d,]+) new$"
)
SCORED = re.compile(
    r"^Scored: (?P<good>[\d,]+) good match(?:es)? · (?P<skipped>[\d,]+) skipped · "
    r"(?P<retry>[\d,]+) to retry$"
)
RESULT = re.compile(
    r"^  (?:\d+/\d+ )?(?P<company>.+?) · (?P<title>.+): "
    r"(?:(?P<score>\d+), good match|skipped, (?P<note>.*)|(?P<retry>couldn't score it.*))$"
)
FOUND = re.compile(
    r"^  (?P<open>[\d,]+) open jobs · (?P<new>[\d,]+) new ones fit your titles and places$"
)
FAILED = re.compile(r"^✘ (?P<message>.+)$")
HINT = re.compile(r"^  → (?P<hint>.+)$")
IN_SETTINGS = re.compile(r"Settings → (?P<tab>[A-Za-z]+)")
LOW_SCORE = re.compile(r"^score (?P<score>\d+): (?P<note>.*)$")
MADE_READY = re.compile(r"^  ✔ (?P<company>.+?) · (?P<title>.+?)(?: \(your original resume\))?$")


def _numbers(pattern: re.Pattern[str], lines: list[str]) -> dict[str, int] | None:
    for line in lines:
        found = pattern.match(line)
        if found:
            return {key: int(value.replace(",", "")) for key, value in found.groupdict().items()}
    return None


def _result(found: re.Match[str]) -> dict[str, object]:
    score, note = found["score"], found["note"] or ""
    low = LOW_SCORE.match(note)
    if low:
        score, note = low["score"], low["note"]
    result = "good" if found["score"] else "retry" if found["retry"] else "skipped"
    return {
        "company": found["company"],
        "title": found["title"],
        "result": result,
        "score": int(score) if score else None,
        "note": note,
    }


def _ready(lines: list[str]) -> list[dict[str, str]]:
    if READY not in lines:
        return []
    after = lines[lines.index(READY) + 1 :]
    return [
        {"company": found["company"], "title": found["title"]}
        for found in map(MADE_READY.match, after)
        if found
    ]


def error_of(lines: list[str]) -> dict[str, str] | None:
    for at, line in enumerate(lines):
        failed = FAILED.match(line)
        if failed:
            hint = HINT.match(lines[at + 1]) if at + 1 < len(lines) else None
            message, more = failed["message"], hint["hint"] if hint else ""
            if more.startswith(message.rstrip(".")):
                message, more = more, ""
            where = IN_SETTINGS.search(f"{message} {more}")
            fix = f"/settings?tab={where['tab'].lower()}" if where else ""
            return {"message": message, "hint": more, "fix": fix}
    return None


def _jobs(summary: list[str], progress: list[str]) -> dict[str, int | None] | None:
    found = _numbers(JOBS, summary)
    if found:
        return dict(found)
    partial = _numbers(FOUND, progress)
    return {"open": partial["open"], "fit": None, "new": partial["new"]} if partial else None


def report_of(lines: list[str]) -> dict[str, object] | None:
    end = lines.index(SUMMARY) if SUMMARY in lines else len(lines)
    progress, summary = lines[:end], lines[end + 1 :]
    report: dict[str, object] = {
        "companies": _numbers(COMPANIES, summary),
        "jobs": _jobs(summary, progress),
        "scored": _numbers(SCORED, summary),
        "results": [_result(found) for found in map(RESULT.match, progress) if found],
        "prepared": _ready(summary),
        "error": error_of(progress),
    }
    return report if any(report.values()) else None
