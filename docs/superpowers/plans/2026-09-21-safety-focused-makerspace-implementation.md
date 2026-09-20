# Safety-Focused MakerSpace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a menu-driven Python SQLite MakerSpace checkout system with category-based safety training validation.

**Architecture:** The app is split into domain models, SQLite database helpers, a service layer, and a CLI entry point. Tests exercise service workflows against temporary SQLite databases so the core rules can be verified without driving the interactive menu.

**Tech Stack:** Python 3 standard library only: `sqlite3`, `dataclasses`, `datetime`, `pathlib`, `tempfile`, and `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-21-safety-focused-makerspace-design.md`

## Global Constraints

- The application runs from `main.py` as a menu-driven CLI.
- Data persists in an SQLite database file between runs.
- Use SQLite through Python's standard-library `sqlite3` module.
- Use meaningful OOP classes: `Member`, `Equipment`, `Loan`, and `TrainingRecord`.
- Use category-specific safety training through the `training_records` table.
- Reject checkout when equipment requires training and the member lacks training for that category.
- Include SQL-backed reports for currently borrowed equipment, overdue loans, safety-restricted equipment, member training summary, and equipment needing maintenance.
- Keep dependencies minimal; `requirements.txt` must not require third-party packages.
- README must explain setup, class design, database tables, demo flow, and AI assistance disclosure.

## Review Focus

- Duplicate sample-data seeding should not crash or create duplicate logical records; Task 4 tests idempotent seeding.
- Invalid checkout IDs should produce a clear service error instead of an uncaught database error; Task 3 tests missing member and missing equipment.
- Training-required equipment should be blocked only when the member lacks that category, not when they are trained for a different category; Task 3 tests wrong-category training.
- Returned loans should not be returned again; Task 3 tests duplicate return rejection.
- Search should work with partial names and exact IDs for both members and equipment; Task 4 tests search behavior.

---

## File Structure

- `models.py`: dataclass domain objects with small behavior methods.
- `database.py`: database connection factory, schema creation, row helpers, and default database path.
- `services.py`: `MakerSpaceService`, validation, CRUD operations, checkout/return workflows, search, reports, and demo-data seeding.
- `main.py`: CLI menu, input parsing, display formatting, and calls into `MakerSpaceService`.
- `tests/test_services.py`: `unittest` coverage for schema, CRUD, safety validation, reports, search, and seeding.
- `README.md`: run instructions, feature summary, class/table explanation, demo script, rubric checklist, AI disclosure.
- `requirements.txt`: intentionally empty except for a note that the project uses standard-library modules.

## Task 1: Models And Database Schema

**Files:**
- Create: `models.py`
- Create: `database.py`
- Create: `tests/test_services.py`
- Create: `requirements.txt`

**Interfaces:**
- Produces: `Member`, `Equipment`, `TrainingRecord`, `Loan` dataclasses.
- Produces: `get_connection(db_path: str | Path) -> sqlite3.Connection`.
- Produces: `initialize_database(conn: sqlite3.Connection) -> None`.
- Produces: `dict_from_row(row: sqlite3.Row) -> dict`.

- [ ] **Step 1: Write failing schema and model tests**

Add this initial test content to `tests/test_services.py`:

```python
import sqlite3
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_services -v`

Expected: FAIL with import errors for `database` and `models`.

- [ ] **Step 3: Implement domain models**

Create `models.py`:

```python
from dataclasses import dataclass
from datetime import date


@dataclass
class Member:
    member_id: int | None
    student_id: str
    name: str
    email: str
    phone: str
    active: bool = True

    def display_label(self) -> str:
        status = "Active" if self.active else "Inactive"
        return f"{self.member_id}: {self.name} ({self.student_id}) - {status}"


@dataclass
class Equipment:
    equipment_id: int | None
    name: str
    category: str
    safety_level: str
    training_required: bool
    condition_status: str = "Good"
    available: bool = True

    def is_available(self) -> bool:
        return self.available

    def requires_training(self) -> bool:
        return self.training_required

    def can_be_loaned(self) -> bool:
        return self.available and self.condition_status == "Good"

    def display_label(self) -> str:
        availability = "Available" if self.available else "Borrowed"
        training = "Training required" if self.training_required else "No training required"
        return f"{self.equipment_id}: {self.name} [{self.category}] - {availability}, {self.condition_status}, {training}"


@dataclass
class TrainingRecord:
    training_id: int | None
    member_id: int
    category: str
    completed_date: str

    def display_label(self) -> str:
        return f"{self.training_id}: member {self.member_id} trained for {self.category} on {self.completed_date}"


@dataclass
class Loan:
    loan_id: int | None
    member_id: int
    equipment_id: int
    checkout_date: str
    due_date: str
    return_date: str | None = None
    status: str = "Active"

    def is_active(self) -> bool:
        return self.status == "Active" and self.return_date is None

    def is_overdue(self, today: str | None = None) -> bool:
        compare_date = date.fromisoformat(today) if today else date.today()
        due = date.fromisoformat(self.due_date)
        return self.is_active() and due < compare_date

    def mark_returned(self, return_date: str) -> None:
        self.return_date = return_date
        self.status = "Returned"
```

