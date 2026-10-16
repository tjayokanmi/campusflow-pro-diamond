# CampusFlow: AI Learning Log

This document records the deliberate AI-assisted learning loops completed by the engineering team during the CampusFlow sprint, following Phase 3 and Phase 4 of the sprint requirements.

> **Note for Human Fellows**:
> Per sprint guidelines, do not fabricate AI interactions or verification results. Below are structured templates containing real technical concepts explored, experiments run, and placeholders for individual fellow reflection and defence preparation.

---

## Engineer B (Terna Peter / Tena-byte) Learning Loops

### Learning Loop 1: Atomic File Replacement for Safe JSON Persistence
- **Concept / Question**:
  - What happens if a program crashes while writing directly to `data/tickets.json` with `json.dump()`?
  - How can Python standard library achieve atomic file replacement without third-party dependencies?
- **AI Explanation Summary**:
  - Writing directly to an existing file (`open('data/tickets.json', 'w')`) empties or truncates the file immediately. If the process terminates abruptly before writing completes, the data is corrupted or lost.
  - The standard approach on POSIX and modern Windows systems is to write full content to a temporary file in the same directory (using `tempfile.NamedTemporaryFile(dir=..., delete=False)`), flush and sync to disk, and then perform an atomic rename using `os.replace(temp_path, target_path)`.
- **Tiny Experiment**:
  - Created a temporary file in Python, dumped test JSON, and called `os.replace` to overwrite a dummy target file.
  - Verified that `os.replace` completes atomically on POSIX filesystem and target content is intact.
- **Verification & Outcome**:
  - Implemented in `campusflow/storage.py` using `tempfile.NamedTemporaryFile` + `os.replace`.
  - Verified with automated tests in `tests/test_storage.py` that invalid data never corrupts existing state.
- **Fellow Reflection (Placeholder for human fellow to personalize)**:
  - *Reflection prompt*: Explain in your own words why `os.replace` is safer than standard `open(file, 'w')`.

---

### Learning Loop 2: Multi-Criteria Queue Sorting & Deterministic Tie-Breaking
- **Concept / Question**:
  - How do we sort a list of dictionaries with custom priority ranks (`critical` > `high` > `medium` > `low`) while breaking ties using the numeric ID (`T002` before `T010`), and without mutating the original collection?
- **AI Explanation Summary**:
  - Use Python's built-in `sorted()` function with a custom `key` callable.
  - Map priority strings to integer ranks: `{"critical": 0, "high": 1, "medium": 2, "low": 3}`.
  - Extract the numeric ticket ID by parsing digits from the ID string: `int(ticket["id"][1:])`.
  - Return a tuple `(priority_rank, numeric_id)` as the sort key. Python compares tuples lexicographically: first comparing priority ranks, and using numeric IDs for ties.
- **Tiny Experiment**:
  - Input list: `[{"id": "T010", "priority": "high"}, {"id": "T002", "priority": "high"}]`.
  - Tested `sorted(records, key=lambda t: (PRIORITY_RANK[t["priority"]], int(t["id"][1:])))`.
  - Result: `T002` correctly placed before `T010`. String sorting would place `"T010"` before `"T002"` because `'0'` < `'2'`, whereas numeric comparison `2 < 10` places `T002` first.
- **Critical Evaluation of AI Suggestion**:
  - *Initial AI suggestion*: Suggested simple string sorting on ticket ID: `t["id"]`.
  - *Identified flaw*: Lexicographical string comparison fails when ID numbers differ in digit length (e.g. `"T100"` vs `"T99"`).
  - *Correction applied*: Parsed the numeric portion explicitly as `int(ticket["id"][1:])`.
- **Fellow Reflection (Placeholder for human fellow to personalize)**:
  - *Reflection prompt*: Be prepared to explain to the examiner why numeric parsing is required for ticket ID tie-breaking.

---

### Learning Loop 3: State Machine Validation & Guarding Against Workflow Bypasses
- **Concept / Question**:
  - How should we enforce strict state transitions between `open`, `in_progress`, and `resolved` so that helper functions (`assign_ticket`, `update_status`, `reopen_ticket`) do not bypass one another?
- **AI Explanation Summary**:
  - Treat ticket lifecycle as a finite state machine:
    - `open` -> `in_progress` (only when `assigned_to` is populated).
    - `in_progress` -> `resolved`.
    - `open` -> `resolved` is strictly disallowed.
    - `resolved` -> `open` is only allowed via explicit `reopen_ticket()`.
    - No direct mutations or assignments on `resolved` tickets without reopening.
- **Critical Evaluation of AI Suggestion**:
  - *Initial AI suggestion*: A generic status update function allowing any target status as long as `target in ALLOWED_STATUSES`.
  - *Identified flaw*: This would allow moving directly from `open` to `resolved`, or assigning/modifying already resolved tickets without explicit reopening.
  - *Correction applied*: Enforced explicit transition matrix and prohibited ordinary status modifications on resolved tickets.
- **Fellow Reflection (Placeholder for human fellow to personalize)**:
  - *Reflection prompt*: Explain the difference between updating status and explicitly reopening a ticket during defence.

---

