import unittest
from copy import deepcopy

from main import run_audited_operation
from campusflow.operations import (
    assign_ticket_with_audit,
    update_status_with_audit,
)


class TestCLIIntegration(unittest.TestCase):

    def setUp(self):
        self.tickets = [
            {
                "id": "T001",
                "title": "Laptop not working",
                "category": "Hardware",
                "urgency": "high",
                "affected_users": 1,
                "priority": "high",
                "status": "open",
                "assigned_to": None,
            }
        ]

        self.events = []
        self.data_path = "test_data.json"

    def fake_save(self, tickets, events, path):
        """Simulate successful persistence."""
        self.saved_tickets = deepcopy(tickets)
        self.saved_events = deepcopy(events)

    def failing_save(self, tickets, events, path):
        """Simulate a storage failure."""
        raise OSError("Simulated disk failure")

    def test_successful_assignment_creates_event(self):
        updated = run_audited_operation(
            self.tickets,
            self.events,
            self.data_path,
            assign_ticket_with_audit,
            "T001",
            "David",
            "Engineer B",
            save_state=self.fake_save,
        )

        self.assertEqual(updated["assigned_to"], "David")
        self.assertEqual(self.tickets[0]["assigned_to"], "David")
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0]["event_type"], "ASSIGN")
        self.assertEqual(self.events[0]["actor"], "Engineer B")

        self.assertEqual(self.saved_tickets, self.tickets)
        self.assertEqual(self.saved_events, self.events)

    def test_failed_assignment_does_not_change_state(self):
        original_tickets = deepcopy(self.tickets)
        original_events = deepcopy(self.events)

        with self.assertRaises(ValueError):
            run_audited_operation(
                self.tickets,
                self.events,
                self.data_path,
                assign_ticket_with_audit,
                "T999",
                "David",
                "Engineer B",
                save_state=self.fake_save,
            )

        self.assertEqual(self.tickets, original_tickets)
        self.assertEqual(self.events, original_events)
        self.assertFalse(hasattr(self, "saved_tickets"))

    def test_storage_failure_does_not_change_state(self):
        original_tickets = deepcopy(self.tickets)
        original_events = deepcopy(self.events)

        with self.assertRaises(OSError):
            run_audited_operation(
                self.tickets,
                self.events,
                self.data_path,
                assign_ticket_with_audit,
                "T001",
                "David",
                "Engineer B",
                save_state=self.failing_save,
            )

        self.assertEqual(self.tickets, original_tickets)
        self.assertEqual(self.events, original_events)

    def test_successful_status_update_creates_start_event(self):
        self.tickets[0]["assigned_to"] = "David"

        updated = run_audited_operation(
            self.tickets,
            self.events,
            self.data_path,
            update_status_with_audit,
            "T001",
            "in_progress",
            "Engineer B",
            save_state=self.fake_save,
        )

        self.assertEqual(updated["status"], "in_progress")
        self.assertEqual(self.tickets[0]["status"], "in_progress")
        self.assertEqual(len(self.events), 1)
        self.assertEqual(self.events[0]["event_type"], "START")
        self.assertEqual(self.events[0]["before_status"], "open")
        self.assertEqual(self.events[0]["after_status"], "in_progress")

    def test_missing_storage_interface_blocks_operation(self):
        original_tickets = deepcopy(self.tickets)

        with self.assertRaises(RuntimeError):
            run_audited_operation(
                self.tickets,
                self.events,
                self.data_path,
                assign_ticket_with_audit,
                "T001",
                "David",
                "Engineer B",
            )

        self.assertEqual(self.tickets, original_tickets)
        self.assertEqual(self.events, [])


if __name__ == "__main__":
    unittest.main()