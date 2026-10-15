import unittest
from copy import deepcopy

from campusflow.operations import (
    assign_ticket_with_audit,
    update_status_with_audit,
)


class TestAuditedOperations(unittest.TestCase):

    def test_failed_assignment_does_not_mutate_state(self):
        tickets = [
            {
                "id": "T001",
                "title": "Network failure",
                "category": "Network",
                "urgency": "high",
                "affected_users": 5,
                "priority": "high",
                "status": "resolved",
                "assigned_to": "David",
            }
        ]

        events = []

        original_tickets = deepcopy(tickets)
        original_events = deepcopy(events)

        with self.assertRaises(ValueError):
            assign_ticket_with_audit(
                tickets,
                events,
                "T001",
                "Stephen",
                "Engineer B",
            )

        self.assertEqual(tickets, original_tickets)
        self.assertEqual(events, original_events)

    def test_successful_assignment_records_event(self):
        tickets = [
            {
                "id": "T001",
                "title": "Network failure",
                "category": "Network",
                "urgency": "high",
                "affected_users": 5,
                "priority": "high",
                "status": "open",
                "assigned_to": None,
            }
        ]

        events = []

        assign_ticket_with_audit(
            tickets,
            events,
            "T001",
            "Stephen",
            "Engineer B",
        )

        self.assertEqual(
            tickets[0]["assigned_to"],
            "Stephen",
        )

        self.assertEqual(len(events), 1)

        self.assertEqual(
            events[0]["event_type"],
            "ASSIGN",
        )

        self.assertEqual(
            events[0]["actor"],
            "Engineer B",
        )

        self.assertEqual(
            events[0]["before_status"],
            "open",
        )

        self.assertEqual(
            events[0]["after_status"],
            "open",
        )

    def test_failed_status_transition_creates_no_event(self):
        tickets = [
            {
                "id": "T001",
                "title": "Network failure",
                "category": "Network",
                "urgency": "high",
                "affected_users": 5,
                "priority": "high",
                "status": "open",
                "assigned_to": None,
            }
        ]

        events = []

        original_tickets = deepcopy(tickets)
        original_events = deepcopy(events)

        with self.assertRaises(ValueError):
            update_status_with_audit(
                tickets,
                events,
                "T001",
                "resolved",
                "Engineer B",
            )

        self.assertEqual(
            tickets,
            original_tickets,
        )

        self.assertEqual(
            events,
            original_events,
        )


if __name__ == "__main__":
    unittest.main()