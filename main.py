"""CampusFlow: Command-line Technical Support Ticket Management System."""

import sys
from copy import deepcopy
from datetime import datetime, timezone

from campusflow.operations import (
    create_ticket_with_audit,
    assign_ticket_with_audit,
    update_status_with_audit,
    reopen_ticket_with_audit,
)
from campusflow.duplicates import detect_duplicates
from campusflow.knowledge_lab import run_knowledge_lab
from campusflow.queues import sla_attention_queue
from campusflow.storage import load_v2, save_v2, DEFAULT_DATA_PATH
from campusflow.tickets import create_ticket
from campusflow.workflow import get_work_queue
from campusflow.reports import generate_report
from campusflow.history import get_ticket_history
from campusflow.sla import escalate_overdue

def print_ticket_summary(ticket: dict) -> None:
    """Print a single line summary of a ticket."""
    tid = ticket.get("id", "N/A")
    pri = ticket.get("priority", "N/A").upper()
    status = ticket.get("status", "N/A")
    assigned = ticket.get("assigned_to") or "Unassigned"
    title = ticket.get("title", "No Title")
    print(f"[{tid}] ({pri}) [{status}] Assigned: {assigned} | {title}")


def print_ticket_details(ticket: dict) -> None:
    """Print full details of a ticket dictionary."""
    print("\n" + "=" * 50)
    print(f"Ticket ID:        {ticket.get('id')}")
    print(f"Title:            {ticket.get('title')}")
    print(f"Category:         {ticket.get('category')}")
    print(f"Urgency:          {ticket.get('urgency')}")
    print(f"Affected Users:   {ticket.get('affected_users')}")
    print(f"Priority:         {ticket.get('priority')}")
    print(f"Status:           {ticket.get('status')}")
    print(f"Assigned To:      {ticket.get('assigned_to') or 'Unassigned'}")
    print(f"Created At:       {ticket.get('created_at', 'N/A')}")
    print(f"Updated At:       {ticket.get('updated_at', 'N/A')}")
    print(f"Due At:           {ticket.get('due_at', 'N/A')}")
    print(f"Escalation Cycle: {ticket.get('escalation_cycle', 0)}")
    print("=" * 50)


def handle_create_ticket(tickets: list[dict], data_path: str, events: list[dict] | None = None) -> None:
    """Validate, confirm duplicates, and atomically persist ticket and CREATE event."""
    if events is None:
        raise RuntimeError("Audit events are required for ticket creation")
    print("\n--- Create New Ticket ---")
    title = input("Enter ticket title/description: ")
    print("Allowed categories: Network, Hardware, Software, Other")
    category = input("Enter category: ")
    print("Allowed urgency levels: low, medium, high")
    urgency = input("Enter urgency: ")
    users_raw = input("Enter number of affected users: ")
    actor = input("Enter your name (operator): ").strip()
    try:
        affected_users = int(users_raw)
        candidate = create_ticket(title=title, category=category, urgency=urgency,
                                  affected_users=affected_users, records=tickets)
        duplicates = detect_duplicates(tickets, candidate["category"], candidate["title"])
        confirm_duplicate = False
        if duplicates:
            print(f"[Warning] Potential duplicate tickets: {', '.join(duplicates)}")
            confirmation = input("Do you still want to create this ticket? (yes/no): ").strip().lower()
            if confirmation != "yes":
                print("[Cancelled] Ticket creation cancelled.")
                return
            confirm_duplicate = True
        ticket = run_audited_operation(
            tickets, events, data_path, create_ticket_with_audit,
            title, category, urgency, affected_users, actor, confirm_duplicate,
            save_state=save_v2,
        )
        print(f"[Success] Ticket {ticket['id']} created with priority '{ticket['priority']}'.")
    except (ValueError, TypeError, OSError, RuntimeError) as err:
        print(f"[Error] Failed to create ticket: {err}")


def handle_list_tickets(tickets: list[dict]) -> None:
    """Display all tickets in the system."""
    print(f"\n--- All Tickets ({len(tickets)} total) ---")
    if not tickets:
        print("No tickets found in the system.")
        return
    for ticket in tickets:
        print_ticket_summary(ticket)


def handle_view_ticket(tickets: list[dict]) -> None:
    """Display full details for a specific ticket by ID."""
    print("\n--- View Ticket Details ---")
    tid = input("Enter ticket ID (e.g., T001): ").strip()
    match = None
    for t in tickets:
        if t.get("id") == tid:
            match = t
            break
    if not match:
        print(f"[Error] Ticket with ID '{tid}' not found.")
        return
    print_ticket_details(match)


