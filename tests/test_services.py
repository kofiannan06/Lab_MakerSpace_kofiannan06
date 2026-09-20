import tempfile
import unittest
from pathlib import Path

from database import get_connection, initialize_database
from models import Equipment, Loan, Member, TrainingRecord


class DatabaseSchemaTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_makerspace.db"
        self.conn = get_connection(self.db_path)
        initialize_database(self.conn)

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_schema_creates_required_tables(self):
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        table_names = {row["name"] for row in rows}

        self.assertIn("members", table_names)
        self.assertIn("equipment", table_names)
        self.assertIn("training_records", table_names)
        self.assertIn("loans", table_names)

    def test_foreign_keys_are_enabled(self):
        result = self.conn.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(result, 1)


class ModelBehaviorTests(unittest.TestCase):
    def test_equipment_loan_rules(self):
        good_item = Equipment(
            equipment_id=1,
            name="Soldering Kit",
            category="Electronics",
            safety_level="High",
            training_required=True,
            condition_status="Good",
            available=True,
        )
        self.assertTrue(good_item.requires_training())
        self.assertTrue(good_item.can_be_loaned())

        maintenance_item = Equipment(
            equipment_id=2,
            name="Laser Cutter",
            category="Power Tools",
            safety_level="High",
            training_required=True,
            condition_status="Needs Maintenance",
            available=True,
        )
        self.assertFalse(maintenance_item.can_be_loaned())

    def test_loan_status_helpers(self):
        loan = Loan(
            loan_id=1,
            member_id=1,
            equipment_id=1,
            checkout_date="2026-09-01",
            due_date="2026-09-10",
            return_date=None,
            status="Active",
        )
        self.assertTrue(loan.is_active())
        self.assertTrue(loan.is_overdue(today="2026-09-11"))
        self.assertFalse(loan.is_overdue(today="2026-09-09"))

    def test_member_and_training_display_labels(self):
        member = Member(1, "STU001", "Amina Doe", "amina@example.com", "555-0101", True)
        training = TrainingRecord(1, 1, "Electronics", "2026-09-21")

        self.assertIn("Amina Doe", member.display_label())
        self.assertIn("Electronics", training.display_label())


if __name__ == "__main__":
    unittest.main()
