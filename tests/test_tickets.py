"""Automated unit tests for ticket creation and validation."""

import unittest
from datetime import datetime, timezone, timedelta
from campusflow.tickets import create_ticket, generate_ticket_id


class TestTicketCreation(unittest.TestCase):

    def test_create_valid_ticket(self):
        """Ticket creation succeeds with valid inputs and calculates priority."""
        ticket = create_ticket(
            title="Projector in Room 101 not working",
            category="Hardware",
            urgency="high",
            affected_users=12,
        )
        self.assertEqual(ticket["title"], "Projector in Room 101 not working")
        self.assertEqual(ticket["category"], "Hardware")
        self.assertEqual(ticket["urgency"], "high")
        self.assertEqual(ticket["affected_users"], 12)
        self.assertEqual(ticket["priority"], "critical")
        self.assertEqual(ticket["status"], "open")
        self.assertIsNone(ticket["assigned_to"])

    def test_create_ticket_rejects_empty_title(self):
        """Empty or whitespace-only title raises ValueError."""
        with self.assertRaises(ValueError):
            create_ticket("   ", "Network", "high", 5)

    def test_create_ticket_rejects_invalid_category(self):
        """Invalid category raises ValueError."""
        with self.assertRaises(ValueError):
            create_ticket("Broken AC", "Facilities", "high", 5)

    def test_create_ticket_rejects_invalid_urgency(self):
        """Invalid urgency level raises ValueError."""
        with self.assertRaises(ValueError):
            create_ticket("Broken mouse", "Hardware", "extreme", 1)

    def test_create_ticket_rejects_invalid_affected_users(self):
        """Affected users must be an integer >= 1."""
        with self.assertRaises(ValueError):
            create_ticket("Broken keyboard", "Hardware", "low", 0)
        with self.assertRaises(ValueError):
            create_ticket("Broken keyboard", "Hardware", "low", -2)
        with self.assertRaises(ValueError):
            create_ticket("Broken keyboard", "Hardware", "low", True)

    def test_generate_ticket_id_sequential(self):
        """Sequential IDs are incremented properly."""
        records = [
            {"id": "T001"},
            {"id": "T002"},
            {"id": "T015"},
        ]
        self.assertEqual(generate_ticket_id(records), "T016")

    def test_generate_ticket_id_empty_records(self):
        """Empty records list starts with T001."""
        self.assertEqual(generate_ticket_id([]), "T001")


    def test_create_ticket_has_all_phase2_fields(self):
        """Ticket creation populates all 12 Phase 2 fields."""
        fixed_now = datetime(2026, 3, 30, 10, 0, tzinfo=timezone.utc)
        ticket = create_ticket(
            title="Wi-Fi connectivity issue in library",
            category="Network",
            urgency="high",
            affected_users=15,
            now=fixed_now,
        )
        required_fields = [
            "id", "title", "category", "urgency", "affected_users",
            "priority", "status", "assigned_to", "created_at",
            "updated_at", "due_at", "escalation_cycle"
        ]
        for field in required_fields:
            self.assertIn(field, ticket)

        self.assertEqual(ticket["escalation_cycle"], 0)
        self.assertEqual(ticket["created_at"], "2026-03-30T10:00:00+00:00")
        self.assertEqual(ticket["updated_at"], "2026-03-30T10:00:00+00:00")
        # Critical priority -> 1 hour SLA
        self.assertEqual(ticket["due_at"], "2026-03-30T11:00:00+00:00")

    def test_create_ticket_due_at_calculation_by_priority(self):
        """Due dates match SLA durations: critical (+1h), high (+4h), medium (+24h), low (+48h)."""
        base_time = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

        # Critical: high urgency + 10 users -> 1h
        crit = create_ticket("Critical", "Network", "high", 10, now=base_time)
        self.assertEqual(crit["priority"], "critical")
        self.assertEqual(crit["due_at"], (base_time + timedelta(hours=1)).isoformat())

        # High: high urgency + 1 user -> 4h
        high = create_ticket("High", "Hardware", "high", 1, now=base_time)
        self.assertEqual(high["priority"], "high")
        self.assertEqual(high["due_at"], (base_time + timedelta(hours=4)).isoformat())

        # Medium: medium urgency + 1 user -> 24h
        med = create_ticket("Medium", "Software", "medium", 1, now=base_time)
        self.assertEqual(med["priority"], "medium")
        self.assertEqual(med["due_at"], (base_time + timedelta(hours=24)).isoformat())

        # Low: low urgency + 1 user -> 48h
        low = create_ticket("Low", "Other", "low", 1, now=base_time)
        self.assertEqual(low["priority"], "low")
        self.assertEqual(low["due_at"], (base_time + timedelta(hours=48)).isoformat())

    def test_create_ticket_with_iso_string_now(self):
        """create_ticket accepts ISO string timestamp for now."""
        iso_str = "2026-05-10T08:30:00+00:00"
        ticket = create_ticket("Email sync", "Software", "medium", 2, now=iso_str)
        self.assertEqual(ticket["created_at"], iso_str)
        self.assertEqual(ticket["updated_at"], iso_str)

    def test_create_ticket_rejects_naive_or_non_utc_now(self):
        """create_ticket rejects naive datetime and non-UTC datetime for now."""
        naive = datetime(2026, 1, 1, 12, 0)
        with self.assertRaises(ValueError):
            create_ticket("Title", "Network", "low", 1, now=naive)

        non_utc = datetime(2026, 1, 1, 12, 0, tzinfo=timezone(timedelta(hours=1)))
        with self.assertRaises(ValueError):
            create_ticket("Title", "Network", "low", 1, now=non_utc)


if __name__ == "__main__":
    unittest.main()