- [ ] **Step 4: Implement database schema**

Create `database.py`:

```python
import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path("makerspace.db")


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS members (
            member_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            active INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS equipment (
            equipment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            safety_level TEXT NOT NULL,
            training_required INTEGER NOT NULL DEFAULT 0,
            condition_status TEXT NOT NULL DEFAULT 'Good',
            available INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS training_records (
            training_id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            completed_date TEXT NOT NULL,
            FOREIGN KEY (member_id) REFERENCES members(member_id),
            UNIQUE(member_id, category)
        );

        CREATE TABLE IF NOT EXISTS loans (
            loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER NOT NULL,
            equipment_id INTEGER NOT NULL,
            checkout_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            return_date TEXT,
            status TEXT NOT NULL DEFAULT 'Active',
            FOREIGN KEY (member_id) REFERENCES members(member_id),
            FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
        );
        """
    )
    conn.commit()


def dict_from_row(row: sqlite3.Row) -> dict:
    return dict(row)
```

Create `requirements.txt`:

```text
# No third-party dependencies required.
# This project uses Python standard-library modules, including sqlite3 and unittest.
```

- [ ] **Step 5: Run tests to verify Task 1 passes**

Run: `python -m unittest tests.test_services -v`

Expected: PASS for all Task 1 tests.

- [ ] **Step 6: Commit Task 1**

Run:

```bash
git add models.py database.py tests/test_services.py requirements.txt
git commit -m "Add models and SQLite schema"
```

## Task 2: Member, Equipment, And Training Services

**Files:**
- Create: `services.py`
- Modify: `tests/test_services.py`

**Interfaces:**
- Consumes: `get_connection`, `initialize_database`, and dataclasses from Task 1.
- Produces: `ServiceError(Exception)`.
- Produces: `MakerSpaceService(conn: sqlite3.Connection)`.
- Produces: `register_member(student_id: str, name: str, email: str, phone: str) -> int`.
- Produces: `list_members(include_inactive: bool = False) -> list[dict]`.
- Produces: `update_member(member_id: int, name: str | None = None, email: str | None = None, phone: str | None = None, active: bool | None = None) -> None`.
- Produces: `register_equipment(name: str, category: str, safety_level: str, training_required: bool, condition_status: str = "Good") -> int`.
- Produces: `list_equipment() -> list[dict]`.
- Produces: `update_equipment(equipment_id: int, name: str | None = None, category: str | None = None, safety_level: str | None = None, training_required: bool | None = None, condition_status: str | None = None, available: bool | None = None) -> None`.
- Produces: `add_training(member_id: int, category: str, completed_date: str) -> int`.
- Produces: `member_has_training(member_id: int, category: str) -> bool`.
- Produces: `list_training_records() -> list[dict]`.

- [ ] **Step 1: Add failing service CRUD tests**

Append these tests to `tests/test_services.py` above the `if __name__ == "__main__"` block:

```python
from services import MakerSpaceService, ServiceError


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_services -v`

Expected: FAIL with import error for `services`.

- [ ] **Step 3: Implement service CRUD operations**

Create `services.py`:

