import json
import sqlite3
import threading
import urllib.request
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime, timedelta
from email.message import Message
from typing import Any
from urllib.error import HTTPError

from satyaapply.core.models import Status
from satyaapply.core.notes import AI_RULE_NOTE, DEALBREAKER_PREFIX, DUPLICATE_NOTE
from satyaapply.core.paths import Paths
from satyaapply.store import jobs
from satyaapply.store.groups import Group
from satyaapply.store.jobs import StatusChange
from satyaapply.tracker.server import TrackerServer
from tests.unit import samples

JSON_TYPE = "application/json"
Reply = tuple[int, Any]
SEEDED: tuple[tuple[Status, str, bool, set[Group]], ...] = (
    (Status.NEW, "", False, {Group.WAITING_SCORE}),
    (Status.SKIPPED, DUPLICATE_NOTE, False, {Group.DUPLICATE}),
    (Status.SKIPPED, AI_RULE_NOTE, False, {Group.NO_AI}),
    (Status.SKIPPED, f"{DEALBREAKER_PREFIX}on-site only", False, {Group.NOT_A_FIT}),
    (Status.SKIPPED, "score 41: weak React match", False, {Group.NOT_A_FIT}),
    (Status.SKIPPED, "title doesn't fit", False, {Group.SKIPPED_OTHER}),
    (Status.SCORED, "good match", False, {Group.SCORED}),
    (Status.CLOSED, "removed", False, {Group.CLOSED}),
    (Status.NEEDS_INPUT, "needs you", False, {Group.NEEDS_INPUT}),
    (Status.FINISH, "picture check", False, {Group.FINISH}),
    (Status.FAILED, "crashed", False, {Group.FAILED}),
    (Status.EXTERNAL, "unsupported form", False, {Group.EXTERNAL}),
    (Status.READY, "filled", False, {Group.READY}),
    (Status.APPROVED, "approved", False, {Group.APPROVED}),
    (Status.SUBMITTING, "sending", False, {Group.APPROVED}),
    (Status.SUBMITTING, "sending", True, {Group.AUTO_SENT}),
    (Status.APPLIED, "sent", True, {Group.AUTO_SENT, Group.APPLIED}),
    (Status.DISMISSED, "dismissed: location", False, {Group.DISMISSED}),
    (Status.APPLIED, "sent", False, {Group.APPLIED}),
    (Status.UNCONFIRMED, "no confirmation", False, {Group.UNCONFIRMED}),
)


def ids_in(group: Group) -> list[int]:
    found = [
        index + 1
        for index, (_, _, _, groups) in enumerate(SEEDED)
        if group is Group.FOUND or group in groups
    ]
    return sorted(found, reverse=True)


def seed_every_group(db: sqlite3.Connection, now: datetime) -> None:
    picks = [samples.job(external_id=str(index)) for index in range(len(SEEDED))]
    jobs.add_many(db, picks, now)
    for index, (status, note, auto, _) in enumerate(SEEDED, start=1):
        at = now + timedelta(minutes=index)
        if status is Status.SUBMITTING:
            jobs.mark_submitting(db, index, at, auto=auto)
        elif status is not Status.NEW:
            jobs.set_status(db, index, StatusChange(status, at, note))
        if auto and status is not Status.SUBMITTING:
            with db:
                db.execute("update jobs set auto_submitted = 1 where id = ?", (index,))


@contextmanager
def running(paths: Paths) -> Iterator[TrackerServer]:
    server = TrackerServer(paths, 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()


def fetch(
    server: TrackerServer,
    path: str,
    data: bytes | None = None,
    headers: Mapping[str, str] | None = None,
) -> tuple[int, Message, bytes]:
    method = "GET" if data is None else "POST"
    request = urllib.request.Request(  # noqa: S310
        server.url + path, data=data, headers=dict(headers or {}), method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
            return response.status, response.headers, response.read()
    except HTTPError as error:
        with error:
            return error.code, error.headers, error.read()


def get(server: TrackerServer, path: str) -> Reply:
    status, _, body = fetch(server, path)
    return status, json.loads(body)


def post(server: TrackerServer, path: str, body: object = None) -> Reply:
    data = json.dumps({} if body is None else body).encode()
    headers = {"Origin": server.url, "Content-Type": JSON_TYPE}
    status, _, answer = fetch(server, path, data, headers)
    return status, json.loads(answer)
