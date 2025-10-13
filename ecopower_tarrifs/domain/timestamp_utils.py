"""Utilities for normalizing timestamps to ensure alignment"""
from datetime import datetime, timedelta


def floor_to_15_minutes(dt: datetime) -> datetime:
    """
    Floor a datetime to the nearest 15-minute boundary.

    This ensures timestamps from different sources align properly.

    Examples:
        2025-10-01 12:07:23 -> 2025-10-01 12:00:00
        2025-10-01 12:15:00 -> 2025-10-01 12:15:00
        2025-10-01 12:16:42 -> 2025-10-01 12:15:00
        2025-10-01 12:47:59 -> 2025-10-01 12:45:00

    Args:
        dt: Datetime to floor

    Returns:
        Datetime floored to 15-minute boundary (with microseconds=0, timezone-naive)
    """
    # Convert to naive datetime (remove timezone info)
    if dt.tzinfo is not None:
        dt = dt.replace(tzinfo=None)

    # Calculate minutes since midnight
    minutes_since_midnight = dt.hour * 60 + dt.minute

    # Floor to nearest 15-minute interval
    floored_minutes = (minutes_since_midnight // 15) * 15

    # Create new datetime with floored time
    return datetime(
        year=dt.year,
        month=dt.month,
        day=dt.day,
        hour=floored_minutes // 60,
        minute=floored_minutes % 60,
        second=0,
        microsecond=0
    )
