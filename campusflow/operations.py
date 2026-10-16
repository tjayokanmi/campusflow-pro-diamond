"""Audited ticket operations for CampusFlow Pro."""

from copy import deepcopy

from campusflow.tickets import create_ticket
from campusflow.workflow import (
    assign_ticket,
    update_status,
    reopen_ticket,
)
from campusflow.history import record_event
from campusflow.duplicates import detect_duplicates


def create_ticket_with_audit(
    tickets,
    events,
    title,
    category,
    urgency,
    affected_users,
    actor,
    confirm_duplicate=False,
):
    """Create a ticket and record its audit event."""

    temp_tickets = deepcopy(tickets)
    temp_events = deepcopy(events)

    ticket = create_ticket(
        title,
        category,
        urgency,
        affected_users,
        records=temp_tickets,
    )

    duplicates = detect_duplicates(
        temp_tickets,
        ticket["category"],
        ticket["title"],
    )

    if duplicates and not confirm_duplicate:
        raise ValueError(
            f"Potential duplicate tickets: {', '.join(duplicates)}. "
            "Confirmation required."
        )

    temp_tickets.append(ticket)

    record_event(
        temp_events,
        ticket["id"],
        "CREATE",
        actor,
        None,
        "open",
        "Ticket created",
    )

    tickets[:] = temp_tickets
    events[:] = temp_events

    return ticket


def assign_ticket_with_audit(
    tickets,
    events,
    ticket_id,
    staff_name,
    actor,
):
    """Assign a ticket and record the successful assignment."""

    temp_tickets = deepcopy(tickets)
    temp_events = deepcopy(events)

    ticket = assign_ticket(
        temp_tickets,
        ticket_id,
        staff_name,
    )

    record_event(
        temp_events,
        ticket_id,
        "ASSIGN",
        actor,
        ticket["status"],
        ticket["status"],
        f"Assigned to {staff_name}",
    )

    tickets[:] = temp_tickets
    events[:] = temp_events

    return ticket


def update_status_with_audit(
    tickets,
    events,
    ticket_id,
    new_status,
    actor,
):
    """Update ticket status and record the transition."""

    temp_tickets = deepcopy(tickets)
    temp_events = deepcopy(events)

    ticket = next(
        (t for t in temp_tickets if t["id"] == ticket_id),
        None,
    )

    if ticket is None:
        raise ValueError("Ticket not found")

    before_status = ticket["status"]

    updated_ticket = update_status(
        temp_tickets,
        ticket_id,
        new_status,
    )

    event_type = {
        "in_progress": "START",
        "resolved": "RESOLVE",
    }.get(updated_ticket["status"])

    if event_type is None:
        raise ValueError("Unsupported audited status transition")

    record_event(
        temp_events,
        ticket_id,
        event_type,
        actor,
        before_status,
        updated_ticket["status"],
        f"Status changed from {before_status} to {updated_ticket['status']}",
    )

    tickets[:] = temp_tickets
    events[:] = temp_events

    return updated_ticket


def reopen_ticket_with_audit(
    tickets,
    events,
    ticket_id,
    actor,
    now=None,
):
    """Reopen a resolved ticket and record the event."""
    from datetime import datetime, timezone

    if now is None:
        now = datetime.now(timezone.utc)

    temp_tickets = deepcopy(tickets)
    temp_events = deepcopy(events)

    ticket = reopen_ticket(
        temp_tickets,
        ticket_id,
        now=now,
    )

    record_event(
        temp_events,
        ticket_id,
        "REOPEN",
        actor,
        "resolved",
        "open",
        "Ticket reopened",
        now=now,
    )

    tickets[:] = temp_tickets
    events[:] = temp_events

    return ticket