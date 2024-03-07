
from typing import Union


def duration(seconds: Union[float, int]) -> str:
    """
    Return 'human' description of number of seconds given. eg.

        >>> duration(300)
        '5 minutes'
        >>> duration(1e6)
        '11 days'

    Args:
        seconds (int)

    Returns (str):
        Approximate (in both senses) human expression of time.
    """
    # Mean Gregorian year
    YEAR = int(60 * 60 * 24 * 365.2425)
    DURATIONS = {
        'year': YEAR,
        'month': YEAR // 12,
        'week': 60 * 60 * 24 * 7,
        'day': 60 * 60 * 24,
        'hour': 60 * 60,
        'minute': 60,
        'second': 1,
    }

    # Validate input
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        raise ValueError('Number of seconds expected, given: {!r}'.format(seconds))

    if seconds < 0:
        raise ValueError('Positive number expected, given: {!r}'.format(seconds))

    # Use two or more units of whatever time unit we have
    duration = f"{seconds:,} seconds"
    for key in DURATIONS:
        length = DURATIONS[key]
        count = seconds // length
        if count > 1:
            return f"{count:,} {key}s"

    # Special case
    if seconds == 1:
        return '1 second'

    return duration
