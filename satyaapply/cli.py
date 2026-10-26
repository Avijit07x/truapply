import argparse
import hashlib
import sys
import webbrowser
from collections.abc import Callable, Sequence
from contextlib import closing
from importlib import metadata
from pathlib import Path

from satyaapply import doctor
from satyaapply.core import logs
from satyaapply.core.errors import SatyaApplyError
from satyaapply.core.models import Job, Source, normalize
from satyaapply.core.paths import Paths, default_paths
from satyaapply.core.profile import load
from satyaapply.onboarding import wizard
from satyaapply.resume.diff import changed_lines
from satyaapply.resume.master import load_resume, master_pdf
from satyaapply.resume.tailor import Tailored, TailorRequest, file_name_for, tailor
from satyaapply.run import RunOptions, RunReport, run
from satyaapply.sources.discover import as_csv_rows, shared_boards
from satyaapply.store import boards
from satyaapply.store.boards import BoardOrigin
from satyaapply.store.db import connect
from satyaapply.tracker.server import DEFAULT_PORT, TrackerServer

Handler = Callable[[argparse.Namespace, Paths], int]
JOB_ID_CHARS = 12
EXIT_USAGE = 2
EXIT_INTERRUPTED = 130
STATUS_MARKS = {"ready": "✔", "applied": "✔", "needs_input": "?", "skipped": "-"}


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
    request = TailorRequest(job, (), folder, file_name_for(profile.name), master_pdf(paths, resume))
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
    print("Prepared:")
    for item in report.prepared:
        mark = STATUS_MARKS.get(item.attempt.status, "✘")
        print(f"  {mark} {item.attempt.status:<12} {item.job.company} · {item.job.title}")
        print(f"      {item.attempt.note}")
        if item.attempt.questions:
            print(f"      questions: {'; '.join(item.attempt.questions)}")
        if item.shot:
            print(f"      screenshot: {item.shot}")


def _say(message: str) -> None:
    print(message, flush=True)


def _run(args: argparse.Namespace, paths: Paths) -> int:
    options = RunOptions(
        limit=args.limit, search=not args.no_search, show=args.show, send=args.send, progress=_say
    )
    _print_run(run(paths, options))
    return 0


def _tracker(args: argparse.Namespace, paths: Paths) -> int:
    with TrackerServer(paths, args.port) as server:
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
        print("No new boards yet. They're found during `satyaapply run`.")
        return 0
    print("ats,slug,company,tags")
    for row in as_csv_rows(new):
        print(row)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="satyaapply", description="Honest job applications, from your own computer."
    )
    parser.add_argument("--version", action="version", version=metadata.version("satyaapply"))
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

    runner = commands.add_parser(
        "run", help="find and score jobs, fill forms, and send the ones you approved"
    )
    runner.add_argument("--limit", type=int, default=5, help="applications to prepare (default 5)")
    runner.add_argument("--no-search", action="store_true", help="skip the daily web search")
    runner.add_argument("--show", action="store_true", help="show the browser window")
    runner.add_argument(
        "--send", action="store_true", help="really send the jobs you approved on the tracker"
    )
    runner.set_defaults(handler=_run)

    listing = commands.add_parser("boards", help="print boards you found that aren't shared yet")
    listing.add_argument("--new", action="store_true", help="only boards not in the shared list")
    listing.set_defaults(handler=_boards)

    page = commands.add_parser("tracker", help="open your tracker page in the browser")
    page.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"default {DEFAULT_PORT}")
    page.add_argument("--open", action="store_true", help="open it in your browser")
    page.set_defaults(handler=_tracker)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logs.configure(args.verbose)
    handler: Handler = args.handler
    try:
        return handler(args, default_paths())
    except SatyaApplyError as error:
        print(f"✘ {error}", file=sys.stderr)
        if error.hint:
            print(f"  → {error.hint}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return EXIT_INTERRUPTED
