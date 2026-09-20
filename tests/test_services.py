import tempfile
import unittest
from pathlib import Path

from database import get_connection, initialize_database
from models import Equipment, Loan, Member, TrainingRecord
from services import MakerSpaceService, ServiceError


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


class ServiceCrudTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_makerspace.db"
        self.conn = get_connection(self.db_path)
        initialize_database(self.conn)
        self.service = MakerSpaceService(self.conn)

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_register_member_rejects_blank_and_duplicate_student_id(self):
        with self.assertRaisesRegex(ServiceError, "required"):
            self.service.register_member("", "Amina Doe", "amina@example.com", "555-0101")

        member_id = self.service.register_member("STU001", "Amina Doe", "amina@example.com", "555-0101")
        self.assertIsInstance(member_id, int)

        with self.assertRaisesRegex(ServiceError, "already exists"):
            self.service.register_member("STU001", "Amina Again", "amina2@example.com", "555-0102")

    def test_member_update_and_deactivation(self):
        member_id = self.service.register_member("STU001", "Amina Doe", "amina@example.com", "555-0101")
        self.service.update_member(member_id, name="Amina Mensah", active=False)

        inactive_members = self.service.list_members(include_inactive=True)
        self.assertEqual(inactive_members[0]["name"], "Amina Mensah")
        self.assertEqual(inactive_members[0]["active"], 0)
        self.assertEqual(self.service.list_members(), [])

    def test_register_and_update_equipment(self):
        equipment_id = self.service.register_equipment(
            "Soldering Kit",
            "Electronics",
            "High",
            True,
        )
        self.service.update_equipment(equipment_id, condition_status="Needs Maintenance")

        equipment = self.service.list_equipment()
        self.assertEqual(equipment[0]["name"], "Soldering Kit")
        self.assertEqual(equipment[0]["condition_status"], "Needs Maintenance")
        self.assertEqual(equipment[0]["training_required"], 1)

    def test_training_records_are_category_specific(self):
        member_id = self.service.register_member("STU001", "Amina Doe", "amina@example.com", "555-0101")
        training_id = self.service.add_training(member_id, "Electronics", "2026-09-21")

        self.assertIsInstance(training_id, int)
        self.assertTrue(self.service.member_has_training(member_id, "Electronics"))
        self.assertFalse(self.service.member_has_training(member_id, "Power Tools"))

        with self.assertRaisesRegex(ServiceError, "already has"):
            self.service.add_training(member_id, "Electronics", "2026-09-22")


class CheckoutReturnTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_makerspace.db"
        self.conn = get_connection(self.db_path)
        initialize_database(self.conn)
        self.service = MakerSpaceService(self.conn)
        self.member_id = self.service.register_member("STU001", "Amina Doe", "amina@example.com", "555-0101")
        self.equipment_id = self.service.register_equipment("Soldering Kit", "Electronics", "High", True)

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_checkout_rejects_missing_member_or_equipment(self):
        with self.assertRaisesRegex(ServiceError, "Member ID 999"):
            self.service.checkout_equipment(999, self.equipment_id, checkout_date="2026-09-21")

        with self.assertRaisesRegex(ServiceError, "Equipment ID 999"):
            self.service.checkout_equipment(self.member_id, 999, checkout_date="2026-09-21")

    def test_checkout_requires_matching_category_training(self):
        self.service.add_training(self.member_id, "Power Tools", "2026-09-21")

        with self.assertRaisesRegex(ServiceError, "training for Electronics"):
            self.service.checkout_equipment(self.member_id, self.equipment_id, checkout_date="2026-09-21")

    def test_checkout_succeeds_after_training_and_marks_unavailable(self):
        self.service.add_training(self.member_id, "Electronics", "2026-09-21")
        loan_id = self.service.checkout_equipment(self.member_id, self.equipment_id, checkout_date="2026-09-21")

        self.assertIsInstance(loan_id, int)
        equipment = self.service.list_equipment()[0]
        self.assertEqual(equipment["available"], 0)
        self.assertEqual(len(self.service.list_active_loans()), 1)

    def test_checkout_blocks_unavailable_and_maintenance_equipment(self):
        self.service.add_training(self.member_id, "Electronics", "2026-09-21")
        self.service.checkout_equipment(self.member_id, self.equipment_id, checkout_date="2026-09-21")

        with self.assertRaisesRegex(ServiceError, "not available"):
            self.service.checkout_equipment(self.member_id, self.equipment_id, checkout_date="2026-09-22")

        camera_id = self.service.register_equipment("Camera Kit", "Media", "Medium", False)
        self.service.update_equipment(camera_id, condition_status="Needs Maintenance")
        with self.assertRaisesRegex(ServiceError, "cannot be loaned"):
            self.service.checkout_equipment(self.member_id, camera_id, checkout_date="2026-09-22")

    def test_return_equipment_closes_loan_and_rejects_duplicate_return(self):
        self.service.add_training(self.member_id, "Electronics", "2026-09-21")
        loan_id = self.service.checkout_equipment(self.member_id, self.equipment_id, checkout_date="2026-09-21")

        self.service.return_equipment(loan_id, return_date="2026-09-23")

        equipment = self.service.list_equipment()[0]
        self.assertEqual(equipment["available"], 1)
        self.assertEqual(self.service.list_active_loans(), [])

        with self.assertRaisesRegex(ServiceError, "already returned"):
            self.service.return_equipment(loan_id, return_date="2026-09-24")

    def test_checkout_and_return_reject_invalid_dates_with_service_error(self):
        self.service.add_training(self.member_id, "Electronics", "2026-09-21")

        with self.assertRaisesRegex(ServiceError, "Checkout date must use YYYY-MM-DD"):
            self.service.checkout_equipment(self.member_id, self.equipment_id, checkout_date="bad-date")

        loan_id = self.service.checkout_equipment(self.member_id, self.equipment_id, checkout_date="2026-09-21")
        with self.assertRaisesRegex(ServiceError, "Return date must use YYYY-MM-DD"):
            self.service.return_equipment(loan_id, return_date="bad-date")


class ReportsSearchSeedTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_makerspace.db"
        self.conn = get_connection(self.db_path)
        initialize_database(self.conn)
        self.service = MakerSpaceService(self.conn)

    def tearDown(self):
        self.conn.close()
        self.temp_dir.cleanup()

    def test_search_members_and_equipment_by_partial_text_or_id(self):
        member_id = self.service.register_member("STU001", "Amina Doe", "amina@example.com", "555-0101")
        equipment_id = self.service.register_equipment("Soldering Kit", "Electronics", "High", True)

        self.assertEqual(self.service.search_members("Amina")[0]["member_id"], member_id)
        self.assertEqual(self.service.search_members(str(member_id))[0]["student_id"], "STU001")
        self.assertEqual(self.service.search_equipment("solder")[0]["equipment_id"], equipment_id)
        self.assertEqual(self.service.search_equipment(str(equipment_id))[0]["name"], "Soldering Kit")

    def test_reports_return_expected_rows(self):
        member_id = self.service.register_member("STU001", "Amina Doe", "amina@example.com", "555-0101")
        self.service.add_training(member_id, "Electronics", "2026-09-21")
        soldering_id = self.service.register_equipment("Soldering Kit", "Electronics", "High", True)
        camera_id = self.service.register_equipment("Camera Kit", "Media", "Medium", False)
        self.service.update_equipment(camera_id, condition_status="Needs Maintenance")

        self.service.checkout_equipment(member_id, soldering_id, checkout_date="2026-09-01", loan_days=3)

        self.assertEqual(len(self.service.report_currently_borrowed()), 1)
        self.assertEqual(len(self.service.report_overdue_loans(today="2026-09-10")), 1)
        self.assertEqual(self.service.report_safety_restricted_equipment()[0]["name"], "Soldering Kit")
        self.assertEqual(self.service.report_member_training_summary()[0]["trained_categories"], "Electronics")
        self.assertEqual(self.service.report_equipment_needing_maintenance()[0]["name"], "Camera Kit")

    def test_seed_demo_data_is_idempotent(self):
        self.service.seed_demo_data()
        self.service.seed_demo_data()

        members = self.service.list_members(include_inactive=True)
        equipment = self.service.list_equipment()
        training = self.service.list_training_records()

        self.assertGreaterEqual(len(members), 3)
        self.assertGreaterEqual(len(equipment), 5)
        self.assertGreaterEqual(len(training), 2)
        self.assertEqual(len([m for m in members if m["student_id"] == "STU001"]), 1)


if __name__ == "__main__":
    unittest.main()
