"""JSON persistence for CampusFlow tickets and audit events with atomic file replacement (Schema Version 2)."""

import json
import os
import re
import tempfile
from datetime import datetime

DEFAULT_DATA_PATH = os.path.join("data", "tickets.json")
SCHEMA_VERSION = 2

ALLOWED_CATEGORIES = ("Network", "Hardware", "Software", "Other")
ALLOWED_URGENCIES = ("low", "medium", "high")
ALLOWED_PRIORITIES = ("critical", "high", "medium", "low")
ALLOWED_STATUSES = ("open", "in_progress", "resolved")
TICKET_ID_REGEX = re.compile(r"^T\d+$")
EVENT_ID_REGEX = re.compile(r"^E\d+$")


def _json_serial(obj):
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj).__name__} not serializable")


def validate_ticket(ticket: dict, idx: int | None = None) -> None:
    """Validate that a dictionary represents a valid ticket according to CampusFlow rules."""
    prefix = f"Ticket at index {idx}: " if idx is not None else "Ticket: "

    if not isinstance(ticket, dict):
        raise ValueError(f"{prefix}must be a dictionary, found {type(ticket).__name__}")

    # Required field: id
    if "id" not in ticket:
        raise ValueError(f"{prefix}missing required field 'id'")
    tid = ticket["id"]
    if not isinstance(tid, str) or not tid.strip():
        raise ValueError(f"{prefix}ticket ID must be a non-empty string")

    # Required field: title
    if "title" not in ticket:
        raise ValueError(f"{prefix}missing required field 'title'")
    title = ticket["title"]
    if not isinstance(title, str) or not title.strip():
        raise ValueError(f"{prefix}title must be a non-empty string")

    # Required field: category
    if "category" not in ticket:
        raise ValueError(f"{prefix}missing required field 'category'")
    cat = ticket["category"]
    if not isinstance(cat, str) or cat not in ALLOWED_CATEGORIES:
        raise ValueError(f"{prefix}invalid category '{cat}', expected one of {ALLOWED_CATEGORIES}")

    # Required field: urgency
    if "urgency" not in ticket:
        raise ValueError(f"{prefix}missing required field 'urgency'")
    urg = ticket["urgency"]
    if not isinstance(urg, str) or urg not in ALLOWED_URGENCIES:
        raise ValueError(f"{prefix}invalid urgency '{urg}', expected one of {ALLOWED_URGENCIES}")

    # Required field: affected_users
    if "affected_users" not in ticket:
        raise ValueError(f"{prefix}missing required field 'affected_users'")
    users = ticket["affected_users"]
    if not isinstance(users, int) or isinstance(users, bool) or users < 1:
        raise ValueError(f"{prefix}affected_users must be an integer >= 1, found {users}")

    # Required field: priority
    if "priority" not in ticket:
        raise ValueError(f"{prefix}missing required field 'priority'")
    pri = ticket["priority"]
    if not isinstance(pri, str) or pri not in ALLOWED_PRIORITIES:
        raise ValueError(f"{prefix}invalid priority '{pri}', expected one of {ALLOWED_PRIORITIES}")

    # Required field: status
    if "status" not in ticket:
        raise ValueError(f"{prefix}missing required field 'status'")
    stat = ticket["status"]
    if not isinstance(stat, str) or stat not in ALLOWED_STATUSES:
        raise ValueError(f"{prefix}invalid status '{stat}', expected one of {ALLOWED_STATUSES}")

    # Required field: assigned_to
    if "assigned_to" not in ticket:
        raise ValueError(f"{prefix}missing required field 'assigned_to'")
    assigned = ticket["assigned_to"]
    if assigned is not None and not isinstance(assigned, str):
        raise ValueError(f"{prefix}assigned_to must be a string or None, found {type(assigned).__name__}")

    # Optional fields validation
    for field in ("created_at", "updated_at", "due_at"):
        if field in ticket:
            val = ticket[field]
            if not isinstance(val, str) or not val.strip():
                raise ValueError(f"{prefix}{field} must be a non-empty ISO datetime string")

    if "escalation_cycle" in ticket:
        cycle = ticket["escalation_cycle"]
        if not isinstance(cycle, int) or isinstance(cycle, bool) or cycle < 0:
            raise ValueError(f"{prefix}escalation_cycle must be an integer >= 0")


