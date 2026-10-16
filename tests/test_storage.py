"""Automated unit tests for CampusFlow JSON persistence."""

import os
import tempfile
import unittest
from campusflow.storage import (
    load_tickets,
    save_tickets,
    load_v2,
    save_v2,
    migrate_v1_to_v2,
    SCHEMA_VERSION,
)
from campusflow.tickets import generate_ticket_id, create_ticket


class TestStorage(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = os.path.join(self.temp_dir.name, "tickets.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_missing_file_returns_empty_list(self):
        """Loading a non-existent file returns an empty list, allowing a fresh start."""
        self.assertFalse(os.path.exists(self.data_path))
        tickets = load_tickets(self.data_path)
        self.assertEqual(tickets, [])

    def test_save_and_load_round_trip(self):
        """Tickets saved to JSON can be reloaded with all fields preserved."""
        original_tickets = [
            {
                "id": "T001",
                "title": "Wi-Fi outage in library",
                "category": "Network",
                "urgency": "high",
                "affected_users": 20,
                "priority": "critical",
                "status": "open",
                "assigned_to": None,
            },
            {
                "id": "T002",
                "title": "Projector broken",
                "category": "Hardware",
                "urgency": "medium",
                "affected_users": 3,
                "priority": "medium",
                "status": "in_progress",
                "assigned_to": "Alice",
            },
        ]

        save_tickets(original_tickets, self.data_path)
        self.assertTrue(os.path.exists(self.data_path))

        loaded_tickets = load_tickets(self.data_path)
        self.assertEqual(loaded_tickets, original_tickets)

    def test_load_malformed_json_raises_value_error(self):
        """Malformed JSON raises ValueError and is never silently erased or replaced."""
        with open(self.data_path, "w", encoding="utf-8") as f:
            f.write("{\ninvalid json data: [not valid")

        with self.assertRaises(ValueError) as ctx:
            load_tickets(self.data_path)
        self.assertIn("Corrupted JSON", str(ctx.exception))

    def test_load_non_list_json_raises_value_error(self):
        """JSON file with root dict or string instead of list raises ValueError."""
        with open(self.data_path, "w", encoding="utf-8") as f:
            f.write('{"error": "not a list"}')

        with self.assertRaises(ValueError) as ctx:
            load_tickets(self.data_path)
        self.assertIn("root JSON structure must be a list", str(ctx.exception))

    def test_load_corrupted_ticket_element_raises_value_error(self):
        """List containing non-dict elements raises ValueError."""
        with open(self.data_path, "w", encoding="utf-8") as f:
            f.write('[{"id": "T001"}, "not a dict"]')

        with self.assertRaises(ValueError) as ctx:
            load_tickets(self.data_path)
        self.assertIn("not a valid ticket dictionary", str(ctx.exception))

    def test_save_creates_parent_directories_if_needed(self):
        """Saving to a nested path creates missing parent directories automatically."""
        nested_path = os.path.join(self.temp_dir.name, "sub", "deep", "tickets.json")
        tickets = [{"id": "T001", "title": "Test"}]
        save_tickets(tickets, nested_path)
        self.assertTrue(os.path.exists(nested_path))
        loaded = load_tickets(nested_path)
        self.assertEqual(loaded, tickets)

    def test_unique_sequential_id_generation_after_reload(self):
        """Reloaded tickets preserve the highest existing ID to maintain sequential IDs."""
        initial_tickets = [
            {"id": "T001", "title": "First ticket"},
            {"id": "T002", "title": "Second ticket"},
            {"id": "T005", "title": "Fifth ticket"},
        ]
        save_tickets(initial_tickets, self.data_path)

        reloaded_tickets = load_tickets(self.data_path)
        next_id = generate_ticket_id(reloaded_tickets)
        self.assertEqual(next_id, "T006")


class TestStorageV2(unittest.TestCase):
    """Automated unit tests for Schema Version 2 JSON persistence and validation."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_path = os.path.join(self.temp_dir.name, "tickets_v2.json")

        self.sample_tickets = [
            {
                "id": "T001",
                "title": "Wi-Fi outage in library",
                "category": "Network",
                "urgency": "high",
                "affected_users": 20,
                "priority": "critical",
                "status": "open",
                "assigned_to": None,
                "created_at": "2026-10-15T09:00:00+00:00",
                "due_at": "2026-10-15T10:00:00+00:00",
                "escalation_cycle": 0,
            },
            {
                "id": "T002",
                "title": "Broken HDMI cable",
                "category": "Hardware",
                "urgency": "low",
                "affected_users": 1,
                "priority": "low",
                "status": "in_progress",
                "assigned_to": "Bob",
                "created_at": "2026-10-15T09:30:00+00:00",
                "due_at": "2026-10-17T09:30:00+00:00",
                "escalation_cycle": 0,
            },
        ]

        self.sample_events = [
            {
                "event_id": "E001",
                "ticket_id": "T001",
                "event_type": "CREATE",
                "actor": "Admin",
                "timestamp": "2026-10-15T09:00:00+00:00",
                "before_status": None,
                "after_status": "open",
                "details": "Ticket created",
            },
            {
                "event_id": "E002",
                "ticket_id": "T002",
                "event_type": "ASSIGN",
                "actor": "Admin",
                "timestamp": "2026-10-15T09:35:00+00:00",
                "before_status": "open",
                "after_status": "in_progress",
                "details": "Assigned to Bob",
            },
        ]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_v2_missing_file_returns_empty_structure(self):
        """Loading a non-existent file returns an empty v2 payload."""
        data = load_v2(self.data_path)
        self.assertEqual(data["schema_version"], SCHEMA_VERSION)
        self.assertEqual(data["tickets"], [])
        self.assertEqual(data["events"], [])

    def test_v2_empty_dataset_round_trip(self):
        """Saving empty dataset produces valid v2 file that reloads properly."""
        save_v2([], [], self.data_path)
        self.assertTrue(os.path.exists(self.data_path))
        loaded = load_v2(self.data_path)
        self.assertEqual(loaded["schema_version"], SCHEMA_VERSION)
        self.assertEqual(loaded["tickets"], [])
        self.assertEqual(loaded["events"], [])

    def test_v2_round_trip_preserves_tickets_and_events(self):
        """Saving and loading tickets and events preserves all fields and structures."""
        save_v2(self.sample_tickets, self.sample_events, self.data_path)
        loaded = load_v2(self.data_path)
        self.assertEqual(loaded["schema_version"], 2)
        self.assertEqual(loaded["tickets"], self.sample_tickets)
        self.assertEqual(loaded["events"], self.sample_events)

    def test_v2_malformed_json_raises_value_error(self):
        """Malformed JSON string raises ValueError."""
        with open(self.data_path, "w", encoding="utf-8") as f:
            f.write("{invalid: json, [unclosed")
        with self.assertRaises(ValueError) as ctx:
            load_v2(self.data_path)
        self.assertIn("Corrupted JSON", str(ctx.exception))

    def test_v2_non_dict_root_raises_value_error(self):
        """Root JSON structure that is a list raises ValueError."""
        with open(self.data_path, "w", encoding="utf-8") as f:
            f.write("[]")
        with self.assertRaises(ValueError) as ctx:
            load_v2(self.data_path)
        self.assertIn("root JSON structure must be", str(ctx.exception))

    def test_v2_missing_or_invalid_schema_version(self):
        """Missing or wrong schema_version raises ValueError."""
        with open(self.data_path, "w", encoding="utf-8") as f:
            f.write('{"tickets": [], "events": []}')
        with self.assertRaises(ValueError) as ctx:
            load_v2(self.data_path)
        self.assertIn("missing 'schema_version'", str(ctx.exception))

        with open(self.data_path, "w", encoding="utf-8") as f:
            f.write('{"schema_version": 999, "tickets": [], "events": []}')
        with self.assertRaises(ValueError) as ctx:
            load_v2(self.data_path)
        self.assertIn("unsupported schema_version", str(ctx.exception))

    def test_v2_missing_tickets_or_events_field(self):
        """Missing 'tickets' or 'events' field raises ValueError."""
        with open(self.data_path, "w", encoding="utf-8") as f:
            f.write('{"schema_version": 2, "events": []}')
        with self.assertRaises(ValueError) as ctx:
            load_v2(self.data_path)
        self.assertIn("'tickets' must be a list", str(ctx.exception))

        with open(self.data_path, "w", encoding="utf-8") as f:
            f.write('{"schema_version": 2, "tickets": []}')
        with self.assertRaises(ValueError) as ctx:
            load_v2(self.data_path)
        self.assertIn("'events' must be a list", str(ctx.exception))

    def test_v2_corrupted_ticket_missing_required_fields(self):
        """Ticket missing required fields raises ValueError."""
        corrupted = [
            {"id": "T001", "title": "Wi-Fi"}  # missing category, urgency, etc.
        ]
        with self.assertRaises(ValueError) as ctx:
            save_v2(corrupted, [], self.data_path)
        self.assertIn("missing required field", str(ctx.exception))

    def test_v2_corrupted_ticket_invalid_field_values(self):
        """Ticket with invalid category, urgency, affected_users, priority, or status raises ValueError."""
        bad_ticket = dict(self.sample_tickets[0])
        bad_ticket["category"] = "Finance"  # Invalid category
        with self.assertRaises(ValueError) as ctx1:
            save_v2([bad_ticket], [], self.data_path)
        self.assertIn("invalid category", str(ctx1.exception))

        bad_ticket2 = dict(self.sample_tickets[0])
        bad_ticket2["affected_users"] = 0  # Must be >= 1
        with self.assertRaises(ValueError) as ctx2:
            save_v2([bad_ticket2], [], self.data_path)
        self.assertIn("affected_users must be an integer >= 1", str(ctx2.exception))

        bad_ticket3 = dict(self.sample_tickets[0])
        bad_ticket3["status"] = "cancelled"  # Invalid status
        with self.assertRaises(ValueError) as ctx3:
            save_v2([bad_ticket3], [], self.data_path)
        self.assertIn("invalid status", str(ctx3.exception))

    def test_v2_duplicate_ticket_ids_raises_value_error(self):
        """Duplicate ticket IDs in payload raise ValueError."""
        duplicate_tickets = [
            dict(self.sample_tickets[0]),
            dict(self.sample_tickets[0]),
        ]
        with self.assertRaises(ValueError) as ctx:
            save_v2(duplicate_tickets, [], self.data_path)
        self.assertIn("duplicate ticket ID", str(ctx.exception))

    def test_v2_corrupted_event_missing_or_invalid_fields(self):
        """Event with missing fields or invalid status raises ValueError."""
        bad_event = {"event_id": "E001"}  # Missing ticket_id, actor, etc.
        with self.assertRaises(ValueError) as ctx:
            save_v2(self.sample_tickets, [bad_event], self.data_path)
        self.assertIn("missing required field", str(ctx.exception))

        bad_event2 = dict(self.sample_events[0])
        bad_event2["before_status"] = "pending_approval"  # Invalid status
        with self.assertRaises(ValueError) as ctx2:
            save_v2(self.sample_tickets, [bad_event2], self.data_path)
        self.assertIn("invalid before_status", str(ctx2.exception))

    def test_v2_duplicate_event_ids_raises_value_error(self):
        """Duplicate event IDs in payload raise ValueError."""
        duplicate_events = [
            dict(self.sample_events[0]),
            dict(self.sample_events[0]),
        ]
        with self.assertRaises(ValueError) as ctx:
            save_v2(self.sample_tickets, duplicate_events, self.data_path)
        self.assertIn("duplicate event ID", str(ctx.exception))

    def test_v2_invalid_event_relationship_missing_ticket_id(self):
        """Event referencing an unknown ticket ID raises ValueError."""
        orphan_event = dict(self.sample_events[0])
        orphan_event["ticket_id"] = "T999"  # Does not exist in tickets
        with self.assertRaises(ValueError) as ctx:
            save_v2(self.sample_tickets, [orphan_event], self.data_path)
        self.assertIn("references unknown ticket ID 'T999'", str(ctx.exception))

    def test_v2_id_continuity_after_reload(self):
        """Reloading v2 data preserves max ticket ID and generates unique next sequential ID."""
        save_v2(self.sample_tickets, self.sample_events, self.data_path)
        loaded = load_v2(self.data_path)
        next_id = generate_ticket_id(loaded["tickets"])
        self.assertEqual(next_id, "T003")

        # Create new ticket with next_id and ensure it saves and increments again
        new_ticket = create_ticket("Server reboot", "Hardware", "medium", 5, records=loaded["tickets"])
        self.assertEqual(new_ticket["id"], "T003")
        loaded["tickets"].append(new_ticket)
        save_v2(loaded["tickets"], loaded["events"], self.data_path)

        reloaded = load_v2(self.data_path)
        self.assertEqual(len(reloaded["tickets"]), 3)
        self.assertEqual(generate_ticket_id(reloaded["tickets"]), "T004")

    def test_v2_atomic_replacement_failure_cleans_up_and_preserves_original(self):
        """Failed save does not mutate existing valid file and cleans up temp files."""
        save_v2(self.sample_tickets, self.sample_events, self.data_path)
        original_mtime = os.path.getmtime(self.data_path)

        # Attempt to save invalid data
        with self.assertRaises(ValueError):
            save_v2([{"invalid": "ticket"}], [], self.data_path)

        # Confirm original file remains valid and unmodified
        self.assertEqual(os.path.getmtime(self.data_path), original_mtime)
        reloaded = load_v2(self.data_path)
        self.assertEqual(reloaded["tickets"], self.sample_tickets)

        # Confirm no leftover temporary files in directory
        dir_files = os.listdir(self.temp_dir.name)
        self.assertEqual(dir_files, ["tickets_v2.json"])

    def test_migrate_v1_to_v2_preserves_original(self):
        """migrate_v1_to_v2 converts legacy JSON to v2 and keeps original file intact."""
        v1_path = os.path.join(self.temp_dir.name, "legacy_v1.json")
        v2_path = os.path.join(self.temp_dir.name, "migrated_v2.json")

        with open(v1_path, "w", encoding="utf-8") as f:
            import json
            json.dump(self.sample_tickets, f)

        with open(v1_path, "r", encoding="utf-8") as f:
            v1_content_before = f.read()

        migrated = migrate_v1_to_v2(v1_path, v2_path)
        self.assertEqual(migrated["schema_version"], 2)
        self.assertEqual(migrated["tickets"], self.sample_tickets)
        self.assertEqual(migrated["events"], [])

        # Check that original v1 file was NOT altered
        with open(v1_path, "r", encoding="utf-8") as f:
            v1_content_after = f.read()
        self.assertEqual(v1_content_before, v1_content_after)

        # Check that migrated v2 file exists and is valid
        loaded_v2 = load_v2(v2_path)
        self.assertEqual(loaded_v2["schema_version"], 2)
        self.assertEqual(loaded_v2["tickets"], self.sample_tickets)


if __name__ == "__main__":
    unittest.main()
