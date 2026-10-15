import datetime, timezone, unittest
from campusflow.sla import escalate_overdue

class TestSLAEscalateDue(unittest.TestCase):
    def test_escalate_due(self):
        ticket = {
        "id": "T001",
        "due_at": datetime(2026, 10, 15, 10, 0, tzinfo=timezone.utc),
        "status": "open",
        "priority": "high",
        "assigned_to": "Ada",
        }

        now = datetime(2026, 11)