def handle_assign_ticket(tickets: list[dict], events: list[dict], data_path: str,
                         save_state=None) -> None:
    """Assign a ticket and persist its audit event."""
    print("\n--- Assign Ticket ---")
    tid = input("Enter ticket ID to assign: ").strip()
    staff = input("Enter staff member name: ").strip()
    actor = input("Enter your name (operator): ").strip()
    try:
        updated = run_audited_operation(tickets, events, data_path,
                                        assign_ticket_with_audit, tid, staff, actor,
                                        save_state=save_state)
        print(f"[Success] Ticket {tid} assigned to '{updated.get('assigned_to')}'.")
    except (ValueError, TypeError, RuntimeError, OSError) as err:
        print(f"[Error] Assignment failed: {err}")


def handle_ticket_history(
    events: list[dict],
) -> None:
    """Display chronological audit history for a ticket."""

    print("\n--- Ticket History ---")

    ticket_id = input("Enter ticket ID: ").strip()

    history = get_ticket_history(events, ticket_id)

    if not history:
        print(f"No history found for ticket {ticket_id}.")
        return

    for event in history:
        print("-" * 50)
        print(f"Event ID:      {event['event_id']}")
        print(f"Event Type:    {event['event_type']}")
        print(f"Actor:         {event['actor']}")
        print(f"Timestamp:     {event['timestamp']}")
        print(f"Before Status: {event['before_status']}")
        print(f"After Status:  {event['after_status']}")
        print(f"Details:       {event['details']}")

def handle_update_status(tickets: list[dict], events: list[dict], data_path: str,
                         save_state=None) -> None:
    """Update ticket status and persist its audit event."""
    print("\n--- Update Ticket Status ---")
    tid = input("Enter ticket ID: ").strip()
    print("Allowed statuses: in_progress, resolved")
    new_status = input("Enter new status: ").strip()
    actor = input("Enter your name (operator): ").strip()
    try:
        updated = run_audited_operation(tickets, events, data_path,
                                        update_status_with_audit, tid, new_status, actor,
                                        save_state=save_state)
        print(f"[Success] Ticket {tid} status updated to '{updated.get('status')}'.")
    except (ValueError, TypeError, RuntimeError, OSError) as err:
        print(f"[Error] Status update failed: {err}")


def handle_reopen_ticket(tickets: list[dict], events: list[dict], data_path: str,
                         save_state=None) -> None:
    """Reopen a resolved ticket and persist its audit event."""
    print("\n--- Reopen Resolved Ticket ---")
    tid = input("Enter resolved ticket ID: ").strip()
    actor = input("Enter your name (operator): ").strip()
    try:
        updated = run_audited_operation(tickets, events, data_path,
                                        reopen_ticket_with_audit, tid, actor,
                                        save_state=save_state)
        print(f"[Success] Ticket {tid} reopened to '{updated.get('status')}'.")
    except (ValueError, TypeError, RuntimeError, OSError) as err:
        print(f"[Error] Reopening failed: {err}")


def handle_check_escalations(tickets: list[dict], data_path: str,
                             events: list[dict] | None = None) -> None:
    """Escalate overdue tickets and persist new events before publishing changes."""
    if events is None:
        raise RuntimeError("Audit events are required for escalation")
    now = datetime.now(timezone.utc)
    temp_tickets = deepcopy(tickets)
    temp_events = deepcopy(events)
    try:
        result = escalate_overdue(temp_tickets, temp_events, now, actor="Operator")
        escalated = result["escalated"]
        already = result["already_escalated"]
        if escalated:
            save_v2(temp_tickets, temp_events, data_path)
            tickets[:] = temp_tickets
            events[:] = temp_events
    except (ValueError, TypeError, OSError, RuntimeError) as err:
        print(f"[Error] Escalation check failed: {err}")
        return
    print("\n--- SLA Escalation Check ---")
    print(f"Timestamp (UTC):     {now.isoformat()}")
    print(f"Newly escalated:     {len(escalated)} ticket(s)")
    if escalated:
        print(f"  Ticket IDs:        {', '.join(escalated)}")
    print(f"Already escalated:   {len(already)} ticket(s)")
    if already:
        print(f"  Ticket IDs:        {', '.join(already)}")
    print("[Success] Audit events recorded and state saved." if escalated
          else "No new tickets escalated.")


def handle_work_queue(tickets: list[dict]) -> None:
    """Display active tickets ordered by priority and numeric ID."""
    print("\n--- Prioritized Work Queue (Unresolved) ---")
    try:
        queue = get_work_queue(tickets)
    except ValueError as err:
        print(f"[Error] Could not generate work queue: {err}")
        return

    if not queue:
        print("Work queue is empty. No unresolved tickets.")
        return

    print(f"Total active tickets in queue: {len(queue)}")
    print("-" * 50)
    for idx, ticket in enumerate(queue, start=1):
        tid = ticket.get("id")
        pri = ticket.get("priority", "").upper()
        status = ticket.get("status")
        assigned = ticket.get("assigned_to") or "Unassigned"
        title = ticket.get("title")
        print(f"{idx}. [{tid}] Priority: {pri:<8} Status: {status:<12} Assigned: {assigned:<15} | {title}")