def validate_event(event: dict, idx: int | None = None, valid_ticket_ids: set[str] | None = None) -> None:
    """Validate that a dictionary represents a valid audit event."""
    prefix = f"Event at index {idx}: " if idx is not None else "Event: "

    if not isinstance(event, dict):
        raise ValueError(f"{prefix}must be a dictionary, found {type(event).__name__}")

    # Required fields
    required_keys = ("event_id", "ticket_id", "event_type", "actor", "timestamp", "before_status", "after_status", "details")
    for key in required_keys:
        if key not in event:
            raise ValueError(f"{prefix}missing required field '{key}'")

    eid = event["event_id"]
    if not isinstance(eid, str) or not eid.strip():
        raise ValueError(f"{prefix}event_id must be a non-empty string")

    tid = event["ticket_id"]
    if not isinstance(tid, str) or not tid.strip():
        raise ValueError(f"{prefix}ticket_id must be a non-empty string")

    if valid_ticket_ids is not None and tid not in valid_ticket_ids:
        raise ValueError(f"{prefix}references unknown ticket ID '{tid}'")

    etype = event["event_type"]
    if not isinstance(etype, str) or not etype.strip():
        raise ValueError(f"{prefix}event_type must be a non-empty string")

    actor = event["actor"]
    if not isinstance(actor, str) or not actor.strip():
        raise ValueError(f"{prefix}actor must be a non-empty string")

    ts = event["timestamp"]
    if not isinstance(ts, str) or not ts.strip():
        raise ValueError(f"{prefix}timestamp must be a non-empty ISO datetime string")

    b_stat = event["before_status"]
    if b_stat is not None and b_stat not in ALLOWED_STATUSES:
        raise ValueError(f"{prefix}invalid before_status '{b_stat}'")

    a_stat = event["after_status"]
    if a_stat is not None and a_stat not in ALLOWED_STATUSES:
        raise ValueError(f"{prefix}invalid after_status '{a_stat}'")

    details = event["details"]
    if not isinstance(details, (str, dict)):
        raise ValueError(f"{prefix}details must be a string or dictionary")


def validate_v2_payload(data: dict) -> None:
    """Validate full Schema Version 2 root structure, ticket integrity, and event relations."""
    if not isinstance(data, dict):
        raise ValueError(
            f"Corrupted data file: root JSON structure must be a list of tickets or v2 object, found {type(data).__name__}"
        )

    if "schema_version" not in data:
        raise ValueError("Corrupted data file: missing 'schema_version' field")

    version = data["schema_version"]
    if not isinstance(version, int) or isinstance(version, bool) or version != SCHEMA_VERSION:
        raise ValueError(f"Corrupted data file: unsupported schema_version '{version}', expected {SCHEMA_VERSION}")

    if "tickets" not in data or not isinstance(data["tickets"], list):
        raise ValueError("Corrupted data file: 'tickets' must be a list")

    if "events" not in data or not isinstance(data["events"], list):
        raise ValueError("Corrupted data file: 'events' must be a list")

    seen_ticket_ids = set()
    for idx, ticket in enumerate(data["tickets"]):
        validate_ticket(ticket, idx)
        tid = ticket["id"]
        if tid in seen_ticket_ids:
            raise ValueError(f"Corrupted data file: duplicate ticket ID '{tid}' at index {idx}")
        seen_ticket_ids.add(tid)

    seen_event_ids = set()
    for idx, event in enumerate(data["events"]):
        validate_event(event, idx, valid_ticket_ids=seen_ticket_ids)
        eid = event["event_id"]
        if eid in seen_event_ids:
            raise ValueError(f"Corrupted data file: duplicate event ID '{eid}' at index {idx}")
        seen_event_ids.add(eid)


