# Technical and Architectural Design

## Project Overview

`Lab_MakerSpace_kofiannan06` is a command-line Python application for managing a campus MakerSpace checkout process. The system supports members, equipment inventory, safety training, loans, maintenance audit notes, reports, and local database export.

The application was designed for the Introduction to Programming and Databases summative assessment. Its main technical goal is to demonstrate object-oriented programming, SQLite database persistence, validation, CRUD-style workflows, and SQL-backed reporting in a small but realistic software system.

## Problem Domain

A campus MakerSpace lends equipment such as soldering kits, 3D printer accessories, cameras, drills, and general tools. Some equipment can be unsafe if used by untrained members. The system therefore needs to do more than record loans: it must also check safety requirements before checkout.

The project models this domain with these core ideas:

- Members can register and borrow equipment.
- Equipment belongs to a category and can require category-specific training.
- Training records prove that a member is approved for a category.
- Loans record checkout and return activity.
- Condition audit notes explain maintenance or safety concerns.
- Reports help operators inspect current activity and risk.

## High-Level Architecture

The system uses a layered architecture:

```text
main.py
  CLI menus and user input/output

services.py
  Business logic, validation, workflows, reports

models.py
  Object-oriented domain classes

database.py
  SQLite connection and schema creation

makerspace.db
  Persistent SQLite database file
```

This separation keeps the menu code simple. `main.py` does not directly implement checkout rules or SQL reports. Instead, it sends user requests to `MakerSpaceService` in `services.py`, which coordinates validation and database operations.

## File Responsibilities

### `main.py`

`main.py` is the application entry point. It contains:

- The main menu loop.
- Submenus for members, equipment, training, checkout, returns, search, reports, seed data, and export.
- Input helper functions such as `prompt_required`, `prompt_int`, and `prompt_yes_no`.
- Display helper `print_rows`.

Its responsibility is user interaction, not business rules.

### `models.py`

`models.py` defines the object-oriented domain model:

- `Member`
- `Equipment`
- `TrainingRecord`
- `Loan`

These classes represent real objects in the MakerSpace domain. They include small behavior methods such as:

- `Equipment.requires_training()`
- `Equipment.can_be_loaned()`
- `Loan.is_active()`
- `Loan.is_overdue()`

### `database.py`

`database.py` handles SQLite setup:

- Defines the default database path: `makerspace.db`
- Opens SQLite connections with `row_factory = sqlite3.Row`
- Enables foreign key checks with `PRAGMA foreign_keys = ON`
- Creates all required tables if they do not already exist

This allows the application to create its database automatically on first run.

### `services.py`

`services.py` contains the main application logic through `MakerSpaceService`.

Responsibilities include:

- Registering and updating members.
- Validating school email domains.
- Registering and updating equipment.
- Adding category-specific safety training.
- Creating and returning loans.
- Blocking invalid or unsafe checkout attempts.
- Searching members and equipment.
- Producing SQL-backed reports.
- Adding and listing condition audit notes.
- Exporting the SQLite database file.

This service layer is the main coordination point between the CLI, the database, and the domain model.

### `tests/`

The test suite uses Python's built-in `unittest` framework. Tests cover:

- Schema creation.
- Domain model behavior.
- Member, equipment, and training workflows.
- Checkout and return validation.
- Search and reports.
- Demo data seeding.
- Email domain validation.
- Database export.
- Equipment condition audit notes.
- CLI startup/exit smoke behavior.

## Object-Oriented Design

The object-oriented design is based on domain entities.

### `Member`

Represents a registered MakerSpace user.

Important fields:

- `member_id`
- `student_id`
- `name`
- `email`
- `phone`
- `active`

The `active` field allows the system to block inactive members from borrowing equipment.

### `Equipment`

Represents a borrowable item in the MakerSpace.

Important fields:

- `equipment_id`
- `name`
- `category`
- `safety_level`
- `training_required`
- `condition_status`
- `available`

Important behavior:

- `requires_training()` checks if the item needs safety approval.
- `can_be_loaned()` checks if it is available and in good condition.

### `TrainingRecord`

Represents a member's approval for one equipment category.

Example:

```text
Member: Amina Doe
Category: Electronics
Completed date: 2026-09-21
```

This design is stronger than a single yes/no training field because a member can be trained for Electronics but not Power Tools.

### `Loan`

Represents a checkout transaction.

Important fields:

- `loan_id`
- `member_id`
- `equipment_id`
- `checkout_date`
- `due_date`
- `return_date`
- `status`

Important behavior:

- `is_active()` checks if the loan is still open.
- `is_overdue()` compares the due date with the current date or a supplied test date.
- `mark_returned()` updates the loan object state.

## Database Design

The database uses SQLite and is normalized around the main domain entities.

### `members`

Stores registered users.

Key columns:

- `member_id` primary key
- `student_id` unique student or staff identifier
- `name`
- `email`
- `phone`
- `active`

Email is validated in the service layer. Accepted domains are:

- `@alustudent.com`
- `@alueducation.com`

### `equipment`

Stores inventory items.

Key columns:

- `equipment_id` primary key
- `name`
- `category`
- `safety_level`
- `training_required`
- `condition_status`
- `available`

