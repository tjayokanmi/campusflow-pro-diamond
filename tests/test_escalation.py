
import unittest
from datetime import datetime, timezone

from campusflow.sla import escalate_overdue


class TestSLAEscalateDue(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 15, 11, 0, tzinfo=timezone.utc)
        self.ticket = {
            "id": "T001",
            "due_at": datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc),
            "status": "open",
            "priority": "high",
            "assigned_to": "Ada",
        }
        self.events = []
        self.actor = "test_user"

    def test_escalate_due(self):
        result = escalate_overdue(
            [self.ticket], self.events, self.now, self.actor
        )

        self.assertEqual(result["escalated"], ["T001"])
        self.assertEqual(result["already_escalated"], [])
        self.assertEqual(len(self.events), 1)

        event = self.events[0]
        self.assertEqual(event["ticket_id"], "T001")
        self.assertEqual(event["event_type"], "escalated")
        self.assertEqual(event["actor"], self.actor)
        self.assertEqual(event["timestamp"], self.now.isoformat())

        # Escalation must not change ticket fields.
        self.assertEqual(self.ticket["priority"], "high")
        self.assertEqual(self.ticket["status"], "open")
        self.assertEqual(self.ticket["assigned_to"], "Ada")

    def test_does_not_duplicate_escalation(self):
        escalate_overdue([self.ticket], self.events, self.now, self.actor)

        result = escalate_overdue(
            [self.ticket], self.events, self.now, self.actor
        )

        self.assertEqual(result["escalated"], [])
        self.assertEqual(result["already_escalated"], ["T001"])
        self.assertEqual(len(self.events), 1)

    def test_deadline_exactly_now_is_not_overdue(self):
        self.ticket["due_at"] = self.now

        result = escalate_overdue(
            [self.ticket], self.events, self.now, self.actor
        )

        self.assertEqual(result["escalated"], [])
        self.assertEqual(self.events, [])

    def test_resolved_ticket_is_not_escalated(self):
        self.ticket["status"] = "resolved"

        result = escalate_overdue(
            [self.ticket], self.events, self.now, self.actor
        )

        self.assertEqual(result["escalated"], [])
        self.assertEqual(self.events, [])


if __name__ == "__main__":
    unittest.main()
