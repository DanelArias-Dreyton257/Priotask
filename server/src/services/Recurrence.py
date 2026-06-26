"""
Date math for recurring tasks (Phase 11): advancing a deadline by a
recurrence rule (interval + unit). Kept separate from TaskManager since it's
pure date arithmetic with no persistence/domain dependencies.
"""
import calendar
from datetime import datetime, timedelta

RECURRENCE_UNITS = ("day", "week", "month")


def next_deadline(deadline: datetime, unit: str, interval: int) -> datetime:
    """Advances deadline by `interval` occurrences of `unit`.

    Month arithmetic clamps the day-of-month to the target month's last day
    (e.g. Jan 31 + 1 month -> Feb 28/29) instead of overflowing into the
    following month, as a naive day-count addition would.
    """
    if unit == "day":
        return deadline + timedelta(days=interval)
    if unit == "week":
        return deadline + timedelta(weeks=interval)
    if unit == "month":
        total_month_index = (deadline.year * 12 + (deadline.month - 1)) + interval
        year, month = divmod(total_month_index, 12)
        month += 1
        day = min(deadline.day, calendar.monthrange(year, month)[1])
        return deadline.replace(year=year, month=month, day=day)
    raise ValueError(f"unknown recurrence unit: {unit!r}")
