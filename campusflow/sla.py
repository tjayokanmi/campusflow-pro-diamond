import datetime


def calculate_due_at(priority, cycle_start):
    now_utc = datetime.datetime(2026, 6, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
    expiry_utc = 