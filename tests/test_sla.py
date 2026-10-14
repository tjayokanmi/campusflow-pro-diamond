import datetime
import unittest 
from campusflow.sla import calculate_due_at

class TestSLADeadline(unittest.TestCase):
    def test_sla_durations(self):
        start_utc = datetime.datetime(2026, 6, 1, 10, 0, 0, tzinfo=datetime.timezone.utc)
        critical_utc = datetime.datetime(2026, 6, 1, 11, 0, 0, tzinfo=datetime.timezone.utc)
        high_utc = datetime.datetime(2026, 6, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)
        medium_utc = datetime.datetime(2026, 6, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)
        low_utc = datetime.datetime(2026, 6, 3, 10, 0, 0, tzinfo=datetime.timezone.utc)
        # critical_utc = start_utc + datetime.timedelta(hours=1)
        # high_utc = start_utc + datetime.timedelta(hours = 4)
        # medium_utc = start_utc + datetime.timedelta(days = 1)
        # low_utc = start_utc + datetime.timedelta(days=2)

        self.assertEqual(calculate_due_at("critical", start_utc), critical_utc)
        self.assertEqual(calculate_due_at("high", start_utc), high_utc)
        self.assertEqual(calculate_due_at("medium", start_utc), medium_utc)
        self.assertEqual(calculate_due_at("low", start_utc), low_utc)
        with self.assertRaises(ValueError):
            calculate_due_at("urgent", start_utc)
        with self.assertRaises(ValueError):
            calculate_due_at("", start_utc)
        with self.assertRaises(ValueError):
            calculate_due_at(None, start_utc)
        with self.assertRaises(ValueError):
            calculate_due_at("high", None)
        with self.assertRaises(TypeError):
            calculate_due_at("low")
        with self.assertRaises(TypeError):
            calculate_due_at(start_utc)

        naive_start = datetime.datetime(2026, 6, 1, 10, 0, 0)
        with self.assertRaises(ValueError):
            calculate_due_at("high", naive_start)

        original_start = start_utc 
        calculate_due_at("high", start_utc)
        self.assertEqual(start_utc, original_start)
