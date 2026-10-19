import unittest

from campusflow.duplicates import (
    detect_duplicates,
    normalize_title,
)


class TestDuplicateDetection(unittest.TestCase):

    def setUp(self):
        self.tickets = [
            {
                "id": "T001",
                "title": "Network Connection Failure",
                "category": "Network",
                "status": "open",
            },
            {
                "id": "T002",
                "title": "Printer Not Working",
                "category": "Hardware",
                "status": "in_progress",
            },
            {
                "id": "T003",
                "title": "System Login Error",
                "category": "Software",
                "status": "resolved",
            },
        ]

    def test_normalize_title(self):
        result = normalize_title(
            "  NETWORK   Connection   FAILURE  "
        )

        self.assertEqual(
            result,
            "network connection failure",
        )

    def test_duplicate_with_different_capitalization(self):
        result = detect_duplicates(
            self.tickets,
            "Network",
            "NETWORK CONNECTION FAILURE",
        )

        self.assertEqual(result, ["T001"])

    def test_duplicate_with_extra_spaces(self):
        result = detect_duplicates(
            self.tickets,
            "Network",
            "  Network    Connection Failure ",
        )

        self.assertEqual(result, ["T001"])

    def test_in_progress_ticket_is_detected(self):
        result = detect_duplicates(
            self.tickets,
            "Hardware",
            "Printer Not Working",
        )

        self.assertEqual(result, ["T002"])

    def test_resolved_ticket_is_not_duplicate(self):
        result = detect_duplicates(
            self.tickets,
            "Software",
            "System Login Error",
        )

        self.assertEqual(result, [])

    def test_different_category_is_not_duplicate(self):
        result = detect_duplicates(
            self.tickets,
            "Software",
            "Network Connection Failure",
        )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()