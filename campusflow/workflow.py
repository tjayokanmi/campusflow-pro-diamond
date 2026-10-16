from datetime import datetime, timezone, timedelta
from campusflow.sla import calculate_due_at

ALLOWED_STATUSES = ("open", "in_progress", "resolved")
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _find_ticket(tickets: list[dict], ticket_id: str) -> dict:
    """Locate a ticket dictionary by its unique identifier.

    Raises:
        TypeError: If tickets collection is not a list.
        ValueError: If ticket_id is not found in the collection.
    """
    if not isinstance(tickets, list):
        raise TypeError("Tickets collection must be a list")
    for ticket in tickets:
        if isinstance(ticket, dict) and ticket.get("id") == ticket_id:
            return ticket
    raise ValueError(f"Ticket with ID '{ticket_id}' not found")


def _extract_numeric_id(ticket_id: str) -> int:
    """Extract numeric suffix from ticket ID (e.g., 'T002' -> 2)."""
    digits = "".join(ch for ch in str(ticket_id) if ch.isdigit())
    if not digits:
        raise ValueError(f"Invalid ticket ID format with no numeric component: '{ticket_id}'")
    return int(digits)


def assign_ticket(tickets: list[dict], ticket_id: str, staff_name: str) -> dict:
    """Assign a ticket to a staff member.

    Validations:
        1. Ticket ID must exist in tickets.
        2. Staff name must be non-empty after trimming.
        3. A resolved ticket cannot be modified or assigned without explicit reopening.

    Returns:
        The updated ticket dictionary.
    """
    ticket = _find_ticket(tickets, ticket_id)

    if ticket.get("status") == "resolved":
        raise ValueError(f"Cannot assign resolved ticket '{ticket_id}'. Reopen the ticket first.")

    if not isinstance(staff_name, str):
        raise ValueError("Staff name must be a string")

    cleaned_name = staff_name.strip()
    if not cleaned_name:
        raise ValueError("Staff name cannot be empty or whitespace only")

    ticket["assigned_to"] = cleaned_name
    return ticket


def update_status(tickets: list[dict], ticket_id: str, new_status: str) -> dict:
    """Transition a ticket's lifecycle status.

    Lifecycle Rules:
        - Allowed statuses: 'open', 'in_progress', 'resolved'.
        - A resolved ticket cannot be modified through ordinary status transitions.
        - An open ticket can move to 'in_progress' only if it has an assigned staff member.
        - An in_progress ticket can move to 'resolved'.
        - An open ticket cannot move directly to 'resolved'.
        - Disallowed transitions and unknown statuses raise ValueError.

    Returns:
        The updated ticket dictionary.
    """
    ticket = _find_ticket(tickets, ticket_id)

    if not isinstance(new_status, str):
        raise ValueError("Status must be a string")

    target_status = new_status.strip().lower()
    if target_status not in ALLOWED_STATUSES:
        raise ValueError(
            f"Invalid status '{new_status}'. Allowed statuses are: {', '.join(ALLOWED_STATUSES)}"
        )

    current_status = ticket.get("status")

    if current_status == "resolved":
        raise ValueError(
            f"Resolved ticket '{ticket_id}' cannot be modified through ordinary status transitions. "
            "Use reopen_ticket instead."
        )

    if target_status == current_status:
        raise ValueError(f"Ticket '{ticket_id}' is already in status '{current_status}'")

    if current_status == "open":
        if target_status == "resolved":
            raise ValueError(
                f"Cannot resolve open ticket '{ticket_id}' directly. "
                "Ticket must move to 'in_progress' before resolution."
            )
        if target_status == "in_progress":
            assignee = ticket.get("assigned_to")
            if assignee is None or not str(assignee).strip():
                raise ValueError(
                    f"Cannot move open ticket '{ticket_id}' to 'in_progress' without an assigned staff member."
                )
            ticket["status"] = "in_progress"
            return ticket

    elif current_status == "in_progress":
        if target_status == "resolved":
            ticket["status"] = "resolved"
            return ticket
        if target_status == "open":
            raise ValueError(
                f"Cannot transition ticket '{ticket_id}' from 'in_progress' back to 'open' directly."
            )

    raise ValueError(f"Disallowed status transition from '{current_status}' to '{target_status}'")


def reopen_ticket(tickets: list[dict], ticket_id: str, now: datetime | None = None) -> dict:
    """Explicitly reopen a resolved ticket back to 'open' status.

    Rules:
        - Only tickets with status 'resolved' can be reopened.
        - Reopened tickets may resume normal lifecycle progression.
        - created_at is preserved unchanged.
        - Reopening starts a new SLA cycle at the reopening timestamp, recalculating due_at.

    Returns:
        The updated ticket dictionary.
    """
    ticket = _find_ticket(tickets, ticket_id)
    current_status = ticket.get("status")

    if current_status != "resolved":
        raise ValueError(
            f"Only resolved tickets can be reopened. Ticket '{ticket_id}' is currently '{current_status}'."
        )

    if now is not None:
        if not isinstance(now, datetime):
            raise TypeError("now must be a datetime")
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        if now.utcoffset() != timedelta(0):
            raise ValueError("now must have a UTC offset of zero")
    else:
        now = datetime.now(timezone.utc)

    ticket["status"] = "open"

    priority = ticket.get("priority")
    if priority and "due_at" in ticket:
        new_due = calculate_due_at(priority, now)
        if isinstance(ticket.get("due_at"), str):
            ticket["due_at"] = new_due.isoformat()
        else:
            ticket["due_at"] = new_due

    if "escalation_cycle" in ticket:
        ticket["escalation_cycle"] = ticket.get("escalation_cycle", 0) + 1

    if "updated_at" in ticket:
        ticket["updated_at"] = now.isoformat()

    return ticket


def get_work_queue(tickets: list[dict]) -> list[dict]:
    """Return active (open or in_progress) tickets ordered by priority and numeric ID.

    Queue Rules:
        - Exclude resolved tickets.
        - Priority order: critical -> high -> medium -> low.
        - Tie-breaking: ascending numeric ticket ID (e.g., T002 before T010).
        - Unexpected priority raises ValueError to preserve queue ordering integrity.
        - Returns a new list without rearranging the original collection.
    """
    if not isinstance(tickets, list):
        raise TypeError("Tickets collection must be a list")

    active_tickets = []
    for t in tickets:
        if not isinstance(t, dict):
            continue
        status = t.get("status")
        if status in ("open", "in_progress"):
            active_tickets.append(t)

    for t in active_tickets:
        p = t.get("priority")
        if p not in PRIORITY_ORDER:
            raise ValueError(
                f"Unexpected priority '{p}' in ticket '{t.get('id')}'. "
                f"Allowed priorities: {', '.join(PRIORITY_ORDER.keys())}"
            )

    return sorted(
        active_tickets,
        key=lambda t: (PRIORITY_ORDER[t["priority"]], _extract_numeric_id(t.get("id", "")))
    )
