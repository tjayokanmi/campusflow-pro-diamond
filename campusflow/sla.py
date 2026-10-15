import datetime

from campusflow.history import record_event


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
    if not isinstance(now, datetime.datetime):
        raise TypeError("now must be a datetime")

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    if now.utcoffset() != datetime.timedelta(0):
        raise ValueError("now must have a UTC offset of zero")

    if not isinstance(ticket, dict):
        raise TypeError("ticket must be a dictionary")

    if "due_at" not in ticket:
        raise KeyError("ticket is missing required field: 'due_at'")

    if "status" not in ticket:
        raise KeyError("ticket is missing required field: 'status'")

    due_at = ticket["due_at"]
    status = ticket["status"]

    if not isinstance(due_at, datetime.datetime):
        raise TypeError("due_at must be a datetime")

    if due_at.tzinfo is None or due_at.utcoffset() is None:
        raise ValueError("due_at must be timezone-aware")

    if due_at.utcoffset() != datetime.timedelta(0):
        raise ValueError("due_at must have a UTC offset of zero")

    if status not in ("open", "in_progress", "resolved"):
        raise ValueError("Invalid ticket status")

    return status != "resolved" and due_at < now

def escalate_overdue(tickets, events, now, actor):
    escalated = []
    already_escalated = []

    for ticket in tickets:
        if not is_overdue(ticket, now):
            continue

        ticket_id = ticket["id"]

        has_escalation = any(
            event["ticket_id"] == ticket_id
            and event["event_type"] == "escalated"
            for event in events
        )

        if has_escalation:
            already_escalated.append(ticket_id)
            continue

        record_event(
            events=events,
            ticket_id=ticket_id,
            event_type="escalated",
            actor=actor,
            before_status=ticket["status"],
            after_status=ticket["status"],
            details="SLA deadline exceeded",
            now=now,
        )

        escalated.append(ticket_id)

    return {
        "escalated": escalated,
        "already_escalated": already_escalated,
    }