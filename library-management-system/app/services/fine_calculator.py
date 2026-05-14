from datetime import datetime
from app.core.config import settings


def calculate_fine(due_date: datetime, returned_at: datetime | None = None) -> float:
    check_date = returned_at or datetime.utcnow()
    if check_date <= due_date:
        return 0.0
    overdue_days = (check_date - due_date).days
    return round(overdue_days * settings.FINE_PER_DAY, 2)
