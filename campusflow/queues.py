from datetime import datetime

def sla_attention_queue(tickets, now):
    def sort_key(ticket):
        due_at_val = ticket.get("due_at")
        if isinstance(due_at_val, str):
            due_at = datetime.fromisoformat(due_at_val)
        elif isinstance(due_at_val, datetime):
            due_at = due_at_val
        else:
            due_at = datetime.max.replace(tzinfo=now.tzinfo)

        overdue = (
            now > due_at
            and ticket.get("status") != "resolved"
        )

        digits = "".join(ch for ch in str(ticket.get("id", "0")) if ch.isdigit())
        ticket_number = int(digits) if digits else 0

        return (
            not overdue,
            due_at,
            ticket_number
        )

    unresolved = [
        ticket 
        for ticket in tickets
        if isinstance(ticket, dict)
        and ticket.get("status") in ("open", "in_progress")
        and ticket.get("due_at") is not None
    ]

    return sorted(unresolved, key=sort_key)