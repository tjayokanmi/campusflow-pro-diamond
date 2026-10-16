# CampusFlow: Architecture & Design Decisions

## 1. Overview and Engineering Roles

CampusFlow is a Python command-line helpdesk application built collaboratively by two engineers:
- **Engineer A (Theophilus Jacob / tjayokanmi)**: Ticket creation (`create_ticket`), input validation, priority calculation (`calculate_priority`), and corresponding unit tests.
- **Engineer B (Terna Peter / Tena-byte)**: Ticket assignment (`assign_ticket`), ticket workflow transitions (`update_status`), explicit ticket reopening (`reopen_ticket`), priority-ordered work queue (`get_work_queue`), ticket reporting (`generate_report`), and corresponding unit tests.
- **Shared Ownership**: JSON persistence (`campusflow/storage.py`), CLI menu integration (`main.py`), and documentation.

---

## 2. Shared Data Model

Tickets are represented as standard Python dictionaries contained within a list (`list[dict]`).
Each ticket contains the following canonical 8 fields:

```python
{
    "id": "T001",                   # String: sequential identifier, e.g. "T001", "T002"
    "title": "Campus Wi-Fi down",   # String: non-empty, trimmed title
    "category": "Network",          # String: "Network", "Hardware", "Software", "Other"
    "urgency": "high",              # String: "low", "medium", "high"
    "affected_users": 15,           # Integer: positive integer (>= 1)
    "priority": "critical",         # String: "critical", "high", "medium", "low"
    "status": "open",               # String: "open", "in_progress", "resolved"
    "assigned_to": None             # String or None: staff member name or None
}
```

Tickets are initially created with `status="open"` and `assigned_to=None`.

---

## 3. Function Contracts & Interfaces

### 3.1 Feature F3: Ticket Assignment (`campusflow.workflow`)
```python
def assign_ticket(tickets: list[dict], ticket_id: str, staff_name: str) -> dict:
```
- **Inputs**:
  - `tickets`: List of ticket dictionaries.
  - `ticket_id`: Target ticket ID (e.g., `"T001"`).
  - `staff_name`: Name of assigned staff member.
- **Preconditions / Validation**:
  - `ticket_id` must match an existing ticket in `tickets`. If not found, raises `ValueError("Ticket <id> not found")`.
  - `staff_name` must be a non-empty string when trimmed. If empty or whitespace-only, raises `ValueError("Staff name cannot be empty")`.
  - A ticket with status `"resolved"` cannot be assigned. If attempted, raises `ValueError("Cannot assign a resolved ticket; reopen the ticket first")`.
- **Side Effects & Return**:
  - Modifies the ticket's `"assigned_to"` field in-place with the trimmed staff name.
  - Returns the updated ticket dictionary.
  - Leaves the ticket unchanged if any validation check fails.

---

### 3.2 Feature F4: Ticket Workflow & Lifecycle (`campusflow.workflow`)
```python
def update_status(tickets: list[dict], ticket_id: str, new_status: str) -> dict:
def reopen_ticket(tickets: list[dict], ticket_id: str) -> dict:
```
- **Allowed Statuses**: `"open"`, `"in_progress"`, `"resolved"`.
- **Workflow State Rules**:
  - Normalized status inputs (whitespace-stripped and lowercased).
  - `ticket_id` must match an existing ticket; otherwise raises `ValueError`.
  - Unrecognized status strings raise `ValueError("Invalid status: <status>")`.
  - An `"open"` ticket can move to `"in_progress"` **only** if `assigned_to` is not `None` and not empty. If unassigned, raises `ValueError("Ticket must be assigned before moving to in_progress")`.
  - An `"in_progress"` ticket can move to `"resolved"`.
  - An `"open"` ticket **cannot** move directly to `"resolved"`. Raises `ValueError("Cannot resolve an open ticket directly; must be in_progress first")`.
  - A `"resolved"` ticket **cannot** be modified via `update_status`. Any transition attempt on a resolved ticket raises `ValueError("Resolved tickets cannot be modified; use reopen_ticket")`.
  - Same-status transitions raise `ValueError("Ticket is already in '<status>' status")`.
- **Explicit Reopening (`reopen_ticket`)**:
  - Finds ticket by `ticket_id`.
  - Can **only** be performed on tickets whose current status is `"resolved"`. If ticket is not resolved, raises `ValueError("Only resolved tickets can be reopened")`.
  - Sets `ticket["status"] = "open"`.
  - Preserves existing `assigned_to` information so assigned staff can resume work or be reassigned.
  - Returns the updated ticket dictionary.

