"""Reporting functionality for CampusFlow tickets."""

from datetime import datetime, timezone

ALLOWED_STATUSES = ("open", "in_progress", "resolved")
ALLOWED_PRIORITIES = ("critical", "high", "medium", "low")


def generate_report(
    tickets: list[dict],
    events: list[dict] | None = None,
    now: datetime | None = None,
) -> dict:
    """Generate ticket statistics, including SLA metrics."""

    if not isinstance(tickets, list):
        raise TypeError("Tickets collection must be a list")

    if events is None:
        events = []

    if not isinstance(events, list):
        raise TypeError("Events collection must be a list")

    if now is None:
        now = datetime.now(timezone.utc)

    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")

    by_status = {status: 0 for status in ALLOWED_STATUSES}
    by_priority = {priority: 0 for priority in ALLOWED_PRIORITIES}

    total = 0
    overdue_count = 0
    escalated_count = 0

    for ticket in tickets:
        if not isinstance(ticket, dict):
            continue

        total += 1

        status = ticket.get("status")
        priority = ticket.get("priority")

        if status in by_status:
            by_status[status] += 1

        if priority in by_priority:
            by_priority[priority] += 1

        if status not in ("open", "in_progress"):
            continue

        due_at = ticket.get("due_at")

        if due_at:
            deadline = datetime.fromisoformat(due_at)

            if deadline.tzinfo is None or deadline.utcoffset() is None:
                raise ValueError("Ticket due_at must be timezone-aware")

            if now > deadline:
                overdue_count += 1

        current_cycle = ticket.get("escalation_cycle", 0)

        was_escalated = any(
            event.get("ticket_id") == ticket.get("id")
            and event.get("event_type") == "ESCALATE"
            and isinstance(event.get("details"), dict)
            and event["details"].get("escalation_cycle") == current_cycle
            for event in events
        )
        if was_escalated:
            escalated_count += 1

    return {
        "total": total,
        "by_status": by_status,
        "by_priority": by_priority,
        "overdue_count": overdue_count,
        "escalated_count": escalated_count,
    }