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