def handle_reports(tickets: list[dict], events: list[dict] | None = None,) -> None:
    """Display aggregate ticket metrics and breakdown."""
    print("\n--- Ticket Statistics Report ---")
    report = generate_report(tickets, events=events)
    print(f"Total Tickets: {report['total']}")
    print("\nBreakdown by Status:")
    for status, count in report["by_status"].items():
        print(f"  - {status:<12}: {count}")
    print("\nBreakdown by Priority:")
    for pri, count in report["by_priority"].items():
        print(f"  - {pri:<12}: {count}")
    print("\nSLA Metrics:")
    print(f"  - Overdue Tickets:   {report['overdue_count']}")
    print(f"  - Escalated Tickets: {report['escalated_count']}")
def handle_sla_attention_queue(tickets: list[dict]) -> None:
    """Display unresolved tickets ordered by SLA urgency."""

    print("\n--- SLA Attention Queue ---")

    now = datetime.now(timezone.utc)

    try:
        queue = sla_attention_queue(tickets, now)
    except (ValueError, TypeError, KeyError) as err:
        print(f"[Error] Could not generate SLA queue: {err}")
        return

    if not queue:
        print("No unresolved tickets.")
        return

    print(f"Total unresolved tickets: {len(queue)}")
    print("-" * 65)

    for ticket in queue:
        due_at = datetime.fromisoformat(ticket["due_at"])

        overdue = now > due_at

        marker = "OVERDUE" if overdue else "ON TIME"

        print(
            f"[{ticket['id']}] "
            f"Priority: {ticket['priority'].upper():<8} "
            f"Status: {ticket['status']:<12} "
            f"SLA: {marker:<8} "
            f"Due: {ticket['due_at']}"
        )

def run_audited_operation(
    tickets,
    events,
    data_path,
    operation,
    *args,
    save_state=None,
):
    """
    Run an audited operation using temporary copies.

    Publish the changes only after persistence succeeds.
    """

    if save_state is None:
        raise RuntimeError(
            "Combined ticket and event storage is not available yet."
        )

    temp_tickets = deepcopy(tickets)
    temp_events = deepcopy(events)

    result = operation(
        temp_tickets,
        temp_events,
        *args,
    )

    save_state(temp_tickets, temp_events, data_path)

    tickets[:] = temp_tickets
    events[:] = temp_events

    return result
def main_menu(data_path: str = DEFAULT_DATA_PATH) -> None:
    """Run the main CampusFlow CLI interactive menu."""
    try:
        data = load_v2(data_path)
        tickets = data["tickets"]
        events = data["events"]
    except (ValueError, OSError, TypeError) as err:
        print(f"[FATAL] Data loading error: {err}")
        print("Application exiting to prevent overwriting corrupted data.")
        return

    print("========================================")
    print(" Welcome to CampusFlow Helpdesk System  ")
    print("========================================")
    while True:
        print("\nMain Menu:")
        print("1. Create New Ticket")
        print("2. List All Tickets")
        print("3. View Ticket Details")
        print("4. Assign Ticket")
        print("5. Update Ticket Status")
        print("6. Reopen Resolved Ticket")
        print("7. View Work Queue")
        print("8. View Reports")
        print("9. View SLA Attention Queue")
        print("10. Check & Escalate Overdue Tickets")
        print("11. View Ticket History")
        print("12. Engineering Knowledge Lab")
        print("13. Exit")
        try:
            choice = input("\nSelect an option (1-13): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting CampusFlow. Goodbye!")
            break
        if choice == "1":
            handle_create_ticket(tickets, data_path, events=events)
        elif choice == "2":
            handle_list_tickets(tickets)
        elif choice == "3":
            handle_view_ticket(tickets)
        elif choice == "4":
            handle_assign_ticket(tickets, events, data_path, save_state=save_v2)
        elif choice == "5":
            handle_update_status(tickets, events, data_path, save_state=save_v2)
        elif choice == "6":
            handle_reopen_ticket(tickets, events, data_path, save_state=save_v2)
        elif choice == "7":
            handle_work_queue(tickets)
        elif choice == "8":
            handle_reports(tickets, events)
        elif choice == "9":
            handle_sla_attention_queue(tickets)
        elif choice == "10":
            handle_check_escalations(tickets, data_path, events=events)
        elif choice == "11":
            handle_ticket_history(events)
        elif choice == "12":
            run_knowledge_lab()
        elif choice == "13":
            print("Exiting CampusFlow. Goodbye!")
            break
        else:
            print("[Error] Invalid option. Please enter a number between 1 and 13.")


if __name__ == "__main__":
    main_menu()