## Engineer A (Theophilus Jacob / tjayokanmi) Learning Loops

### Learning Loop 1: Timezone-Aware UTC Enforcement and SLA Boundary Logic
- **Concept / Question**:
  - Why is comparing naive `datetime` with timezone-aware `datetime` disallowed in Python, and how do we strictly validate that inputs have a UTC offset of zero?
  - At the exact minute a deadline expires (e.g. 60 minutes after ticket creation), should a ticket be classified as overdue or on-time?
- **AI Explanation Summary**:
  - Python raises `TypeError: can't compare offset-naive and offset-aware datetimes` to prevent timezone ambiguity.
  - To enforce UTC strictly: verify `dt.tzinfo is not None and dt.utcoffset() is not None`, then check `dt.utcoffset() == datetime.timedelta(0)`.
  - Service Level Agreements define deadlines as the boundary until which service is compliant. Therefore, `due_at == now` is compliant (not overdue). A ticket is overdue strictly when `due_at < now`.
- **Tiny Experiment**:
  - Tested `is_overdue({"due_at": now, "status": "open"}, now)`.
  - Confirmed `now < now` evaluates to `False`, correctly preventing premature escalation at the exact deadline second.
- **Verification & Outcome**:
  - Implemented in `campusflow/sla.py` (`calculate_due_at`, `is_overdue`).
  - Tested in `tests/test_sla.py` and `tests/test_escalation.py` (`test_critical_deadline_boundary_60_and_61_minutes`).
- **Fellow Reflection**:
  - *Takeaway*: Using explicit UTC offset checks (`utcoffset() == timedelta(0)`) prevents subtle bugs where non-UTC timezone-aware timestamps (like UTC+2) bypass naive checks but calculate inaccurate duration deltas.

---

### Learning Loop 2: Escalation-Cycle Idempotency and Critical Evaluation of AI Advice
- **Concept / Question**:
  - How do we implement idempotent escalation checks so that repeated background runs do not spam duplicate escalation events, while still allowing a ticket to be legitimately re-escalated if it is reopened after resolution?
- **Initial AI Suggestion**:
  - The AI suggested adding an `is_escalated: bool` field directly to the ticket dictionary: `ticket["is_escalated"] = True` upon escalation, and resetting `ticket["is_escalated"] = False` upon reopening.
- **Critical Evaluation & Flaw Identification**:
  - *Identified flaw*: Mutating ticket fields during `escalate_overdue` directly violates the engineering requirement that escalation must not change ticket priority, status, or assignment. Furthermore, in-memory flags do not persist across restarts unless added to the ticket schema, breaking compatibility with existing Phase 1 tickets.
  - *Correction applied*: Rejected the mutable ticket flag suggestion. Instead, implemented cycle derivation from the append-only event history:
    - Iterate chronologically through `events` for `ticket_id`.
    - If a reopening event is encountered (`before_status == "resolved"` and `after_status == "open"`, or `event_type` is `"REOPEN"`), reset `has_escalation = False`.
    - If an escalation event is encountered (`event_type` matching `"escalate"` or `"escalated"`), set `has_escalation = True`.
- **Tiny Experiment & Verification**:
  - Created a test scenario in `tests/test_escalation.py` (`test_reopen_starts_new_sla_cycle_and_allows_re_escalation`):
    1. Ticket escalates in cycle 1 -> 1 event recorded.
    2. Repeated check in cycle 1 -> 0 new events, reported in `already_escalated`.
    3. Ticket resolved and reopened at new timestamp -> new `due_at` calculated.
    4. New deadline breached in cycle 2 -> 2nd escalation event recorded.
    5. Repeated check in cycle 2 -> 0 new events, reported in `already_escalated`.
  - Test passed cleanly, proving cycle idempotency without ticket mutation.

---

### Learning Loop 3: Schema Version 2 JSON Persistence & Relational Validation
- **Concept / Question**:
  - How should we transition CampusFlow from a raw list of tickets to an extensible Schema Version 2 object (`{"schema_version": 2, "tickets": [], "events": []}`) while guaranteeing atomicity and relational integrity?
- **AI Explanation Summary**:
  - Validating foreign-key-style relations in JSON storage requires validating the parent records (`tickets`) first, collecting valid primary keys (`ticket["id"]`), and then validating that child records (`events`) reference existing parent IDs.
  - In-memory validation must occur before writing any bytes to disk to ensure invalid data never touches physical storage.
- **Tiny Experiment**:
  - Attempted saving an event referencing ticket ID `"T999"` when only `"T001"` existed.
  - Verified that `save_v2` immediately raised `ValueError("Event references unknown ticket ID 'T999'")`, leaving the target file intact.
- **Verification & Outcome**:
  - Implemented `save_v2`, `load_v2`, `validate_v2_payload`, and `migrate_v1_to_v2` in `campusflow/storage.py`.
  - Added 16 tests in `TestStorageV2` within `tests/test_storage.py` covering round trips, corruption handling, relational checks, and sequential ID continuity.
- **Fellow Reflection**:
  - *Takeaway*: Atomic file replacement (`os.replace`) coupled with pre-write schema validation guarantees zero file corruption during power cuts, unexpected process termination, or invalid input submissions.

