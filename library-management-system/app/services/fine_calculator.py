import math
from datetime import datetime


def calculate_fine(due_date: datetime, returned_at: datetime, fine_per_day: float) -> float:
    """Return overdue fine; any partial day counts as a full day."""
    if returned_at <= due_date:
        return 0.0
    overdue_seconds = (returned_at - due_date).total_seconds()
    overdue_days = math.ceil(overdue_seconds / 86400)
    return round(overdue_days * fine_per_day, 2)
