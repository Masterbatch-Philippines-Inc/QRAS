from django.utils import timezone
from ...dataclasses import PairingResult


def pair_logs(logs):
    pairs         = []
    stack         = None
    first_time_in = None

    for log in logs:
        if log.is_time_in:
            if stack is None:
                stack = log.timestamp
                if first_time_in is None:
                    first_time_in = timezone.localtime(log.timestamp)
        elif log.is_time_out and stack:
            pairs.append((stack, log.timestamp))
            stack = None

    pairs = [(inn, out) for inn, out in pairs if (out - inn).total_seconds() > 60]

    return PairingResult(
        pairs=pairs,
        stack=stack,
        first_time_in=first_time_in,
    )