```python
import sqlite3
from datetime import date, timedelta


VALID_CONDITIONS = {"Good", "Needs Maintenance", "Retired"}


class ServiceError(Exception):
    """Raised when a user action cannot be completed safely."""


class MakerSpaceService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _require_text(self, value: str, field_name: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ServiceError(f"{field_name} is required.")
        return cleaned

    def _require_date(self, value: str, field_name: str) -> str:
        cleaned = self._require_text(value, field_name)
        try:
            date.fromisoformat(cleaned)
        except ValueError as exc:
            raise ServiceError(f"{field_name} must use YYYY-MM-DD format.") from exc
        return cleaned

    def register_member(self, student_id: str, name: str, email: str, phone: str) -> int:
        student_id = self._require_text(student_id, "Student ID")
        name = self._require_text(name, "Member name")
        try:
            cursor = self.conn.execute(
                "INSERT INTO members (student_id, name, email, phone) VALUES (?, ?, ?, ?)",
                (student_id, name, email.strip(), phone.strip()),
            )
            self.conn.commit()
            return int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise ServiceError(f"Member with student ID {student_id} already exists.") from exc

    def list_members(self, include_inactive: bool = False) -> list[dict]:
        if include_inactive:
            rows = self.conn.execute("SELECT * FROM members ORDER BY name").fetchall()
        else:
            rows = self.conn.execute("SELECT * FROM members WHERE active = 1 ORDER BY name").fetchall()
        return [dict(row) for row in rows]

    def update_member(
        self,
        member_id: int,
        name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        active: bool | None = None,
    ) -> None:
        member = self._get_member(member_id)
        updated = {
            "name": self._require_text(name, "Member name") if name is not None else member["name"],
            "email": email.strip() if email is not None else member["email"],
            "phone": phone.strip() if phone is not None else member["phone"],
            "active": int(active) if active is not None else member["active"],
            "member_id": member_id,
        }
        self.conn.execute(
            """
            UPDATE members
            SET name = :name, email = :email, phone = :phone, active = :active
            WHERE member_id = :member_id
            """,
            updated,
        )
        self.conn.commit()

    def register_equipment(
        self,
        name: str,
        category: str,
        safety_level: str,
        training_required: bool,
        condition_status: str = "Good",
    ) -> int:
        name = self._require_text(name, "Equipment name")
        category = self._require_text(category, "Category")
        safety_level = self._require_text(safety_level, "Safety level")
        if condition_status not in VALID_CONDITIONS:
            raise ServiceError("Condition must be Good, Needs Maintenance, or Retired.")
        cursor = self.conn.execute(
            """
            INSERT INTO equipment (name, category, safety_level, training_required, condition_status, available)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (name, category, safety_level, int(training_required), condition_status),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_equipment(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM equipment ORDER BY category, name").fetchall()
        return [dict(row) for row in rows]

    def update_equipment(
        self,
        equipment_id: int,
        name: str | None = None,
        category: str | None = None,
        safety_level: str | None = None,
        training_required: bool | None = None,
        condition_status: str | None = None,
        available: bool | None = None,
    ) -> None:
        equipment = self._get_equipment(equipment_id)
        new_condition = condition_status if condition_status is not None else equipment["condition_status"]
        if new_condition not in VALID_CONDITIONS:
            raise ServiceError("Condition must be Good, Needs Maintenance, or Retired.")
        updated = {
            "name": self._require_text(name, "Equipment name") if name is not None else equipment["name"],
            "category": self._require_text(category, "Category") if category is not None else equipment["category"],
            "safety_level": self._require_text(safety_level, "Safety level") if safety_level is not None else equipment["safety_level"],
            "training_required": int(training_required) if training_required is not None else equipment["training_required"],
            "condition_status": new_condition,
            "available": int(available) if available is not None else equipment["available"],
            "equipment_id": equipment_id,
        }
        self.conn.execute(
            """
            UPDATE equipment
            SET name = :name,
                category = :category,
                safety_level = :safety_level,
                training_required = :training_required,
                condition_status = :condition_status,
                available = :available
            WHERE equipment_id = :equipment_id
            """,
            updated,
        )
        self.conn.commit()

    def add_training(self, member_id: int, category: str, completed_date: str) -> int:
        self._get_member(member_id)
        category = self._require_text(category, "Training category")
        completed_date = self._require_date(completed_date, "Completed date")
        try:
            cursor = self.conn.execute(
                """
                INSERT INTO training_records (member_id, category, completed_date)
                VALUES (?, ?, ?)
                """,
                (member_id, category, completed_date),
            )
            self.conn.commit()
            return int(cursor.lastrowid)
        except sqlite3.IntegrityError as exc:
            raise ServiceError(f"Member already has training for {category}.") from exc

    def member_has_training(self, member_id: int, category: str) -> bool:
        row = self.conn.execute(
            """
            SELECT 1 FROM training_records
            WHERE member_id = ? AND lower(category) = lower(?)
            """,
            (member_id, category),
        ).fetchone()
        return row is not None

    def list_training_records(self) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT tr.training_id, tr.member_id, m.name AS member_name, tr.category, tr.completed_date
            FROM training_records tr
            JOIN members m ON m.member_id = tr.member_id
            ORDER BY m.name, tr.category
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def _get_member(self, member_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM members WHERE member_id = ?", (member_id,)).fetchone()
        if row is None:
            raise ServiceError(f"Member ID {member_id} was not found.")
        return dict(row)

    def _get_equipment(self, equipment_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM equipment WHERE equipment_id = ?", (equipment_id,)).fetchone()
        if row is None:
            raise ServiceError(f"Equipment ID {equipment_id} was not found.")
        return dict(row)
```

