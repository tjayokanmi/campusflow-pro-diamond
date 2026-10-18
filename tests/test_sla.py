import datetime
import unittest 
from campusflow.sla import calculate_due_at, is_overdue

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


class TestSLAOverdue(unittest.TestCase):

    def setUp(self):
        self.now = datetime.datetime(
            2026, 6, 1, 10, 0, 0,
            tzinfo=datetime.timezone.utc,
            )
    def test_is_overdue_tomorrow(self):
        ticket = {
        "status": "open",
        "due_at" : datetime.datetime(
            2026, 6, 2, 10, 0, 0,
            tzinfo=datetime.timezone.utc,
            )
    }
        actual = is_overdue(ticket, self.now)
        self.assertFalse(actual)

    def test_is_overdue_now(self):
        ticket = {
        "status": "open",
        "due_at" : datetime.datetime(
            2026, 6, 1, 10, 0, 0,
            tzinfo=datetime.timezone.utc,
            )
    }
        actual = is_overdue(ticket, self.now)
        self.assertFalse(actual)

    def test_is_overdue_second(self):
        ticket = {
        "status": "open",
        "due_at" : datetime.datetime(
            2026, 6, 1, 9, 59, 59,
            tzinfo=datetime.timezone.utc,
            )
        }
        actual = is_overdue(ticket, self.now)
        self.assertTrue(actual)

    def test_is_overdue_in_progress_deadline_passed(self):
        ticket = {
        "status": "in_progress",
        "due_at" : datetime.datetime(
            2026, 6, 1, 9, 59, 59,
            tzinfo=datetime.timezone.utc,
            )
        }
        actual = is_overdue(ticket, self.now)
        self.assertTrue(actual)


    def test_is_overdue_resolved_deadline_passed(self):
        ticket = {
        "status": "resolved",
        "due_at" : datetime.datetime(
            2026, 6, 1, 9, 59, 59,
            tzinfo=datetime.timezone.utc,
            )
    }
        actual = is_overdue(ticket, self.now)
        self.assertFalse(actual)

    def test_naive_due_at(self):
        ticket = {
        "status": "resolved",
        "due_at" : datetime.datetime(
            2026, 6, 1, 11, 0, 0
            )
        }
        with self.assertRaises(ValueError):
            is_overdue(ticket, self.now)

    def test_now_naive(self):
        now = datetime.datetime(
            2026, 6, 1, 10, 0, 0,
            )
        
        ticket = {
        "status": "resolved",
        "due_at" : datetime.datetime(
            2026, 6, 1, 11, 0, 0,
            tzinfo=datetime.timezone.utc,
            )
        }

        with self.assertRaises(ValueError):
            is_overdue(ticket, now)

    def test_due_at_string(self):   
        ticket = {
        "status": "resolved",
        "due_at" : 'datetime'
        }
            
        with self.assertRaises(TypeError):
            is_overdue(ticket, self.now)

    def test_due_at_non_utc(self):
        ticket = {
            "status": "open",
            "due_at": datetime.datetime(
                2026, 6, 1, 11, 0, 0,
                tzinfo=datetime.timezone(
                    datetime.timedelta(hours=1)
                ),
            ),
        }

        with self.assertRaises(ValueError):
            is_overdue(ticket, self.now)
    
    def test_unsupported_status(self):
        ticket = {
        "status": "pending",
         "due_at" : datetime.datetime(
            2026, 6, 1, 9, 59, 59,
            tzinfo=datetime.timezone.utc,
            )
        }
            
        with self.assertRaises(ValueError):
            is_overdue(ticket, self.now)


    def test_missing_due_at(self):
        ticket = {"status": "open"}

        with self.assertRaises(KeyError):
            is_overdue(ticket, self.now)


    def test_missing_status(self):
        ticket = {
            "due_at": datetime.datetime(
                2026, 6, 1, 9, 59, 59,
                tzinfo=datetime.timezone.utc,
            )
        }

        with self.assertRaises(KeyError):
            is_overdue(ticket, self.now)
