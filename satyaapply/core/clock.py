from collections.abc import Callable
from datetime import UTC, datetime

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


def start_of_local_day(moment: datetime) -> datetime:
    local = moment.astimezone()
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(UTC)
