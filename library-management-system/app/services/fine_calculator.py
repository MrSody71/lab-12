from datetime import datetime, timezone
from app.core.config import get_settings


def calculate_fine(due_date: datetime, returned_at: datetime | None = None) -> float:
    check_date = returned_at or datetime.now(timezone.utc)
    if check_date <= due_date:
        return 0.0
    overdue_days = (check_date - due_date).days
    return round(overdue_days * get_settings().FINE_PER_DAY, 2)