---

### 3.3 Feature F5: Work Queue (`campusflow.workflow`)
```python
def get_work_queue(tickets: list[dict]) -> list[dict]:
```
- **Filtering**:
  - Includes **only** tickets with status `"open"` or `"in_progress"`.
  - Strictly excludes `"resolved"` tickets.
- **Ordering**:
  - Primary sort: Priority in exact order: `"critical"` (rank 0) > `"high"` (rank 1) > `"medium"` (rank 2) > `"low"` (rank 3).
  - Secondary tie-breaker: Ascending numeric ticket ID (e.g., `"T002"` precedes `"T010"` by parsing the numeric portion `int(ticket_id[1:])`).
- **Policy for Unexpected Priority Values**:
  - If a ticket has an unknown or missing priority value not in the 4 canonical levels, `get_work_queue` raises `ValueError(f"Unexpected priority '{priority}' in ticket '{ticket_id}'")` to avoid silently misordering or corrupting the queue.
- **Side Effects**:
  - Non-destructive: returns a new sorted list without modifying the original collection order.
  - Handles empty input gracefully by returning `[]`.

---

### 3.4 Feature F6: Reports (`campusflow.reports`)
```python
def generate_report(tickets: list[dict]) -> dict:
```
- **Return Structure**:
  ```python
  {
      "total": int,
      "by_status": {
          "open": int,
          "in_progress": int,
          "resolved": int
      },
      "by_priority": {
          "critical": int,
          "high": int,
          "medium": int,
          "low": int
      }
  }
  ```
- **Requirements**:
  - Always includes all allowed statuses and priorities with integer count `0`, even if no tickets match.
  - For empty list `[]`, returns `total: 0` and all subcounts as `0`.
  - Does not mutate input list.

---

### 3.5 Feature F7: Shared JSON Persistence (`campusflow.storage`)
```python
def load_tickets(filepath: str = "data/tickets.json") -> list[dict]:
def save_tickets(tickets: list[dict], filepath: str = "data/tickets.json") -> None:
```
- **Loading Behavior**:
  - If `filepath` does not exist: returns empty list `[]` (fresh start).
  - If `filepath` exists and contains valid JSON list: returns loaded list.
  - If `filepath` contains malformed JSON or non-list root structure: raises `ValueError("Corrupted data file...")`. It **never** silently replaces corrupt data with an empty list.
- **Saving Behavior**:
  - Ensures parent directory exists (`os.makedirs`).
  - Uses atomic replacement (writes to a temporary file in the same directory, then calls `os.replace`) to protect against partial writes on crash or power loss.
- **Sequential Ticket IDs**:
  - Uses Engineer A's `generate_ticket_id(records)` logic.
  - When loading existing tickets on application startup, the highest existing numeric ID is preserved, guaranteeing unique sequential IDs across sessions.

---

## 4. Engineer A Integration Inspection & Coordination Items

During repository inspection of Engineer A's code in `campusflow/tickets.py` and `tests/test_priority.py`:
1. **Import Path in `campusflow/tickets.py`**:
   - Current line 1: `from priority import calculate_priority`.
   - Issue: When running tests or CLI from project root, raises `ModuleNotFoundError: No module named 'priority'`.
   - Proposed safe solution: Change to `from campusflow.priority import calculate_priority`.
2. **Missing Return Statement in `create_ticket`**:
   - `create_ticket` constructs `my_ticket` dict but omits `return my_ticket`.
   - Proposed safe solution: Add `return my_ticket`.
3. **Hardcoded ID in `create_ticket`**:
   - `create_ticket` hardcodes `"id": "T001"`.
   - Proposed safe solution: Support `records` parameter or pass existing tickets: `create_ticket(title, category, urgency, affected_users, records=None)`.
4. **Top-Level Print & Global Records in `campusflow/tickets.py`**:
   - `print(generate_ticket_id(records))` runs on module import, printing `"T008"`.
   - Proposed safe solution: Guard under `if __name__ == "__main__":` or remove scratch execution.
5. **Bare Assertions in `tests/test_priority.py`**:
   - Top-level `assert` statements fail with `NameError` under `python -m unittest discover` because `calculate_priority` is not imported and assertions are not inside a `unittest.TestCase`.
   - Proposed safe solution: Wrap assertions in a standard `unittest.TestCase` class with `from campusflow.priority import calculate_priority`.

---

## 5. Phase 2 Architecture & Design Decisions (Engineer A)