- [ ] **Step 4: Run tests to verify Task 2 passes**

Run: `python -m unittest tests.test_services -v`

Expected: PASS for Task 1 and Task 2 tests.

- [ ] **Step 5: Commit Task 2**

Run:

```bash
git add services.py tests/test_services.py
git commit -m "Add member equipment and training services"
```

## Task 3: Checkout And Return Workflows

**Files:**
- Modify: `services.py`
- Modify: `tests/test_services.py`

**Interfaces:**
- Consumes: Task 2 `MakerSpaceService`.
- Produces: `checkout_equipment(member_id: int, equipment_id: int, checkout_date: str | None = None, loan_days: int = 7) -> int`.
- Produces: `return_equipment(loan_id: int, return_date: str | None = None) -> None`.
- Produces: `list_active_loans() -> list[dict]`.

- [ ] **Step 1: Add failing checkout and return tests**

Append these tests above the `if __name__ == "__main__"` block:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_services -v`

Expected: FAIL because checkout and return methods are missing.

- [ ] **Step 3: Implement checkout and return workflows**

Add these methods to `MakerSpaceService` in `services.py`:

```python
    def checkout_equipment(
        self,
        member_id: int,
        equipment_id: int,
        checkout_date: str | None = None,
        loan_days: int = 7,
    ) -> int:
        member = self._get_member(member_id)
        equipment = self._get_equipment(equipment_id)

        if not member["active"]:
            raise ServiceError("Inactive members cannot borrow equipment.")
        if not equipment["available"]:
            raise ServiceError(f"{equipment['name']} is not available.")
        if equipment["condition_status"] != "Good":
            raise ServiceError(f"{equipment['name']} cannot be loaned because its condition is {equipment['condition_status']}.")
        if equipment["training_required"] and not self.member_has_training(member_id, equipment["category"]):
            raise ServiceError(f"{member['name']} needs training for {equipment['category']} before checkout.")

        checkout = date.fromisoformat(checkout_date) if checkout_date else date.today()
        due = checkout + timedelta(days=loan_days)
        cursor = self.conn.execute(
            """
            INSERT INTO loans (member_id, equipment_id, checkout_date, due_date, status)
            VALUES (?, ?, ?, ?, 'Active')
            """,
            (member_id, equipment_id, checkout.isoformat(), due.isoformat()),
        )
        self.conn.execute(
            "UPDATE equipment SET available = 0 WHERE equipment_id = ?",
            (equipment_id,),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def return_equipment(self, loan_id: int, return_date: str | None = None) -> None:
        loan = self._get_loan(loan_id)
        if loan["status"] != "Active" or loan["return_date"] is not None:
            raise ServiceError(f"Loan ID {loan_id} was already returned.")

        returned = date.fromisoformat(return_date).isoformat() if return_date else date.today().isoformat()
        self.conn.execute(
            """
            UPDATE loans
            SET return_date = ?, status = 'Returned'
            WHERE loan_id = ?
            """,
            (returned, loan_id),
        )
        self.conn.execute(
            "UPDATE equipment SET available = 1 WHERE equipment_id = ?",
            (loan["equipment_id"],),
        )
        self.conn.commit()

    def list_active_loans(self) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT l.loan_id,
                   m.name AS member_name,
                   e.name AS equipment_name,
                   e.category,
                   l.checkout_date,
                   l.due_date,
                   l.status
            FROM loans l
            JOIN members m ON m.member_id = l.member_id
            JOIN equipment e ON e.equipment_id = l.equipment_id
            WHERE l.status = 'Active'
            ORDER BY l.due_date
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def _get_loan(self, loan_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM loans WHERE loan_id = ?", (loan_id,)).fetchone()
        if row is None:
            raise ServiceError(f"Loan ID {loan_id} was not found.")
        return dict(row)
```

- [ ] **Step 4: Run tests to verify Task 3 passes**

Run: `python -m unittest tests.test_services -v`

Expected: PASS for Task 1 through Task 3.

- [ ] **Step 5: Commit Task 3**

Run:

```bash
git add services.py tests/test_services.py
git commit -m "Add checkout and return workflows"
```

## Task 4: Reports, Search, And Demo Data

**Files:**
- Modify: `services.py`
- Modify: `tests/test_services.py`

**Interfaces:**
- Consumes: Task 3 service methods.
- Produces: `search_members(query: str) -> list[dict]`.
- Produces: `search_equipment(query: str) -> list[dict]`.
- Produces: `report_currently_borrowed() -> list[dict]`.
- Produces: `report_overdue_loans(today: str | None = None) -> list[dict]`.
- Produces: `report_safety_restricted_equipment() -> list[dict]`.
- Produces: `report_member_training_summary() -> list[dict]`.
- Produces: `report_equipment_needing_maintenance() -> list[dict]`.
- Produces: `seed_demo_data() -> None`.

- [ ] **Step 1: Add failing report, search, and seeding tests**

Append these tests above the `if __name__ == "__main__"` block:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_services -v`

Expected: FAIL because report, search, and seed methods are missing.

- [ ] **Step 3: Implement search methods**

Add these methods to `MakerSpaceService`:

```python
    def search_members(self, query: str) -> list[dict]:
        cleaned = self._require_text(query, "Search query")
        pattern = f"%{cleaned.lower()}%"
        rows = self.conn.execute(
            """
            SELECT * FROM members
            WHERE lower(name) LIKE ?
               OR lower(student_id) LIKE ?
               OR CAST(member_id AS TEXT) = ?
            ORDER BY name
            """,
            (pattern, pattern, cleaned),
        ).fetchall()
        return [dict(row) for row in rows]

    def search_equipment(self, query: str) -> list[dict]:
        cleaned = self._require_text(query, "Search query")
        pattern = f"%{cleaned.lower()}%"
        rows = self.conn.execute(
            """
            SELECT * FROM equipment
            WHERE lower(name) LIKE ?
               OR lower(category) LIKE ?
               OR CAST(equipment_id AS TEXT) = ?
            ORDER BY category, name
            """,
            (pattern, pattern, cleaned),
        ).fetchall()
        return [dict(row) for row in rows]
```

- [ ] **Step 4: Implement reports**

Add these methods to `MakerSpaceService`:

```python
    def report_currently_borrowed(self) -> list[dict]:
        return self.list_active_loans()

    def report_overdue_loans(self, today: str | None = None) -> list[dict]:
        compare = date.fromisoformat(today).isoformat() if today else date.today().isoformat()
        rows = self.conn.execute(
            """
            SELECT l.loan_id,
                   m.name AS member_name,
                   e.name AS equipment_name,
                   e.category,
                   l.checkout_date,
                   l.due_date
            FROM loans l
            JOIN members m ON m.member_id = l.member_id
            JOIN equipment e ON e.equipment_id = l.equipment_id
            WHERE l.status = 'Active' AND l.due_date < ?
            ORDER BY l.due_date
            """,
            (compare,),
        ).fetchall()
        return [dict(row) for row in rows]

    def report_safety_restricted_equipment(self) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT equipment_id, name, category, safety_level, condition_status, available
            FROM equipment
            WHERE training_required = 1
            ORDER BY safety_level DESC, category, name
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def report_member_training_summary(self) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT m.member_id,
                   m.name,
                   m.student_id,
                   COALESCE(group_concat(tr.category, ', '), 'No training') AS trained_categories
            FROM members m
            LEFT JOIN training_records tr ON tr.member_id = m.member_id
            GROUP BY m.member_id, m.name, m.student_id
            ORDER BY m.name
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def report_equipment_needing_maintenance(self) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT equipment_id, name, category, safety_level, condition_status
            FROM equipment
            WHERE condition_status IN ('Needs Maintenance', 'Retired')
            ORDER BY condition_status, category, name
            """
        ).fetchall()
        return [dict(row) for row in rows]
```

- [ ] **Step 5: Implement idempotent sample-data seeding**

Add this method to `MakerSpaceService`:

```python
    def seed_demo_data(self) -> None:
        members = [
            ("STU001", "Amina Doe", "amina@example.com", "555-0101"),
            ("STU002", "Kofi Mensah", "kofi@example.com", "555-0102"),
            ("STU003", "Lina Patel", "lina@example.com", "555-0103"),
        ]
        for student_id, name, email, phone in members:
            if not self.conn.execute("SELECT 1 FROM members WHERE student_id = ?", (student_id,)).fetchone():
                self.register_member(student_id, name, email, phone)

        equipment_items = [
            ("Soldering Kit", "Electronics", "High", True, "Good"),
            ("3D Printer Nozzle Set", "3D Printing", "Medium", True, "Good"),
            ("DSLR Camera Kit", "Media", "Medium", False, "Good"),
            ("Cordless Drill", "Power Tools", "High", True, "Needs Maintenance"),
            ("Measuring Caliper", "General Tools", "Low", False, "Good"),
        ]
        for name, category, safety_level, training_required, condition_status in equipment_items:
            if not self.conn.execute("SELECT 1 FROM equipment WHERE name = ?", (name,)).fetchone():
                self.register_equipment(name, category, safety_level, training_required, condition_status)

        amina = self.conn.execute("SELECT member_id FROM members WHERE student_id = 'STU001'").fetchone()
        kofi = self.conn.execute("SELECT member_id FROM members WHERE student_id = 'STU002'").fetchone()
        if amina and not self.member_has_training(amina["member_id"], "Electronics"):
            self.add_training(amina["member_id"], "Electronics", "2026-09-21")
        if kofi and not self.member_has_training(kofi["member_id"], "3D Printing"):
            self.add_training(kofi["member_id"], "3D Printing", "2026-09-21")
```

- [ ] **Step 6: Run tests to verify Task 4 passes**

Run: `python -m unittest tests.test_services -v`

Expected: PASS for Task 1 through Task 4.

- [ ] **Step 7: Commit Task 4**

Run:

```bash
git add services.py tests/test_services.py
git commit -m "Add reports search and demo data"
```

## Task 5: Interactive CLI

**Files:**
- Create: `main.py`

**Interfaces:**
- Consumes: `get_connection`, `initialize_database`, and `MakerSpaceService`.
- Produces: `main() -> None`.
- Produces: helper functions `prompt_required`, `prompt_int`, `print_rows`, and submenu functions.

- [ ] **Step 1: Create CLI entry point and shared prompt helpers**

Create `main.py` with the connection setup and reusable helpers:

```python
from database import DEFAULT_DB_PATH, get_connection, initialize_database
from services import MakerSpaceService, ServiceError


def prompt_required(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print(f"{label} is required.")


def prompt_optional(label: str) -> str:
    return input(f"{label} (leave blank to keep current): ").strip()


def prompt_int(label: str) -> int:
    while True:
        value = input(f"{label}: ").strip()
        try:
            return int(value)
        except ValueError:
            print("Please enter a valid number.")


def prompt_yes_no(label: str) -> bool:
    while True:
        value = input(f"{label} (y/n): ").strip().lower()
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please enter y or n.")


def print_rows(rows: list[dict]) -> None:
    if not rows:
        print("No records found.")
        return
    for row in rows:
        print(" | ".join(f"{key}: {value}" for key, value in row.items()))
```

- [ ] **Step 2: Add member, equipment, and training menus**

Add these functions to `main.py`:

```python
def manage_members(service: MakerSpaceService) -> None:
    while True:
        print("\nMembers")
        print("1. Register member")
        print("2. List active members")
        print("3. List all members")
        print("4. Update member")
        print("5. Deactivate member")
        print("6. Back")
        choice = input("Choose: ").strip()
        try:
            if choice == "1":
                member_id = service.register_member(
                    prompt_required("Student ID"),
                    prompt_required("Name"),
                    prompt_required("Email"),
                    prompt_required("Phone"),
                )
                print(f"Member created with ID {member_id}.")
            elif choice == "2":
                print_rows(service.list_members())
            elif choice == "3":
                print_rows(service.list_members(include_inactive=True))
            elif choice == "4":
                member_id = prompt_int("Member ID")
                name = prompt_optional("New name")
                email = prompt_optional("New email")
                phone = prompt_optional("New phone")
                service.update_member(
                    member_id,
                    name=name or None,
                    email=email or None,
                    phone=phone or None,
                )
                print("Member updated.")
            elif choice == "5":
                service.update_member(prompt_int("Member ID"), active=False)
                print("Member deactivated.")
            elif choice == "6":
                return
            else:
                print("Invalid choice.")
        except ServiceError as exc:
            print(f"Error: {exc}")


def manage_equipment(service: MakerSpaceService) -> None:
    while True:
        print("\nEquipment")
        print("1. Register equipment")
        print("2. List equipment")
        print("3. Update condition")
        print("4. Update availability")
        print("5. Back")
        choice = input("Choose: ").strip()
        try:
            if choice == "1":
                equipment_id = service.register_equipment(
                    prompt_required("Name"),
                    prompt_required("Category"),
                    prompt_required("Safety level"),
                    prompt_yes_no("Training required"),
                    prompt_required("Condition status"),
                )
                print(f"Equipment created with ID {equipment_id}.")
            elif choice == "2":
                print_rows(service.list_equipment())
            elif choice == "3":
                service.update_equipment(
                    prompt_int("Equipment ID"),
                    condition_status=prompt_required("Condition status"),
                )
                print("Equipment condition updated.")
            elif choice == "4":
                service.update_equipment(
                    prompt_int("Equipment ID"),
                    available=prompt_yes_no("Available"),
                )
                print("Equipment availability updated.")
            elif choice == "5":
                return
            else:
                print("Invalid choice.")
        except ServiceError as exc:
            print(f"Error: {exc}")


def manage_training(service: MakerSpaceService) -> None:
    while True:
        print("\nSafety Training")
        print("1. Add training record")
        print("2. List training records")
        print("3. Back")
        choice = input("Choose: ").strip()
        try:
            if choice == "1":
                training_id = service.add_training(
                    prompt_int("Member ID"),
                    prompt_required("Category"),
                    prompt_required("Completed date YYYY-MM-DD"),
                )
                print(f"Training record created with ID {training_id}.")
            elif choice == "2":
                print_rows(service.list_training_records())
            elif choice == "3":
                return
            else:
                print("Invalid choice.")
        except ServiceError as exc:
            print(f"Error: {exc}")
```

- [ ] **Step 3: Add checkout, return, search, reports, and main loop**

Add these functions to `main.py`:

```python
def checkout_menu(service: MakerSpaceService) -> None:
    try:
        loan_id = service.checkout_equipment(
            prompt_int("Member ID"),
            prompt_int("Equipment ID"),
        )
        print(f"Checkout completed. Loan ID: {loan_id}.")
    except (ServiceError, ValueError) as exc:
        print(f"Error: {exc}")


def return_menu(service: MakerSpaceService) -> None:
    try:
        service.return_equipment(prompt_int("Loan ID"))
        print("Equipment returned.")
    except (ServiceError, ValueError) as exc:
        print(f"Error: {exc}")


def search_menu(service: MakerSpaceService) -> None:
    query = prompt_required("Search query")
    print("\nMembers")
    print_rows(service.search_members(query))
    print("\nEquipment")
    print_rows(service.search_equipment(query))


def reports_menu(service: MakerSpaceService) -> None:
    while True:
        print("\nReports")
        print("1. Currently borrowed equipment")
        print("2. Overdue loans")
        print("3. Safety-restricted equipment")
        print("4. Member training summary")
        print("5. Equipment needing maintenance")
        print("6. Back")
        choice = input("Choose: ").strip()
        try:
            if choice == "1":
                print_rows(service.report_currently_borrowed())
            elif choice == "2":
                print_rows(service.report_overdue_loans())
            elif choice == "3":
                print_rows(service.report_safety_restricted_equipment())
            elif choice == "4":
                print_rows(service.report_member_training_summary())
            elif choice == "5":
                print_rows(service.report_equipment_needing_maintenance())
            elif choice == "6":
                return
            else:
                print("Invalid choice.")
        except ServiceError as exc:
            print(f"Error: {exc}")


def main() -> None:
    conn = get_connection(DEFAULT_DB_PATH)
    initialize_database(conn)
    service = MakerSpaceService(conn)
    print("Safety-Focused Campus MakerSpace Checkout System")

    try:
        while True:
            print("\nMain Menu")
            print("1. Manage members")
            print("2. Manage equipment")
            print("3. Manage safety training")
            print("4. Checkout equipment")
            print("5. Return equipment")
            print("6. Search records")
            print("7. Reports")
            print("8. Seed sample demo data")
            print("9. Exit")
            choice = input("Choose: ").strip()
            if choice == "1":
                manage_members(service)
            elif choice == "2":
                manage_equipment(service)
            elif choice == "3":
                manage_training(service)
            elif choice == "4":
                checkout_menu(service)
            elif choice == "5":
                return_menu(service)
            elif choice == "6":
                search_menu(service)
            elif choice == "7":
                reports_menu(service)
            elif choice == "8":
                service.seed_demo_data()
                print("Sample demo data is ready.")
            elif choice == "9":
                print("Goodbye.")
                return
            else:
                print("Invalid choice.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run automated tests**

Run: `python -m unittest tests.test_services -v`

Expected: PASS.

- [ ] **Step 5: Smoke-test the CLI starts and exits**

Run: `python main.py`

Manual input:

```text
9
```

Expected: The app prints the main menu and exits with `Goodbye.`

- [ ] **Step 6: Commit Task 5**

Run:

```bash
git add main.py
git commit -m "Add interactive CLI menu"
```

## Task 6: README And Final Verification

**Files:**
- Create: `README.md`
- Modify: `tests/test_services.py` only if final verification exposes a real gap.

**Interfaces:**
- Consumes: completed app from Tasks 1-5.
- Produces: complete submission documentation and final verification evidence.

- [ ] **Step 1: Create README**

Create `README.md`:

````markdown
# Lab_MakerSpace_kofiannan06

## Campus MakerSpace Checkout System

This is a safety-focused Python CLI application for managing a campus MakerSpace. It stores members, equipment, category-specific safety training, and equipment loans in SQLite.

The unique feature is safety validation: equipment can require training for a category such as Electronics, 3D Printing, Power Tools, Media, or General Tools. The system blocks checkout when a member has not completed the required category training.

## How To Run

```bash
python main.py
```

The app creates `makerspace.db` automatically on first run.

## How To Run Tests

```bash
python -m unittest tests.test_services -v
```

## Main Features

- Register, list, update, and deactivate members.
- Register, list, and update equipment.
- Track equipment category, safety level, condition, and availability.
- Add category-specific safety training records.
- Checkout equipment with validation.
- Return equipment and update availability.
- Search members and equipment.
- Run SQL-backed reports.
- Seed sample data for live demonstration.

## Object-Oriented Design

- `Member`: represents a MakerSpace member and displays member identity/status.
- `Equipment`: represents an inventory item and checks whether it is available, training-restricted, and loanable.
- `TrainingRecord`: links a member to one approved equipment category.
- `Loan`: represents a checkout transaction and checks active/overdue status.
- `MakerSpaceService`: coordinates database operations and business rules across the model objects.

## SQLite Tables

- `members`: stores student ID, name, contact details, and active status.
- `equipment`: stores inventory details, category, safety level, training requirement, condition, and availability.
- `training_records`: stores which member is trained for which category.
- `loans`: stores checkout date, due date, return date, and loan status.

## Reports

- Currently borrowed equipment.
- Overdue loans.
- Safety-restricted equipment.
- Member training summary.
- Equipment needing maintenance.

## Suggested Live Demo Script

1. Run `python main.py`.
2. Choose `8` to seed sample demo data.
3. List members and equipment.
4. Register a new member who has no training.
5. Try to checkout the `Soldering Kit` or another Electronics item to that untrained member.
6. Show that the system blocks checkout because Electronics training is missing.
7. Add Electronics training for the member.
8. Repeat checkout successfully.
9. Return the equipment.
10. Open reports and show currently borrowed equipment, overdue loans, safety-restricted equipment, member training summary, and equipment needing maintenance.

## Rubric Checklist

- OOP classes are implemented in `models.py`.
- SQLite schema and CRUD workflows are implemented in `database.py` and `services.py`.
- Menu features are implemented in `main.py`.
- Validation prevents unsafe checkout, missing IDs, duplicate student IDs, invalid conditions, and duplicate training records.
- Reports are SQL-backed and available from the CLI.
- Tests verify the main service workflows.

## AI Assistance Disclosure

AI assistance was used to help design the project structure, plan implementation steps, and draft parts of the code and documentation. I reviewed the design and will be responsible for explaining the code, database schema, and live demo behavior.
````

- [ ] **Step 2: Run full automated test suite**

Run: `python -m unittest tests.test_services -v`

Expected: PASS.

- [ ] **Step 3: Run CLI smoke path with sample data**

Run: `python main.py`

Manual input:

```text
8
7
3
6
9
```

Expected:

- Sample data seeding succeeds.
- Reports menu opens.
- Safety-restricted equipment report displays at least `Soldering Kit`.
- App exits cleanly.

- [ ] **Step 4: Check repository status**

Run: `git status --short`

Expected: only intended README changes before commit; no accidental database file committed unless intentionally included.

- [ ] **Step 5: Commit Task 6**

Run:

```bash
git add README.md
git commit -m "Add README and demo instructions"
```

- [ ] **Step 6: Final verification command**

Run:

```bash
python -m unittest tests.test_services -v
```

Expected: PASS.

- [ ] **Step 7: Final status**

Run: `git status --short`

Expected: clean working tree, except `makerspace.db` may appear if created during manual CLI testing. If `makerspace.db` appears, leave it untracked unless the submission specifically needs a sample database file.
