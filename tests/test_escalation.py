
import unittest
from datetime import datetime, timezone, timedelta

from campusflow.sla import calculate_due_at, escalate_overdue, is_overdue
from campusflow.workflow import reopen_ticket, update_status
from campusflow.history import record_event


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

    def test_critical_deadline_boundary_60_and_61_minutes(self):
        """A critical ticket is not overdue at exactly 60 minutes, but is overdue after 61 minutes."""
        cycle_start = datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc)
        due_at = calculate_due_at("critical", cycle_start)
        self.assertEqual(due_at, cycle_start + timedelta(minutes=60))

        critical_ticket = {
            "id": "T002",
            "due_at": due_at,
            "status": "open",
            "priority": "critical",
            "assigned_to": "Engineer",
        }

        # Exactly at 60 minutes: not overdue, not escalated
        at_60m = cycle_start + timedelta(minutes=60)
        self.assertFalse(is_overdue(critical_ticket, at_60m))
        res_60m = escalate_overdue([critical_ticket], self.events, at_60m, self.actor)
        self.assertEqual(res_60m["escalated"], [])
        self.assertEqual(len(self.events), 0)

        # After 61 minutes: overdue, escalated
        at_61m = cycle_start + timedelta(minutes=61)
        self.assertTrue(is_overdue(critical_ticket, at_61m))
        res_61m = escalate_overdue([critical_ticket], self.events, at_61m, self.actor)
        self.assertEqual(res_61m["escalated"], ["T002"])
        self.assertEqual(len(self.events), 1)

    def test_all_sla_durations(self):
        """Test calculation and overdue threshold for each of the 4 SLA durations."""
        start = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)

        cases = [
            ("critical", timedelta(minutes=60)),
            ("high", timedelta(minutes=240)),
            ("medium", timedelta(minutes=1440)),
            ("low", timedelta(minutes=2880)),
        ]

        for priority, duration in cases:
            due = calculate_due_at(priority, start)
            self.assertEqual(due, start + duration)

            ticket = {
                "id": f"T_{priority}",
                "due_at": due,
                "status": "open",
                "priority": priority,
                "assigned_to": "Tech",
            }

            # 1 second before deadline -> not overdue
            self.assertFalse(is_overdue(ticket, due - timedelta(seconds=1)))
            # Exactly at deadline -> not overdue
            self.assertFalse(is_overdue(ticket, due))
            # 1 second after deadline -> overdue
            self.assertTrue(is_overdue(ticket, due + timedelta(seconds=1)))

    def test_invalid_and_non_utc_inputs_raise_errors(self):
        """escalate_overdue rejects non-UTC, naive, or invalid input types."""
        # Naive now
        naive_now = datetime(2026, 10, 15, 11, 0)
        with self.assertRaises(ValueError):
            escalate_overdue([self.ticket], self.events, naive_now, self.actor)

        # Non-UTC timezone (e.g., UTC+2)
        non_utc = datetime(2026, 10, 15, 11, 0, tzinfo=timezone(timedelta(hours=2)))
        with self.assertRaises(ValueError):
            escalate_overdue([self.ticket], self.events, non_utc, self.actor)

        # Non-datetime now
        with self.assertRaises(TypeError):
            escalate_overdue([self.ticket], self.events, "2026-10-15T11:00:00Z", self.actor)

        # Non-list tickets
        with self.assertRaises(TypeError):
            escalate_overdue("not_a_list", self.events, self.now, self.actor)

        # Non-list events
        with self.assertRaises(TypeError):
            escalate_overdue([self.ticket], "not_a_list", self.now, self.actor)

        # Empty or whitespace actor
        with self.assertRaises(ValueError):
            escalate_overdue([self.ticket], self.events, self.now, "")
        with self.assertRaises(ValueError):
            escalate_overdue([self.ticket], self.events, self.now, "   ")

    def test_reopen_starts_new_sla_cycle_and_allows_re_escalation(self):
        """Reopening a resolved ticket resets the SLA cycle and permits a second escalation."""
        ticket = {
            "id": "T001",
            "title": "Outage",
            "category": "Network",
            "urgency": "high",
            "affected_users": 10,
            "priority": "high",
            "status": "open",
            "assigned_to": "Bob",
            "created_at": "2026-10-15T08:00:00+00:00",
            "due_at": datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc),
            "escalation_cycle": 0,
        }
        tickets = [ticket]
        events = []

        # Cycle 1: Escalate at 10:30 UTC
        now_cycle1 = datetime(2026, 10, 15, 10, 30, tzinfo=timezone.utc)
        res1 = escalate_overdue(tickets, events, now_cycle1, "Auditor")
        self.assertEqual(res1["escalated"], ["T001"])
        self.assertEqual(len(events), 1)

        # Repeated check in Cycle 1 produces no new event
        res1_dup = escalate_overdue(tickets, events, now_cycle1, "Auditor")
        self.assertEqual(res1_dup["escalated"], [])
        self.assertEqual(res1_dup["already_escalated"], ["T001"])
        self.assertEqual(len(events), 1)

        # Progress ticket to resolved
        update_status(tickets, "T001", "in_progress")
        update_status(tickets, "T001", "resolved")
        self.assertEqual(ticket["status"], "resolved")

        # Reopen at 11:00 UTC -> Starts Cycle 2
        reopen_time = datetime(2026, 10, 15, 11, 0, tzinfo=timezone.utc)
        reopened = reopen_ticket(tickets, "T001", now=reopen_time)
        self.assertEqual(reopened["status"], "open")
        self.assertEqual(reopened["created_at"], "2026-10-15T08:00:00+00:00")  # created_at preserved
        # New due_at should be reopen_time + 4 hours (for high priority) = 15:00 UTC
        self.assertEqual(reopened["due_at"], datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc))

        # Record reopen event in events
        record_event(
            events,
            "T001",
            "REOPEN",
            "Supervisor",
            "resolved",
            "open",
            "Ticket reopened",
            now=reopen_time,
        )

        # Cycle 2 at 12:00 UTC: not overdue yet (due at 15:00)
        at_12 = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)
        res_before_due = escalate_overdue(tickets, events, at_12, "Auditor")
        self.assertEqual(res_before_due["escalated"], [])
        self.assertEqual(res_before_due["already_escalated"], [])

        # Cycle 2 at 15:30 UTC: overdue in new cycle! Legitimate re-escalation
        at_1530 = datetime(2026, 10, 15, 15, 30, tzinfo=timezone.utc)
        res2 = escalate_overdue(tickets, events, at_1530, "Auditor")
        self.assertEqual(res2["escalated"], ["T001"])
        self.assertEqual(res2["already_escalated"], [])

        # Total escalation events is now 2 (plus 1 reopen event = 3 events)
        escalation_events = [e for e in events if e["event_type"] == "escalated"]
        self.assertEqual(len(escalation_events), 2)
        self.assertEqual(escalation_events[0]["timestamp"], now_cycle1.isoformat())
        self.assertEqual(escalation_events[1]["timestamp"], at_1530.isoformat())

        # Repeated check in Cycle 2 is idempotent
        res2_dup = escalate_overdue(tickets, events, at_1530, "Auditor")
        self.assertEqual(res2_dup["escalated"], [])
        self.assertEqual(res2_dup["already_escalated"], ["T001"])
        self.assertEqual(len([e for e in events if e["event_type"] == "escalated"]), 2)

    def test_escalation_does_not_mutate_ticket_fields(self):
        """Escalation must never mutate priority, status, assigned_to, or other ticket fields."""
        original_snapshot = dict(self.ticket)
        escalate_overdue([self.ticket], self.events, self.now, self.actor)
        self.assertEqual(self.ticket, original_snapshot)

    def test_invalid_operations_produce_no_unintended_events(self):
        """Non-overdue tickets, resolved tickets, or failed validations append zero events."""
        # 1. Non-overdue ticket
        future_ticket = {
            "id": "T099",
            "due_at": self.now + timedelta(hours=2),
            "status": "open",
            "priority": "low",
        }
        escalate_overdue([future_ticket], self.events, self.now, self.actor)
        self.assertEqual(len(self.events), 0)

        # 2. Resolved ticket past deadline
        resolved_ticket = {
            "id": "T098",
            "due_at": self.now - timedelta(hours=2),
            "status": "resolved",
            "priority": "critical",
        }
        escalate_overdue([resolved_ticket], self.events, self.now, self.actor)
        self.assertEqual(len(self.events), 0)

        # 3. Failed validation
        with self.assertRaises(ValueError):
            escalate_overdue([self.ticket], self.events, self.now, "")
        self.assertEqual(len(self.events), 0)


if __name__ == "__main__":
    unittest.main()