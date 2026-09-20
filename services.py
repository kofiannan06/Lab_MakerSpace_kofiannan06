import shutil
import sqlite3
from datetime import date, timedelta
from pathlib import Path


VALID_CONDITIONS = {"Good", "Needs Maintenance", "Retired"}
ALLOWED_EMAIL_DOMAINS = ("@alustudent.com", "@alueducation.com")


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

    def _require_school_email(self, value: str) -> str:
        cleaned = value.strip().lower()
        if not cleaned.endswith(ALLOWED_EMAIL_DOMAINS):
            raise ServiceError("Email must be a school email ending in @alustudent.com or @alueducation.com.")
        return cleaned

    def register_member(self, student_id: str, name: str, email: str, phone: str) -> int:
        student_id = self._require_text(student_id, "Student ID")
        name = self._require_text(name, "Member name")
        email = self._require_school_email(email)
        try:
            cursor = self.conn.execute(
                "INSERT INTO members (student_id, name, email, phone) VALUES (?, ?, ?, ?)",
                (student_id, name, email, phone.strip()),
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
            "email": self._require_school_email(email) if email is not None else member["email"],
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
            raise ServiceError(
                f"{equipment['name']} cannot be loaned because its condition is {equipment['condition_status']}."
            )
        if equipment["training_required"] and not self.member_has_training(member_id, equipment["category"]):
            raise ServiceError(f"{member['name']} needs training for {equipment['category']} before checkout.")

        checkout = date.fromisoformat(self._require_date(checkout_date, "Checkout date")) if checkout_date else date.today()
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

        returned = date.fromisoformat(self._require_date(return_date, "Return date")).isoformat() if return_date else date.today().isoformat()
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

    def export_database(self, source_path: str | Path, export_path: str | Path) -> Path:
        source = Path(source_path)
        destination = Path(export_path)
        if not source.exists():
            raise ServiceError(f"Database file {source} was not found.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination

    def add_condition_note(
        self,
        equipment_id: int,
        note: str,
        logged_by: str,
        logged_date: str,
    ) -> int:
        self._get_equipment(equipment_id)
        note = self._require_text(note, "Audit note")
        logged_by = self._require_text(logged_by, "Logged by")
        logged_date = self._require_date(logged_date, "Logged date")
        cursor = self.conn.execute(
            """
            INSERT INTO condition_notes (equipment_id, note, logged_by, logged_date)
            VALUES (?, ?, ?, ?)
            """,
            (equipment_id, note, logged_by, logged_date),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_condition_notes(self, equipment_id: int | None = None) -> list[dict]:
        if equipment_id is not None:
            self._get_equipment(equipment_id)
            rows = self.conn.execute(
                """
                SELECT cn.note_id,
                       cn.equipment_id,
                       e.name AS equipment_name,
                       e.condition_status,
                       cn.note,
                       cn.logged_by,
                       cn.logged_date
                FROM condition_notes cn
                JOIN equipment e ON e.equipment_id = cn.equipment_id
                WHERE cn.equipment_id = ?
                ORDER BY cn.logged_date DESC, cn.note_id DESC
                """,
                (equipment_id,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """
                SELECT cn.note_id,
                       cn.equipment_id,
                       e.name AS equipment_name,
                       e.condition_status,
                       cn.note,
                       cn.logged_by,
                       cn.logged_date
                FROM condition_notes cn
                JOIN equipment e ON e.equipment_id = cn.equipment_id
                ORDER BY cn.logged_date DESC, cn.note_id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def seed_demo_data(self) -> None:
        members = [
            ("STU001", "Amina Doe", "amina@alustudent.com", "555-0101"),
            ("STU002", "Kofi Mensah", "kofi@alustudent.com", "555-0102"),
            ("STU003", "Lina Patel", "lina@alustudent.com", "555-0103"),
        ]
        for student_id, name, email, phone in members:
            if not self.conn.execute("SELECT 1 FROM members WHERE student_id = ?", (student_id,)).fetchone():
                self.register_member(student_id, name, email, phone)
            else:
                self.conn.execute(
                    "UPDATE members SET email = ?, phone = ? WHERE student_id = ?",
                    (email, phone, student_id),
                )
                self.conn.commit()

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

    def _get_loan(self, loan_id: int) -> dict:
        row = self.conn.execute("SELECT * FROM loans WHERE loan_id = ?", (loan_id,)).fetchone()
        if row is None:
            raise ServiceError(f"Loan ID {loan_id} was not found.")
        return dict(row)