Condition statuses include:

- `Good`
- `Needs Maintenance`
- `Retired`

### `training_records`

Stores category-specific safety approvals.

Key columns:

- `training_id` primary key
- `member_id` foreign key
- `category`
- `completed_date`

The table has a unique constraint on `(member_id, category)` so the same member cannot receive duplicate training records for the same category.

### `loans`

Stores checkout and return history.

Key columns:

- `loan_id` primary key
- `member_id` foreign key
- `equipment_id` foreign key
- `checkout_date`
- `due_date`
- `return_date`
- `status`

Active loans are records where `status = 'Active'` and `return_date` is empty.

### `condition_notes`

Stores maintenance and safety audit notes for equipment.

Key columns:

- `note_id` primary key
- `equipment_id` foreign key
- `note`
- `logged_by`
- `logged_date`

This table gives the project a realistic safety-audit trail. For example, a drill can be marked as needing maintenance and also have a note explaining that the battery overheats after 10 minutes.

## Key Workflows

### Member Registration

1. User selects member registration from the CLI.
2. `main.py` collects student ID, name, email, and phone.
3. `MakerSpaceService.register_member()` validates required fields.
4. The service checks that the email ends in `@alustudent.com` or `@alueducation.com`.
5. The service inserts the member into SQLite.

### Equipment Checkout

1. User enters member ID and equipment ID.
2. `MakerSpaceService.checkout_equipment()` loads the member and equipment.
3. The service validates:
   - Member exists.
   - Equipment exists.
   - Member is active.
   - Equipment is available.
   - Equipment condition is `Good`.
   - If training is required, the member has training for that equipment category.
4. If validation passes, the service creates a loan.
5. The service marks the equipment as unavailable.

This workflow is central to the safety-focused design.

### Equipment Return

1. User enters the loan ID.
2. The service checks that the loan exists and is still active.
3. The loan is updated with a return date and `Returned` status.
4. The equipment is marked available again.

### Condition Audit Note

1. User selects equipment condition audit notes from the equipment menu.
2. User enters equipment ID, note text, person logging the note, and date.
3. The service validates the equipment ID, note, author, and date.
4. The note is saved in the `condition_notes` table.
5. The note can later be viewed as part of the maintenance/safety record.

### Database Export

1. User selects `Export database`.
2. The service copies `makerspace.db` to `exports/makerspace_export.db`.
3. The exported file can be moved, downloaded, backed up, or inspected locally with an SQLite viewer.

## Validation and Error Handling

The application uses a custom `ServiceError` exception for user-facing validation problems.

Validation examples:

- Blank required fields are rejected.
- Duplicate student IDs are rejected.
- Non-school email domains are rejected.
- Invalid dates are rejected unless they use `YYYY-MM-DD`.
- Missing members, equipment, and loans are rejected.
- Unavailable equipment cannot be checked out.
- Equipment needing maintenance or retired equipment cannot be checked out.
- Training-required equipment cannot be borrowed without matching category training.
- Returned loans cannot be returned again.

The CLI catches `ServiceError` and prints clear messages instead of crashing.

## Reports

The reports are SQL-backed and use joins where needed.

Implemented reports include:

- Currently borrowed equipment.
- Overdue loans.
- Safety-restricted equipment.
- Member training summary.
- Equipment needing maintenance.
- Equipment condition audit notes through the equipment menu.

Reports demonstrate that the system can query persisted data, not just store it.

## Testing Strategy

The project uses automated tests to verify the main behavior.

Test categories:

- Schema tests confirm database tables and foreign keys.
- Model tests confirm object behavior.
- Service tests confirm CRUD-style workflows and validation.
- Checkout tests confirm safety rules.
- Report tests confirm SQL queries return expected data.
- Export tests confirm the database can be copied locally.
- Audit note tests confirm maintenance notes are stored and validated.
- CLI smoke test confirms the menu can start and exit cleanly.

Run tests with:

```bash
python -m unittest discover -s tests -p "test*.py" -v
```

## Design Strengths

- Clear separation between CLI, business logic, models, and database setup.
- SQLite persistence allows data to remain between runs.
- Category-based training is more realistic than a single training flag.
- Condition audit notes give the safety system a practical maintenance record.
- Reports demonstrate meaningful SQL usage.
- The database export feature supports backup or local inspection.
- Tests cover core behavior and edge cases.

## Known Limitations

- The application is a CLI, not a graphical interface.
- User authentication is not implemented.
- The system does not track multiple campuses or departments.
- Audit notes can be added and listed, but not edited or deleted.
- Export creates a database copy, but does not generate CSV or PDF reports.

These limitations are acceptable for the assignment scope because the project focuses on OOP, SQLite, validation, and a working menu-driven application.

## Live Demonstration Summary

A strong live demonstration should show:

1. Seed sample data.
2. List members and equipment.
3. Show category-specific training records.
4. Attempt unsafe checkout without required training.
5. Add training and repeat checkout successfully.
6. Return the equipment.
7. Add a condition audit note for maintenance equipment.
8. Show reports.
9. Export the database.
10. Explain the class structure and SQLite tables.

This demonstrates the full architecture: object-oriented design, persistent database storage, validation, reporting, and safety-focused business rules.
