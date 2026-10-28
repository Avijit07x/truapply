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

from tests.unit import samples
from truapply.core.models import Status
from truapply.core.notes import (
    AI_RULE_NOTE,
    DEALBREAKER_PREFIX,
    DUPLICATE_NOTE,
    SKIPPED_COMPANY_NOTE,
    TOO_OLD_NOTE,
    WRONG_PLACE_NOTE,
    WRONG_TITLE_NOTE,
)
from truapply.core.paths import Paths
from truapply.store import jobs
from truapply.store.groups import Group
from truapply.store.jobs import StatusChange
from truapply.tracker.server import TrackerServer

JSON_TYPE = "application/json"
Reply = tuple[int, Any]
SEEDED: tuple[tuple[Status, str, set[Group]], ...] = (
    (Status.NEW, "", {Group.WAITING_SCORE}),
    (Status.SKIPPED, DUPLICATE_NOTE, {Group.DUPLICATE}),
    (Status.SKIPPED, AI_RULE_NOTE, {Group.NO_AI}),
    (Status.SKIPPED, f"{DEALBREAKER_PREFIX}on-site only", {Group.NOT_A_FIT}),
    (Status.SKIPPED, "score 41: weak React match", {Group.NOT_A_FIT}),
    (Status.SKIPPED, "title doesn't fit", {Group.SKIPPED}),
    (Status.SCORED, "good match", {Group.SCORED}),
    (Status.CLOSED, "removed", {Group.CLOSED}),
    (Status.READY, "tailored", {Group.READY}),
    (Status.DISMISSED, "dismissed: location", {Group.DISMISSED}),
    (Status.APPLIED, "sent", {Group.APPLIED}),
    (Status.SKIPPED, WRONG_TITLE_NOTE, {Group.SKIPPED, Group.WRONG_TITLE}),
    (Status.SKIPPED, WRONG_PLACE_NOTE, {Group.SKIPPED, Group.WRONG_PLACE}),
    (Status.SKIPPED, TOO_OLD_NOTE, {Group.SKIPPED, Group.TOO_OLD}),
    (Status.SKIPPED, SKIPPED_COMPANY_NOTE, {Group.SKIPPED, Group.SKIPPED_COMPANY}),
)


def ids_in(group: Group) -> list[int]:
    found = [
        index + 1
        for index, (_, _, groups) in enumerate(SEEDED)
        if group is Group.FOUND or group in groups
    ]
    return sorted(found, reverse=True)


def seed_every_group(db: sqlite3.Connection, now: datetime) -> None:
    picks = [samples.job(external_id=str(index)) for index in range(len(SEEDED))]
    jobs.add_many(db, picks, now)
    for index, (status, note, _) in enumerate(SEEDED, start=1):
        if status is not Status.NEW:
            jobs.set_status(db, index, StatusChange(status, now + timedelta(minutes=index), note))


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
