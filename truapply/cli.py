import argparse
import hashlib
import sys
import webbrowser
from collections.abc import Callable, Sequence
from contextlib import closing, redirect_stderr, redirect_stdout
from importlib import metadata
from pathlib import Path

from truapply import doctor
from truapply.core import logs, schedule
from truapply.core.clock import utc_now
from truapply.core.errors import TruApplyError
from truapply.core.locks import is_held
from truapply.core.models import Job, RunStage, Source, normalize
from truapply.core.paths import AUTOMATIC_RUN, MANUAL_RUN, Paths, default_paths
from truapply.core.profile import MAX_EVERY_MINUTES, MIN_EVERY_MINUTES, load
from truapply.onboarding import wizard
from truapply.resume.diff import changed_lines
from truapply.resume.master import load_resume, master_pdf
from truapply.resume.tailor import Tailored, TailorRequest, file_name_for, tailor
from truapply.run import RunOptions, RunReport, run
from truapply.run.lock import ALREADY_RUNNING as ALREADY_GOING
from truapply.sources.discover import as_csv_rows, shared_boards
from truapply.sources.intake import NOT_A_BOARD, take_in_link
from truapply.store import boards, rules
from truapply.store.boards import BoardOrigin
from truapply.store.db import connect
from truapply.store.rules import RuleKind
from truapply.tracker.server import DEFAULT_PORT, open_server

Handler = Callable[[argparse.Namespace, Paths], int]
JOB_ID_CHARS = 12
EXIT_USAGE = 2
EXIT_INTERRUPTED = 130


def _setup(args: argparse.Namespace, paths: Paths) -> int:
    wizard.run(paths, args.resume)
    return 0


def _doctor(_args: argparse.Namespace, paths: Paths) -> int:
    return doctor.report(doctor.run_checks(paths))


def _print_tailored(result: Tailored, changed: list[str]) -> None:
    if result.used_original:
        print("✘ Kept your original resume, because:")
        for problem in result.problems:
            print(f"   - {problem}")
    else:
        print("✔ Tailored. Passed: structure, numbers, new-claims and length checks.")
        for change in result.changes:
            print(f"   - {change}")
        print("\nChanged lines:")
        for line in changed:
            print(f"  {line}")
    print(f"\nPDF: {result.pdf}")


def _tailor(args: argparse.Namespace, paths: Paths) -> int:
    job_file: Path = args.job_file
    if not job_file.is_file():
        print(f"✘ {job_file} doesn't exist.", file=sys.stderr)
        return EXIT_USAGE
    profile = load(paths)
    resume = load_resume(profile)
    description = job_file.read_text(encoding="utf-8")
    job = Job(
        Source.MANUAL,
        hashlib.sha256(description.encode()).hexdigest()[:JOB_ID_CHARS],
        url="",
        company=args.company,
        title=args.title,
        description=description,
    )
    folder = paths.previews / normalize(f"{args.company} {args.title}").replace(" ", "-")
    with closing(connect(paths.database)) as db:
        notes = rules.active_texts(db, RuleKind.TAILORING_NOTE)
    master = master_pdf(paths, resume)
    request = TailorRequest(job, notes, folder, file_name_for(profile.name), master)
    print(f"Tailoring your resume for {args.title} at {args.company} …")
    result = tailor(resume, request)
    original, tailored = resume.readable(resume.source), resume.readable(result.source)
    _print_tailored(result, changed_lines(original, tailored))
    return 0


def _print_run(report: RunReport) -> None:
    found, scored = report.discovery, report.scoring
    print("\nSummary")
    print(
        f"Boards: {found.boards} checked · {found.new_boards} new · {found.dead} gone · "
        f"{found.unreachable} unreachable"
    )
    print(
        f"Jobs: {found.found:,} open · {found.kept} fit your titles and places · {found.added} new"
    )
    print(
        f"Scored: {scored.matched} good {'match' if scored.matched == 1 else 'matches'} · "
        f"{scored.skipped} skipped · {scored.failed} to retry"
    )
    if not report.prepared:
        print("Prepared: nothing this run")
        return
    print("Ready for you to apply in your Chrome:")
    for item in report.prepared:
        kept = " (your original resume)" if item.resume.used_original else ""
        print(f"  ✔ {item.job.company} · {item.job.title}{kept}")


def _say(message: str) -> None:
    print(message, flush=True)


def _explain(error: TruApplyError) -> None:
    print(f"✘ {error}", file=sys.stderr)
    if error.hint:
        print(f"  → {error.hint}", file=sys.stderr)


def _run(args: argparse.Namespace, paths: Paths) -> int:
    options = RunOptions(
        limit=args.limit,
        search=not args.no_search,
        search_now=args.find_companies,
        find=not args.no_find,
        job=args.job,
        score=tuple(args.score or ()),
        only=RunStage(args.only) if args.only else None,
        progress=_say,
    )
    if not args.scheduled:
        print(MANUAL_RUN, flush=True)
        _print_run(run(paths, options))
        return 0
    if is_held(paths.lock):
        print(ALREADY_GOING, flush=True)
        return 0
    log = paths.run_log(utc_now())
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as out, redirect_stdout(out), redirect_stderr(out):
        print(AUTOMATIC_RUN, flush=True)
        try:
            _print_run(run(paths, options))
        except TruApplyError as error:
            _explain(error)
            return 1
    return 0