### 5.1 SLA Deadline Engine & Strict UTC Validation
- **Durations**:
  - `critical`: 60 minutes (`timedelta(hours=1)`)
  - `high`: 240 minutes (`timedelta(hours=4)`)
  - `medium`: 1,440 minutes (`timedelta(days=1)`)
  - `low`: 2,880 minutes (`timedelta(days=2)`)
- **Strict UTC Enforced**: All datetime arguments (`cycle_start`, `now`, `due_at`) must be timezone-aware with UTC offset 0 (`utcoffset() == timedelta(0)`). Naive datetimes or non-UTC offsets raise `ValueError`. Non-datetime types raise `TypeError`.
- **Strict Boundary Comparison**:
  - `is_overdue(ticket, now)` returns `status != "resolved" and due_at < now`.
  - Exactly at the deadline (`due_at == now`), a ticket is strictly **not overdue**. Only after passing the deadline (`due_at < now`) does it become overdue.

### 5.2 Escalation-Cycle Idempotency Strategy
- **Problem**: When `escalate_overdue` runs repeatedly, overdue tickets must not receive duplicate escalation events within the same SLA cycle. However, when a resolved ticket is reopened, it enters a new SLA cycle and must be eligible for escalation again if its new deadline passes.
- **Evaluated Strategies**:
  1. *Mutable in-memory ticket flag (`ticket["is_escalated"] = True`)*:
     - *Flaw*: Fails to survive session reloads unless serialized into ticket schema; introduces mutation into an operation that must not alter ticket attributes.
  2. *Strict Event Schema Pattern Matching (`event["event_type"] == "ESCALATE"`)*:
     - *Flaw*: Fragile against schema variations between modules or historical versions (e.g., uppercase `"ESCALATE"` vs lowercase `"escalated"`, string details vs dict details).
  3. *Chronological Event History Cycle Derivation (Chosen Strategy)*:
     - Scans `events` chronologically for `ticket_id`.
     - A reopening event (detected via `before_status="resolved" and after_status="open"`, or `event_type` containing "reopen") resets the cycle's escalation flag to `False`.
     - An escalation event (`event_type` matching "escalate" or "escalated") sets the flag to `True`.
     - *Trade-offs*: $O(N)$ scan over events list per ticket; negligible overhead given helpdesk scale, but provides complete crash resilience, schema tolerance, and guarantees that reopening permits re-escalation without deleting or altering previous audit events.
- **Side Effects**: Escalation creates an audit event (`event_type="escalated"`, `details="SLA deadline exceeded"`) and reports ticket IDs in `{"escalated": [...], "already_escalated": [...]}` without altering ticket priority, status, or assignee.

### 5.3 Reopening Semantics & SLA Reset
- When a ticket is reopened (`reopen_ticket` / `reopen_ticket_with_audit`):
  - `ticket["status"]` is set to `"open"`.
  - `ticket["created_at"]` remains strictly **unchanged**.
  - `ticket["due_at"]` is recalculated from the reopening timestamp using `calculate_due_at(priority, reopen_time)`.
  - `ticket["escalation_cycle"]` is incremented if present.
  - A `"REOPEN"` event is appended to the audit trail.

### 5.4 Schema Version 2 JSON Persistence
- **Structure**:
  ```json
  {
    "schema_version": 2,
    "tickets": [],
    "events": []
  }
  ```
- **Validation Pipeline**:
  - Root must be a `dict` with `schema_version == 2`.
  - Both `tickets` and `events` must be lists.
  - Every ticket is validated for required fields (`id`, `title`, `category`, `urgency`, `affected_users >= 1`, `priority`, `status`, `assigned_to`).
  - Ticket IDs must be unique across `tickets`.
  - Every event is validated for required fields (`event_id`, `ticket_id`, `event_type`, `actor`, `timestamp`, `before_status`, `after_status`, `details`).
  - Event IDs must be unique across `events`.
  - **Relational Integrity**: Every event's `ticket_id` must reference an existing ticket in `tickets`.
- **Atomicity & Crash Safety**:
  - Data is validated in-memory before file creation.
  - Formatted JSON is written to a temporary file via `tempfile.NamedTemporaryFile` in the same target directory.
  - Buffer is flushed and synced with `os.fsync`.
  - Destination file is replaced atomically via `os.replace`.
  - In case of write failure, the temporary file is unlinked and the destination remains untouched.
- **Ticket ID Continuity**:
  - `generate_ticket_id(records)` extracts numeric suffixes from all loaded tickets, takes `max()`, and formats the next sequential ID `f"T{max + 1:03d}"`. This guarantees strictly increasing, non-colliding IDs across reloads.

