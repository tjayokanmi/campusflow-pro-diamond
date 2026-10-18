from datetime import datetime, timezone, timedelta
try:
    from campusflow.priority import calculate_priority
    from campusflow.sla import calculate_due_at
except ImportError:
    from priority import calculate_priority
    from sla import calculate_due_at


def create_ticket(title, category, urgency, affected_users, records=None, now=None):

    title = title.strip()
    
    if title == "":
        raise ValueError("Empty Text")

    categories = ("Network", "Hardware", "Software", "Other")
    category = category.title()

    if category not in categories:
        raise ValueError("Supplied Category is invalid")
    
    urgencies = ["low", "medium", "high"]
    urgency = urgency.lower()

    if urgency not in urgencies:
        raise ValueError("Urgencies level does not exist")

    if not isinstance(affected_users, int) or isinstance(affected_users, bool) or affected_users < 1:
        raise ValueError("Incorrect input; user must be atleast 1 written in number")
    
    priority = calculate_priority(urgency, affected_users)

    ticket_id = generate_ticket_id(records) if records is not None else "T001"

    if now is not None:
        if isinstance(now, str):
            now_dt = datetime.fromisoformat(now)
        elif isinstance(now, datetime):
            now_dt = now
        else:
            raise TypeError("now must be a datetime or ISO datetime string")

        if now_dt.tzinfo is None or now_dt.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        if now_dt.utcoffset() != timedelta(0):
            raise ValueError("now must have a UTC offset of zero")
    else:
        now_dt = datetime.now(timezone.utc)

    due_dt = calculate_due_at(priority, now_dt)

    my_ticket = {
        "id": ticket_id,
        "title": title,
        "category": category,
        "urgency": urgency,
        "affected_users": affected_users,
        "priority": priority,
        "status": "open",
        "assigned_to": None,
        "created_at": now_dt.isoformat(),
        "updated_at": now_dt.isoformat(),
        "due_at": due_dt.isoformat(),
        "escalation_cycle": 0,
    }
    return my_ticket


# This is fake to test our generate_ticket_id function
records = [
    {
        "id": "T007",
        "title": "Wi-Fi is down",
        "category": "Network",
        "urgency": "high",
        "affected_users": 15,
        "priority": "critical",
        "status": "open",
        "assigned_to": None
    },
    {
        "id": "T003",
        "title": "Laptop is faulty",
        "category": "Hardware",
        "urgency": "medium",
        "affected_users": 2,
        "priority": "medium",
        "status": "open",
        "assigned_to": None
    },
    {
        "id": "T001",
        "title": "Cannot access learning platform",
        "category": "Software",
        "urgency": "low",
        "affected_users": 1,
        "priority": "low",
        "status": "open",
        "assigned_to": None
    }
]


def generate_ticket_id(records): 
    if not records:
        return "T001"
    numbers = [] 
    for record in records:
        if not isinstance(record, dict):
            continue
        ticket_id = record.get("id")
        if isinstance(ticket_id, str) and ticket_id.startswith("T") and ticket_id[1:].isdigit():
            numbers.append(int(ticket_id[1:])) 
    if not numbers:
        return "T001"
    max_id = max(numbers) 
    new_id = f"T{max_id + 1:03d}" 
    return new_id


if __name__ == "__main__":
    print(generate_ticket_id(records))
