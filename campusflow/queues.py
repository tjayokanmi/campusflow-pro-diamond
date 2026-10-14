from datetime import datetime

def sla_attention_queue(tickets, now):
    def sort_key(ticket):
        due_at = datetime.fromisoformat(ticket["due_at"])

        overdue = (
            now > due_at
            and ticket["status"] != "resolved"
        )

        ticket_number = int(ticket["id"][1:])

        return (
            not overdue,
            due_at,
            ticket_number
        )

    unresolved = [
        ticket 
        for ticket in tickets
        if ticket["status"] in ("open", "in_progress")
    ]

    return sorted(unresolved, key=sort_key)