def load_v2(filepath: str = DEFAULT_DATA_PATH) -> dict:
    """Load CampusFlow Schema Version 2 JSON data.

    Returns:
        dict: {"schema_version": 2, "tickets": list[dict], "events": list[dict]}

    Raises:
        ValueError: If file is malformed, has invalid schema, or fails validation.
    """
    if not os.path.exists(filepath):
        return {"schema_version": SCHEMA_VERSION, "tickets": [], "events": []}

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Corrupted JSON in data file '{filepath}': {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Failed to read data file '{filepath}': {exc}") from exc

    validate_v2_payload(data)
    return data


def save_v2(tickets: list[dict], events: list[dict], filepath: str = DEFAULT_DATA_PATH) -> None:
    """Save tickets and events using Schema Version 2 with atomic replacement.

    Atomic write process:
        1. Validate full payload structure before opening or modifying disk.
        2. Ensure destination directory exists.
        3. Write formatted JSON to a temporary file in the same directory.
        4. Flush and sync file descriptor to physical storage.
        5. Atomically replace the target file with the temporary file (os.replace).
    """
    if not isinstance(tickets, list):
        raise TypeError(f"Tickets must be a list, received {type(tickets).__name__}")
    if not isinstance(events, list):
        raise TypeError(f"Events must be a list, received {type(events).__name__}")

    payload = {
        "schema_version": SCHEMA_VERSION,
        "tickets": tickets,
        "events": events,
    }

    validate_v2_payload(payload)

    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)
    target_dir = directory if directory else "."

    temp_file = tempfile.NamedTemporaryFile("w", dir=target_dir, delete=False, encoding="utf-8")
    temp_path = temp_file.name
    try:
        json.dump(payload, temp_file, indent=2, default=_json_serial)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        os.replace(temp_path, filepath)
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def load_tickets(filepath: str = DEFAULT_DATA_PATH) -> list[dict]:
    """Compatible ticket loader supporting both legacy list files and Schema Version 2."""
    if not os.path.exists(filepath):
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Corrupted JSON in data file '{filepath}': {exc}") from exc
    except OSError as exc:
        raise ValueError(f"Failed to read data file '{filepath}': {exc}") from exc

    if isinstance(data, list):
        for idx, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(
                    f"Corrupted data file '{filepath}': item at index {idx} is not a valid ticket dictionary"
                )
        return data

    if isinstance(data, dict):
        if "schema_version" in data:
            if data["schema_version"] == SCHEMA_VERSION and "tickets" in data and isinstance(data["tickets"], list):
                return data["tickets"]
            validate_v2_payload(data)
            return data["tickets"]
        raise ValueError(
            f"Corrupted data file '{filepath}': root JSON structure must be a list of tickets, found dict"
        )

    raise ValueError(
        f"Corrupted data file '{filepath}': root JSON structure must be a list of tickets, found {type(data).__name__}"
    )


def save_tickets(tickets: list[dict], filepath: str = DEFAULT_DATA_PATH, events: list[dict] | None = None) -> None:
    """Compatible ticket saver persisting data atomically as Schema Version 2."""
    if not isinstance(tickets, list):
        raise TypeError(f"Tickets must be a list, received {type(tickets).__name__}")

    for idx, item in enumerate(tickets):
        if not isinstance(item, dict):
            raise ValueError(f"All ticket items must be dictionaries, item at index {idx} is {type(item).__name__}")

    if events is None:
        if os.path.exists(filepath):
            try:
                existing = load_v2(filepath)
                events = existing.get("events", [])
            except Exception:
                events = []
        else:
            events = []

    directory = os.path.dirname(filepath)
    if directory:
        os.makedirs(directory, exist_ok=True)
    target_dir = directory if directory else "."

    payload = {
        "schema_version": SCHEMA_VERSION,
        "tickets": tickets,
        "events": events,
    }

    temp_file = tempfile.NamedTemporaryFile("w", dir=target_dir, delete=False, encoding="utf-8")
    temp_path = temp_file.name
    try:
        json.dump(payload, temp_file, indent=2, default=_json_serial)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        os.replace(temp_path, filepath)
    except Exception:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        raise


def migrate_v1_to_v2(v1_filepath: str, v2_filepath: str | None = None) -> dict:
    """Explicitly migrate legacy list-style JSON to Schema Version 2.

    The original v1_filepath is preserved unchanged.
    """
    if not os.path.exists(v1_filepath):
        raise ValueError(f"Legacy data file '{v1_filepath}' does not exist")

    with open(v1_filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Legacy data file '{v1_filepath}' must be a list, found {type(data).__name__}")

    for idx, item in enumerate(data):
        validate_ticket(item, idx)

    v2_payload = {
        "schema_version": SCHEMA_VERSION,
        "tickets": data,
        "events": [],
    }

    if v2_filepath:
        save_v2(data, [], v2_filepath)

    return v2_payload
