import datetime
import unittest 
from campusflow.sla import calculate_due_at

class TestSLADeadline(unittest.TestCase):
    def setUp(self):
        self.start_utc = datetime.datetime(
            2026, 6, 1, 10, 0, 0,
            tzinfo=datetime.timezone.utc,
            )
        
    def test_sla_durations(self):
        critical_utc = datetime.datetime(2026, 6, 1, 11, 0, 0, tzinfo=datetime.timezone.utc)
        high_utc = datetime.datetime(2026, 6, 1, 14, 0, 0, tzinfo=datetime.timezone.utc)
        medium_utc = datetime.datetime(2026, 6, 2, 10, 0, 0, tzinfo=datetime.timezone.utc)
        low_utc = datetime.datetime(2026, 6, 3, 10, 0, 0, tzinfo=datetime.timezone.utc)
       
        self.assertEqual(calculate_due_at("critical", self.start_utc), critical_utc)
        self.assertEqual(calculate_due_at("high", self.start_utc), high_utc)
        self.assertEqual(calculate_due_at("medium", self.start_utc), medium_utc)
        self.assertEqual(calculate_due_at("low", self.start_utc), low_utc)

    
    def test_invalid_priority(self):        
        with self.assertRaises(ValueError):
            calculate_due_at("urgent", self.start_utc)
        with self.assertRaises(ValueError):
            calculate_due_at("", self.start_utc)
        with self.assertRaises(ValueError):
            calculate_due_at(None, self.start_utc)

    def test_invalid_start_time(self):
        with self.assertRaises(TypeError):
            calculate_due_at("high", None)

        naive_start = datetime.datetime(2026, 6, 1, 10, 0)
        with self.assertRaises(ValueError):
            calculate_due_at("high", naive_start)

    def test_invalid_start_time_type(self):
        with self.assertRaises(TypeError):
            calculate_due_at("high", "start_utc")

    def test_missing_arguments(self):
        with self.assertRaises(TypeError):
            calculate_due_at("low")

        with self.assertRaises(TypeError):
            calculate_due_at(self.start_utc)

    def test_start_time_unchanged(self):
        original_start = self.start_utc 
        calculate_due_at("high", self.start_utc)
        self.assertEqual(self.start_utc, original_start)

    def test_non_utc_datetime_raises_value_error(self):
        non_utc_start = datetime.datetime(
            2026, 6, 1, 10, 0, 0,
            tzinfo=datetime.timezone(datetime.timedelta(hours=1)),
        )

        with self.assertRaises(ValueError):
            calculate_due_at("high", non_utc_start)

            