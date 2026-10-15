"""CampusFlow: Command-line Technical Support Ticket Management System."""

from campusflow.operations import (
    create_ticket_with_audit,
    assign_ticket_with_audit,
    update_status_with_audit,
    reopen_ticket_with_audit,
)
from campusflow.duplicates import detect_duplicates
from campusflow.knowledge_lab import run_knowledge_lab
from datetime import datetime, timezone
from campusflow.queues import sla_attention_queue
import sys
from campusflow.storage import load_tickets, save_tickets, DEFAULT_DATA_PATH
from campusflow.tickets import create_ticket
from campusflow.workflow import (
    assign_ticket,
    update_status,
    reopen_ticket,
    get_work_queue,
)
from campusflow.reports import generate_report
from campusflow.history import get_ticket_history

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


def handle_create_ticket(tickets: list[dict], data_path: str) -> None:
    """Collect inputs and create a new support ticket."""
    print("\n--- Create New Ticket ---")
    title = input("Enter ticket title/description: ")
    print("Allowed categories: Network, Hardware, Software, Other")
    category = input("Enter category: ")
    print("Allowed urgency levels: low, medium, high")
    urgency = input("Enter urgency: ")
    users_raw = input("Enter number of affected users: ")

    try:
        affected_users = int(users_raw)
    except ValueError:
        print("[Error] Affected users must be a valid integer.")
        return

    try:
    # Validate the ticket before checking for duplicates.
    new_ticket = create_ticket(
        title=title,
        category=category,
        urgency=urgency,
        affected_users=affected_users,
        records=tickets,
    )

    duplicates = detect_duplicates(
        tickets,
        new_ticket["category"],
        new_ticket["title"],
    )

    if duplicates:
        print(
            f"\n[Warning] Potential duplicate tickets: "
            f"{', '.join(duplicates)}"
        )

        confirmation = input(
            "Do you still want to create this ticket? (yes/no): "
        ).strip().lower()

        if confirmation != "yes":
            print("[Cancelled] Ticket creation cancelled.")
            return

    tickets.append(new_ticket)
    save_tickets(tickets, data_path)

except ValueError as err:
    print(f"[Error] Failed to create ticket: {err}")
    return

    tickets.append(new_ticket)
    save_tickets(tickets, data_path)
    print(f"[Success] Ticket {new_ticket.get('id')} created successfully with priority '{new_ticket.get('priority')}'.")


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


def handle_assign_ticket(tickets: list[dict], data_path: str) -> None:
    """Assign an existing ticket to a staff member."""
    print("\n--- Assign Ticket ---")
    tid = input("Enter ticket ID to assign: ").strip()
    staff = input("Enter staff member name: ")
    try:
        updated = assign_ticket(tickets, tid, staff)
        save_tickets(tickets, data_path)
        print(f"[Success] Ticket {tid} assigned to '{updated.get('assigned_to')}'.")
    except ValueError as err:
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
def handle_update_status(tickets: list[dict], data_path: str) -> None:
    """Update lifecycle status of an active ticket."""
    print("\n--- Update Ticket Status ---")
    tid = input("Enter ticket ID: ").strip()
    print("Allowed statuses: open, in_progress, resolved")
    new_status = input("Enter new status: ").strip()
    try:
        updated = update_status(tickets, tid, new_status)
        save_tickets(tickets, data_path)
        print(f"[Success] Ticket {tid} status updated to '{updated.get('status')}'.")
    except ValueError as err:
        print(f"[Error] Status update failed: {err}")


def handle_reopen_ticket(tickets: list[dict], data_path: str) -> None:
    """Explicitly reopen a resolved ticket back to open."""
    print("\n--- Reopen Resolved Ticket ---")
    tid = input("Enter resolved ticket ID to reopen: ").strip()
    try:
        updated = reopen_ticket(tickets, tid)
        save_tickets(tickets, data_path)
        print(f"[Success] Ticket {tid} reopened to status '{updated.get('status')}'.")
    except ValueError as err:
        print(f"[Error] Reopening failed: {err}")


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

def main_menu(data_path: str = DEFAULT_DATA_PATH) -> None:
    """Run the main CampusFlow CLI interactive menu."""
    try:
        tickets = load_tickets(data_path)
    except ValueError as err:
        print(f"[FATAL] Data loading error: {err}")
        print("Application exiting to prevent overwriting corrupted data.")
        sys.exit(1)
    events = []
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
        print("10. View Ticket History")
        print("11. Engineering Knowledge Lab")
        print("12. Exit")

        try:
            choice = input("\nSelect an option (1-12): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting CampusFlow. Goodbye!")
            break

        if choice == "1":
            handle_create_ticket(tickets, data_path)
        elif choice == "2":
            handle_list_tickets(tickets)
        elif choice == "3":
            handle_view_ticket(tickets)
        elif choice == "4":
            handle_assign_ticket(tickets, data_path)
        elif choice == "5":
            handle_update_status(tickets, data_path)
        elif choice == "6":
            handle_reopen_ticket(tickets, data_path)
        elif choice == "7":
            handle_work_queue(tickets)
        elif choice == "8":
            handle_reports(tickets, events)
        elif choice == "9":
            handle_sla_attention_queue(tickets)

        elif choice == "10":
            handle_ticket_history(events)
        elif choice == "11":
            run_knowledge_lab()

        elif choice == "12":
            print("Exiting CampusFlow. Goodbye!")
            break

if __name__ == "__main__":
    main_menu()
