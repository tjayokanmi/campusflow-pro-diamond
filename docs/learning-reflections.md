# CampusFlow Pro — Engineering Learning Reflections

**Date:** October 16, 2026  
**Repository:** https://github.com/tjayokanmi/campusflow-pro-diamond  
**Authors:** Engineer A & Engineer B  

---

## 1. Overview & Purpose

Per the **CampusFlow Pro Advanced Engineering Challenge** (§7, §13), after completing the CLI Engineering Knowledge Lab quiz, each engineer must document their learning reflections using the mandatory structured inquiry framework:
> *"I first believed..., I checked..., I changed my understanding because..."*

Additionally, each engineer must document at least one major architectural or design mistake encountered during development and describe how empirical evidence and test verification changed their engineering decisions.

---

## 2. Engineer A — SLA Engine, UTC Handling & Data Integrity

### 2.1 Quiz Question Reflection: Q1 — Critical SLA Boundary (`due` vs. `overdue`)
- **Question:** *Is a critical ticket overdue exactly 60 minutes after creation?*
- **Structured Reflection:**
  - **I first believed** that an SLA deadline was a soft threshold where a ticket could be treated as overdue as soon as the clock reached `due_at` (i.e., `now >= due_at`), assuming operational escalation should happen immediately at the 60th minute.
  - **I checked** the specification contract in Section 3 and tested boundary conditions with `datetime.datetime`:
    ```python
    cycle_start = datetime(2026, 3, 30, 10, 0, tzinfo=timezone.utc)
    due_at = cycle_start + timedelta(minutes=60) # 11:00 UTC
    now_at_deadline = datetime(2026, 3, 30, 11, 0, tzinfo=timezone.utc)
    now_past_deadline = datetime(2026, 3, 30, 11, 1, tzinfo=timezone.utc)
    ```
    At `11:00:00`, the ticket is at its deadline, meaning the allotted resolution window has not yet been exceeded.
  - **I changed my understanding because** an SLA deadline defines the promised duration during which work may be completed without breach. A ticket is overdue only when the current UTC timestamp is **strictly later** than `due_at` (`due_at < now`). Treating `due_at == now` as overdue prematurely flags on-time work as failing SLA commitments. I encoded this strict inequality into [`is_overdue`](file:///home/student/campusflow-ruby/campusflow/sla.py#L28-L63) and verified it in [`test_deadline_exactly_now_is_not_overdue`](file:///home/student/campusflow-ruby/tests/test_escalation.py#L54-L65).

### 2.2 Quiz Question Reflection: Q5 — Repeated Escalation Idempotency Across Reopened Cycles
- **Question:** *What happens if escalation is checked three times in the same cycle?*
- **Structured Reflection:**
  - **I first believed** that checking escalations could simply check if the ticket had ever been escalated by inspecting whether any `escalated` event existed in the global history list.
  - **I checked** how ticket reopening behaves: when a resolved ticket is reopened, it initiates a fresh SLA cycle. If the ticket later breaches its new deadline, inspecting only global history would permanently prevent it from escalating in its new cycle.
  - **I changed my understanding because** escalation idempotency must be strictly scoped to the *current SLA cycle*. A ticket overdue in its current cycle creates exactly one escalation event; running escalation checks 3 or 10 times in that cycle must append at most 1 event. However, upon resolution and subsequent reopening, a new cycle begins, resetting escalation eligibility while preserving all historical audit records.

### 2.3 Engineer A Design Mistake Encountered & How Evidence Changed Thinking
- **Mistake:** Attempting to store escalation state as a mutable boolean flag (`ticket["is_escalated"] = True`) directly on the ticket dictionary during escalation.
- **Evidence & Failure Mode:**
  1. *Specification violation:* Section 4 and Section 12 explicitly stipulate that escalation must **never** mutate ticket attributes (priority, status, assigned staff, or arbitrary ticket fields).
  2. *Reopening cycle desynchronization:* If `is_escalated` is stored on the ticket, reopening requires manual mutation to reset it back to `False`. If that reset step is missed, corrupted, or bypassed by external workflow transitions, the ticket is permanently barred from future escalations.
  3. *Audit inconsistency:* The source of truth for all lifecycle state in Phase 2 is the append-only audit log.
- **Resolution:** Removed `is_escalated` from ticket attributes. In [`escalate_overdue`](file:///home/student/campusflow-ruby/campusflow/sla.py#L64-L154), escalation eligibility is derived dynamically by scanning the ticket's events chronologically: any `REOPEN` event resets the cycle's escalation flag to `False`, while any `ESCALATE` event sets it to `True`. The ticket object remains completely immutable during escalation checks.

---

## 3. Engineer B — Persistence, Duplicate Detection & Audit Integrity

### 3.1 Quiz Question Reflection: Q8 — Security Risks of Dynamic Deserialization (`eval()` vs. `json.loads`)
- **Question:** *An AI suggests using eval() to load JSON. What should you do?*
- **Structured Reflection:**
  - **I first believed** that for small, trusted local files, `eval()` might be an acceptable shortcut to quickly convert Python dictionary string representations into native dicts without schema parsing.
  - **I checked** the security implications and OWASP injection guidelines: `eval()` executes arbitrary code. If a saved data file is modified by a malicious actor or contains corrupted text with executable expressions (e.g., `__import__('os').system(...)`), the CLI application immediately suffers a remote code execution vulnerability.
  - **I changed my understanding because** data persistence must strictly separate data deserialization from code execution. JSON parsing using `json.loads()` with strict schema versioning and schema validation ([`validate_v2_payload`](file:///home/student/campusflow-ruby/campusflow/storage.py#L143-L200)) safely rejects malformed or malicious structures without executing unintended side-effects.

### 3.2 Quiz Question Reflection: Q9 — Duplicate Detection vs. Accidental Data Loss
- **Question:** *What should happen when a new ticket matches an unresolved ticket's normalized title and category?*
- **Structured Reflection:**
  - **I first believed** that duplicate detection should automatically reject or drop incoming tickets that match existing unresolved tickets to keep the ticket queue clean.
  - **I checked** real-world IT service desk workflows: users frequently report the same campus-wide outage (e.g. "Wi-Fi Down in Library" by multiple faculty members and students). Silently dropping or blocking a submission prevents helpdesk operators from logging affected user counts or unique context.
  - **I changed my understanding because** duplicate detection should serve as a high-visibility warning with confirmation rather than an aggressive silent block. Prompting the operator with normalized matches allows them to either link/confirm the ticket or cancel the duplicate submission gracefully.

### 3.3 Engineer B Design Mistake Encountered & How Evidence Changed Thinking
- **Mistake:** Calculating the next ticket ID using `len(tickets) + 1` (e.g., `f"T{len(tickets) + 1:03d}"`).
- **Evidence & Failure Mode:**
  1. *Deletion or Non-Sequential IDs:* When a dataset contains gaps (e.g. tickets `T001`, `T002`, `T015`), `len(tickets)` is 3. The naive formula generates `T004`, which would eventually collide with `T015` as more tickets are created.
  2. *Save/Load Round-Trip Collision:* When reloading tickets from a dataset where higher IDs exist or where tickets were archived, `len(tickets) + 1` caused duplicate ticket ID collisions during test runs.
- **Resolution:** Replaced the count-based approach with numeric suffix extraction and maximum tracking in [`generate_ticket_id`](file:///home/student/campusflow-ruby/campusflow/tickets.py#L110-L125):
  ```python
  def generate_ticket_id(records):
      if not records:
          return "T001"
      numbers = [
          int(r["id"][1:])
          for r in records
          if isinstance(r, dict) and isinstance(r.get("id"), str)
          and r["id"].startswith("T") and r["id"][1:].isdigit()
      ]
      return f"T{max(numbers) + 1:03d}" if numbers else "T001"
  ```
  Verified through [`test_v2_id_continuity_after_reload`](file:///home/student/campusflow-ruby/tests/test_storage.py#L313-L330).

---

## 4. Summary Matrix of Acceptance Criteria & Test Evidence

| Domain | Responsible | Key Mechanism | Verification Unit Test |
| :--- | :--- | :--- | :--- |
| **SLA Boundary** | Engineer A | Strict inequality (`due_at < now`) | [`test_deadline_exactly_now_is_not_overdue`](file:///home/student/campusflow-ruby/tests/test_escalation.py#L54-L65) |
| **Escalation Idempotency** | Engineer A | Event-history derived cycle state | [`test_repeated_escalation_checks_produce_single_event`](file:///home/student/campusflow-ruby/tests/test_escalation.py#L173-L194) |
| **Cycle Reset on Reopen** | Engineer A | SLA reset at reopen timestamp | [`test_reopening_resets_sla_and_allows_re_escalation`](file:///home/student/campusflow-ruby/tests/test_escalation.py#L195-L225) |
| **Schema v2 Persistence** | Engineer A | Atomic write (`tempfile` + `os.replace`) | [`test_v2_atomic_replacement_failure_cleans_up_and_preserves_original`](file:///home/student/campusflow-ruby/tests/test_storage.py#L330-L345) |
| **ID Continuity** | Engineer A | Max numeric ID tracking across reloads | [`test_v2_id_continuity_after_reload`](file:///home/student/campusflow-ruby/tests/test_storage.py#L313-L330) |
| **Audit Log Integrity** | Engineer B | Append-only event history | [`test_invalid_operations_produce_no_unintended_events`](file:///home/student/campusflow-ruby/tests/test_escalation.py#L247-L274) |
| **Knowledge Lab Quiz** | Both | Interactive 10-question CLI quiz & JSON sessions | [`test_perfect_score`](file:///home/student/campusflow-ruby/tests/test_knowledge_lab.py#L8-L15) |
