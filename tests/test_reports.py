"""Automated unit tests for CampusFlow reports generation."""

import unittest
from campusflow.reports import generate_report


class TestReports(unittest.TestCase):

    def test_report_empty_tickets(self):
        """Empty ticket collection produces total 0 and zero counts for all categories."""
        report = generate_report([])
        self.assertEqual(report["total"], 0)
        self.assertEqual(
            report["by_status"],
            {"open": 0, "in_progress": 0, "resolved": 0}
        )
        self.assertEqual(
            report["by_priority"],
            {"critical": 0, "high": 0, "medium": 0, "low": 0}
        )

    def test_report_mixed_tickets(self):
        """Mixed tickets are counted accurately across statuses and priorities."""
        tickets = [
            {"id": "T001", "status": "open", "priority": "critical"},
            {"id": "T002", "status": "open", "priority": "high"},
            {"id": "T003", "status": "in_progress", "priority": "critical"},
            {"id": "T004", "status": "resolved", "priority": "low"},
            {"id": "T005", "status": "resolved", "priority": "low"},
        ]
        report = generate_report(tickets)

        self.assertEqual(report["total"], 5)
        self.assertEqual(
            report["by_status"],
            {"open": 2, "in_progress": 1, "resolved": 2}
        )
        self.assertEqual(
            report["by_priority"],
            {"critical": 2, "high": 1, "medium": 0, "low": 2}
        )

    def test_report_all_same_category_still_includes_zero_counts(self):
        """Report preserves zero-count entries even when all tickets share one status/priority."""
        tickets = [
            {"id": "T001", "status": "open", "priority": "low"},
            {"id": "T002", "status": "open", "priority": "low"},
        ]
        report = generate_report(tickets)
        self.assertEqual(report["total"], 2)
        self.assertEqual(report["by_status"]["open"], 2)
        self.assertEqual(report["by_status"]["in_progress"], 0)
        self.assertEqual(report["by_status"]["resolved"], 0)
        self.assertEqual(report["by_priority"]["low"], 2)
        self.assertEqual(report["by_priority"]["critical"], 0)
        self.assertEqual(report["by_priority"]["high"], 0)
        self.assertEqual(report["by_priority"]["medium"], 0)

    def test_report_does_not_mutate_tickets(self):
        """Report generation does not mutate the input tickets list or items."""
        tickets = [{"id": "T001", "status": "open", "priority": "high"}]
        original = list(tickets)
        generate_report(tickets)
        self.assertEqual(tickets, original)

    def test_report_rejects_non_list_input(self):
        """Passing non-list input raises TypeError."""
        with self.assertRaises(TypeError):
            generate_report(None)
        with self.assertRaises(TypeError):
            generate_report("invalid")


if __name__ == "__main__":
    unittest.main()


def test_report_counts_overdue_unresolved_tickets(self):
    from datetime import datetime, timezone

    now = datetime(2026, 10, 14, 15, 0, tzinfo=timezone.utc)

    tickets = [
        {
            "id": "T001",
            "status": "open",
            "priority": "high",
            "due_at": "2026-10-14T14:00:00+00:00",
        },
        {
            "id": "T002",
            "status": "in_progress",
            "priority": "medium",
            "due_at": "2026-10-14T16:00:00+00:00",
        },
        {
            "id": "T003",
            "status": "resolved",
            "priority": "critical",
            "due_at": "2026-10-14T12:00:00+00:00",
        },
    ]

    report = generate_report(tickets, now=now)

    self.assertEqual(report["overdue_count"], 1)


def test_report_does_not_count_deadline_as_overdue(self):
    from datetime import datetime, timezone

    now = datetime(2026, 10, 14, 15, 0, tzinfo=timezone.utc)

    tickets = [
        {
            "id": "T001",
            "status": "open",
            "priority": "critical",
            "due_at": "2026-10-14T15:00:00+00:00",
        }
    ]

    report = generate_report(tickets, now=now)

    self.assertEqual(report["overdue_count"], 0)


def test_report_counts_escalation_only_in_current_cycle(self):
    tickets = [
        {
            "id": "T001",
            "status": "open",
            "priority": "high",
            "escalation_cycle": 2,
        }
    ]

    events = [
        {
            "ticket_id": "T001",
            "event_type": "ESCALATE",
            "details": {"escalation_cycle": 1},
        },
        {
            "ticket_id": "T001",
            "event_type": "ESCALATE",
            "details": {"escalation_cycle": 2},
        },
    ]

    report = generate_report(tickets, events=events)

    self.assertEqual(report["escalated_count"], 1)