# CampusFlow

CampusFlow is a robust command-line helpdesk ticket management system built with Python's standard library. It enables campus technical support staff to record, prioritize, assign, track, queue, and report on technical support incidents.

This project is part of the **AI-Native Engineering Sprint**.

---

## Team Roles & Ownership

The application is co-developed by a two-engineer team:

- **Engineer A (Theophilus Jacob / @tjayokanmi)**:
  - Ticket creation (`create_ticket`) and unique sequential ID generation (`generate_ticket_id`).
  - Input validation (non-empty titles, valid categories, positive integer user counts).
  - Priority calculation engine (`calculate_priority`).
  - Ticket creation and priority test suites (`test_priority.py`, `test_tickets.py`).

- **Engineer B (Terna Peter / @Tena-byte)**:
  - Ticket assignment (`assign_ticket`).
  - Ticket lifecycle workflow state machine (`update_status`) and explicit reopening (`reopen_ticket`).
  - Prioritized work queue with numeric ID tie-breaking (`get_work_queue`).
  - System reporting and aggregate metrics (`generate_report`).
  - Workflow, queue, and reporting test suites (`test_workflow.py`, `test_reports.py`).

- **Shared Responsibilities**:
  - Safe JSON persistence with atomic replacement (`campusflow/storage.py`, `test_storage.py`).
  - Interactive CLI integration (`main.py`).
  - System architecture documentation (`docs/design-decisions.md`) and AI learning logs (`docs/ai-learning-log.md`).

---

## Features (F1–F7)

- **F1 — Ticket Creation**: Create support requests with title, category, urgency, and affected users. Automatically computes priority using rule hierarchy.
- **F2 — List & View Details**: Browse all active and resolved tickets, or inspect individual ticket details.
- **F3 — Assignment**: Assign tickets to staff members; prevents whitespace-only names and rejects assigning resolved tickets without reopening.
- **F4 — Workflow Lifecycle**: Enforces state machine (`open` -> `in_progress` -> `resolved`). Disallows moving to `in_progress` without assignment, forbids direct resolution from `open`, and requires explicit reopening for `resolved` tickets.
- **F5 — Work Queue**: Displays active, unresolved tickets sorted by priority (`critical` > `high` > `medium` > `low`) with deterministic tie-breaking based on numeric ticket IDs (`T002` before `T010`).
- **F6 — Reports**: Generates summary statistics including total ticket count and complete breakdowns across all valid statuses and priorities (preserving zero-count entries).
- **F7 — JSON Persistence**: Persists tickets to `data/tickets.json` across sessions using atomic file replacement (`tempfile` + `os.replace`). Handles missing files gracefully on first run and rejects corrupted or malformed JSON without silent data loss.

---

## Architecture & Project Structure

```text
campusflow-ruby/
├── campusflow/
│   ├── __init__.py
│   ├── priority.py         # Priority calculation engine (Engineer A)
│   ├── tickets.py          # Ticket creation & ID generation (Engineer A)
│   ├── workflow.py         # Assignment, lifecycle state machine, work queue (Engineer B)
│   ├── reports.py          # Reporting metrics (Engineer B)
│   └── storage.py          # Atomic JSON persistence (Shared)
├── tests/
│   ├── __init__.py
│   ├── test_priority.py    # Priority engine tests
│   ├── test_tickets.py     # Ticket creation & validation tests
│   ├── test_workflow.py    # Assignment, workflow, and queue tests
│   ├── test_reports.py     # Reporting tests
│   └── test_storage.py     # JSON persistence tests
├── docs/
│   ├── design-decisions.md # Architectural agreements & function contracts
│   └── ai-learning-log.md  # Deliberate AI learning records & reflection prompts
├── data/                   # Local application runtime data (git-ignored)
│   └── tickets.json
├── main.py                 # CLI entry point
├── README.md
└── .gitignore
```

---

## Getting Started

### Prerequisites
- Python 3.10+ (Standard library only; no external dependencies required)

### Running the Application

Run the interactive CLI:

```bash
python3 main.py
```

### Running Automated Tests

Run the complete automated test suite using `unittest`:

```bash
python3 -m unittest discover -s tests -v
```

All 96 automated tests should pass:
- `test_priority.py`: 1 test (covering priority calculation boundaries)
- `test_tickets.py`: 7 tests (creation validation, boundary checks, ID generation)
- `test_workflow.py`: 22 tests (assignment, transition matrix, unassigned guards, reopening, queue sorting, tie-breaking)
- `test_reports.py`: 8 tests (empty lists, mixed counts, zero-count preservation, mutation checks, SLA metrics)
- `test_sla.py`: 16 tests (SLA durations, UTC validation, boundary thresholds)
- `test_escalation.py`: 10 tests (idempotent escalation, reopening cycles, boundary thresholds, non-mutation)
- `test_storage.py`: 23 tests (v1 legacy & v2 schema validation, round trips, corruption handling, relational checks, ID continuity, migration)
- `test_operations.py`: 6 tests (audited operations, rollback on failure)
- `test_knowledge_lab.py`: 3 tests (knowledge lab evaluation and scoring)

---

## Known Limitations & Considerations

1. **Terminal-Only Interface**: CampusFlow is designed as a focused command-line tool using standard terminal input.
2. **Local Single-File Storage**: Persistence uses a local JSON file (`data/tickets.json`). For multi-user concurrent production setups, a database backend with transaction locking would be recommended.
3. **Staff Directory**: Staff names are currently validated as non-empty strings. A dedicated staff directory entity could be introduced in a future sprint.
