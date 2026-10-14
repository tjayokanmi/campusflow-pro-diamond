import datetime


def calculate_due_at(priority, cycle_start):
    
    if not isinstance(cycle_start, datetime.datetime):
        raise TypeError("cycle_start must be a datetime")
    
    if cycle_start.tzinfo is None or cycle_start.utcoffset() is None:
        raise ValueError("cycle_start must be timezone-aware")
    
    if cycle_start.utcoffset() != datetime.timedelta(0):
        raise ValueError("cycle_start must have a UTC offset of zero")

    if priority == "critical":
        return cycle_start + datetime.timedelta(hours=1)
    elif priority == "high":
        return cycle_start + datetime.timedelta(hours = 4)
    elif priority == "medium":
        return cycle_start + datetime.timedelta(days = 1)
    elif priority == "low": 
        return cycle_start + datetime.timedelta(days=2)
    else:
        raise ValueError("You have only 4 options: critical, high, medium, and low")
    
def is_overdue(ticket, now):
    