def _minutes(text: str) -> int:
    value = int(text)
    if not MIN_EVERY_MINUTES <= value <= MAX_EVERY_MINUTES:
        raise argparse.ArgumentTypeError(f"use {MIN_EVERY_MINUTES} to {MAX_EVERY_MINUTES} minutes")
    return value


def _schedule(args: argparse.Namespace, paths: Paths) -> int:
    every: int = args.every or load(paths).settings.run_every_minutes
    plan = schedule.Plan(every)
    if sys.platform != "darwin":
        print("Add this line with `crontab -e`:")
        print(schedule.cron_line(paths, plan))
        return 0
    schedule.install(paths, plan, schedule.agents_dir())
    print(f"✔ Scheduled every {schedule.every(plan.every_minutes)}.")
    print("  Logs show on the tracker's Run page. Stop with: truapply unschedule")
    return 0


def _unschedule(_args: argparse.Namespace, _paths: Paths) -> int:
    if sys.platform != "darwin":
        print("Remove the truapply line with `crontab -e`.")
        return 0
    removed = schedule.remove(schedule.agents_dir())
    print("✔ Unscheduled. Nothing runs on its own now." if removed else "Nothing was scheduled.")
    return 0


def _tracker(args: argparse.Namespace, paths: Paths) -> int:
    with open_server(paths, args.port) as server:
        print(f"Tracker running at {server.url}  (Ctrl+C to stop)", flush=True)
        if args.open:
            webbrowser.open(server.url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
    return 0


def _boards(_args: argparse.Namespace, paths: Paths) -> int:
    shared = {board.key for board in shared_boards()}
    with closing(connect(paths.database)) as db:
        found = boards.by_origin(db, BoardOrigin.SEARCH) + boards.by_origin(db, BoardOrigin.LINK)
    new = [board for board in found if board.key not in shared]
    if not new:
        print("No new boards yet. They're found during `truapply run`.")
        return 0
    print("ats,slug,company,tags")
    for row in as_csv_rows(new):
        print(row)
    return 0


def _add(args: argparse.Namespace, paths: Paths) -> int:
    profile = load(paths)
    with closing(connect(paths.database)) as db:
        linked = take_in_link(db, args.link, profile, utc_now())
    if linked is None:
        print(f"✘ {NOT_A_BOARD}", file=sys.stderr)
        return EXIT_USAGE
    board, intake = linked
    print(
        f"✔ Added {board.company or board.slug}: {intake.found} open, {intake.kept} for you, "
        f"{intake.added} new. They're scored on the next run."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="truapply", description="Honest job applications, from your own computer."
    )
    parser.add_argument("--version", action="version", version=metadata.version("truapply"))
    parser.add_argument("--verbose", action="store_true", help="show detailed logs")
    commands = parser.add_subparsers(dest="command", required=True)

    setup = commands.add_parser("setup", help="answer the setup questions")
    setup.add_argument("--resume", type=Path, help="path to your resume")
    setup.set_defaults(handler=_setup)

    commands.add_parser("doctor", help="check that everything works").set_defaults(handler=_doctor)

    preview = commands.add_parser("tailor", help="preview your resume tailored to one job")
    preview.add_argument("job_file", type=Path, help="text file with the job description")
    preview.add_argument("--company", required=True)
    preview.add_argument("--title", required=True)
    preview.set_defaults(handler=_tailor)

    runner = commands.add_parser("run", help="find and score jobs, and tailor your resume")
    runner.add_argument("--limit", type=int, help="resumes to tailor (default: your settings)")
    runner.add_argument(
        "--no-search", action="store_true", help="skip the web search for companies"
    )
    runner.add_argument(
        "--find-companies", action="store_true", help="search the web for new companies now"
    )
    runner.add_argument("--job", type=int, help="only score and tailor this one job")
    runner.add_argument(
        "--score", type=int, nargs="+", help="score these jobs, then tailor the good matches"
    )
    runner.add_argument(
        "--no-find", action="store_true", help="skip career pages; score jobs already added"
    )
    runner.add_argument(
        "--only", choices=[str(stage) for stage in RunStage], help="run just this one step"
    )
    runner.add_argument("--scheduled", action="store_true", help=argparse.SUPPRESS)
    runner.set_defaults(handler=_run)

    timer = commands.add_parser("schedule", help="run on its own every few hours")
    timer.add_argument(
        "--every", type=_minutes, help="minutes between runs (default: your settings)"
    )
    timer.set_defaults(handler=_schedule)
    commands.add_parser("unschedule", help="stop running on its own").set_defaults(
        handler=_unschedule
    )

    adder = commands.add_parser("add", help="add a company's jobs from a job or board link")
    adder.add_argument("link", help="a Greenhouse, Lever or Ashby job or board link")
    adder.set_defaults(handler=_add)

    listing = commands.add_parser("boards", help="print boards you found that aren't shared yet")
    listing.add_argument("--new", action="store_true", help="only boards not in the shared list")
    listing.set_defaults(handler=_boards)

    page = commands.add_parser("tracker", help="open your tracker page in the browser")
    page.add_argument(
        "--port", type=int, help=f"default {DEFAULT_PORT}, or a free one if that's taken"
    )
    page.add_argument("--open", action="store_true", help="open it in your browser")
    page.set_defaults(handler=_tracker)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logs.configure(args.verbose)
    handler: Handler = args.handler
    try:
        return handler(args, default_paths())
    except TruApplyError as error:
        _explain(error)
        return 1
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return EXIT_INTERRUPTED
