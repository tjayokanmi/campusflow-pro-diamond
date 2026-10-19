import unittest
from datetime import datetime, timezone

from campusflow.queues import sla_attention_queue


class TestSLAAttentionQueue(unittest.TestCase):

    def setUp(self):
        self.now = datetime(
            2026, 10, 15, 12, 0, tzinfo=timezone.utc
        )

        self.tickets = [
            {
                "id": "T003",
                "status": "open",
                "due_at": "2026-10-15T14:00:00+00:00",
            },
            {
                "id": "T002",
                "status": "in_progress",
                "due_at": "2026-10-15T10:00:00+00:00",
            },
            {
                "id": "T001",
                "status": "open",
                "due_at": "2026-10-15T10:00:00+00:00",
            },
            {
                "id": "T004",
                "status": "resolved",
                "due_at": "2026-10-15T09:00:00+00:00",
            },
        ]

    def test_overdue_tickets_appear_first(self):
        result = sla_attention_queue(
            self.tickets,
            self.now,
        )

        ids = [ticket["id"] for ticket in result]

        self.assertEqual(
            ids,
            ["T001", "T002", "T003"],
        )

    def test_resolved_tickets_are_excluded(self):
        result = sla_attention_queue(
            self.tickets,
            self.now,
        )

        ids = [ticket["id"] for ticket in result]

        self.assertNotIn("T004", ids)

    def test_equal_deadlines_sorted_by_ticket_id(self):
        result = sla_attention_queue(
            self.tickets,
            self.now,
        )

        ids = [ticket["id"] for ticket in result]

        self.assertLess(
            ids.index("T001"),
            ids.index("T002"),
        )

    def test_queue_does_not_modify_tickets(self):
        from copy import deepcopy

        original = deepcopy(self.tickets)

        sla_attention_queue(
            self.tickets,
            self.now,
        )

        self.assertEqual(
            self.tickets,
            original,
        )


if __name__ == "__main__":
    unittest.main()