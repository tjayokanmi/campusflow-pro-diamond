from datetime import datetime, timezone


def record_event(
    events,
    ticket_id,
    event_type,
    actor,
    before_status,
    after_status,
    details,
    now=None
):
    if now is None:
        now = datetime.now(timezone.utc)
    
    event = {
        "event_id": f"E{len(events)+ 1:03d}",
        "ticket_id": ticket_id,
        "event_type": event_type,
        "actor": actor,
        "timestamp": now.isoformat(),
        "before_status": before_status,
        "after_status": after_status,
        "details": details,
    }

    events.append(event)

    return event


def get_ticket_history(events, ticket_id):
    history = [
        event
        for event in events
        if event["ticket_id"] == ticket_id
    ]

    return sorted(
        history,
        key=lambda event: (
            event["timestamp"],
            event["event_id"]
        ),
    )