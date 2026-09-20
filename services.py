import sqlite3
from datetime import date


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
