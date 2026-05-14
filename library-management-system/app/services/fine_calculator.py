from datetime import datetime


def calculate_fine(due_date: datetime, returned_at: datetime, fine_per_day: float) -> float:
    """Return overdue fine. Zero when returned on time."""
    if returned_at <= due_date:
        return 0.0
    overdue_days = (returned_at - due_date).days
    return round(overdue_days * fine_per_day, 2)
