# Safety-Focused MakerSpace Checkout System Design

## Purpose

Build an individual Object-Oriented Python CLI application for the Campus MakerSpace Checkout System assessment. The application will manage members, equipment, safety training, and loans using SQLite for persistent storage.

The project will follow the assessment rubric closely while adding a distinctive safety-focused workflow: equipment can require category-specific training, and checkout is blocked when a member is not approved for the equipment category.

## Success Criteria

- The application runs from `main.py` as a menu-driven CLI.
- Data persists in an SQLite database file between runs.
- The code uses meaningful OOP classes with clear attributes and behavior.
- Members, equipment, training records, and loans can be managed through menu features.
- Checkout validation prevents unsafe or invalid loans.
- At least two SQL reports are implemented; the project will include more than two for stronger demonstration evidence.
- The README explains setup, class design, database tables, demo flow, and AI assistance disclosure.

## Project Structure

```text
main.py
models.py
database.py
services.py
README.md
requirements.txt
tests/
  test_services.py
```

### `main.py`

Contains the menu loop, input prompts, and display formatting. It delegates real business logic to `MakerSpaceService` instead of directly manipulating the database.

### `models.py`

Defines the domain objects:

- `Member`
- `Equipment`
- `Loan`
- `TrainingRecord`

These classes hold domain data and include small behavior methods such as `is_active()`, `is_overdue()`, `requires_training()`, and `can_be_loaned()`.

### `database.py`

Owns SQLite connection setup, schema creation, and low-level SQL helpers. It enables foreign keys and creates the database tables on first run.

### `services.py`

Defines `MakerSpaceService`, which coordinates workflows across models and database operations. This is where checkout, return, validation, search, reports, and sample-data seeding live.

### `tests/test_services.py`

Uses Python's built-in `unittest` module to verify the core workflows without needing external dependencies.

## Domain Model

### `Member`

Represents a MakerSpace member.

Attributes:

- `member_id`
- `student_id`
- `name`
- `email`
- `phone`
- `active`

Main behavior:

- Display member details clearly.
- Identify inactive members so they cannot borrow equipment.

### `Equipment`

Represents a borrowable MakerSpace item.

Attributes:

- `equipment_id`
- `name`
- `category`
- `safety_level`
- `training_required`
- `condition_status`
- `available`

Main behavior:

- `is_available()`
- `requires_training()`
- `can_be_loaned()`

Equipment cannot be loaned if it is unavailable, retired, or marked as needing maintenance.

### `TrainingRecord`

Represents a member's approval for one equipment category.

Attributes:

- `training_id`
- `member_id`
- `category`
- `completed_date`

Main behavior:

- Confirm whether a member has category-specific approval.

### `Loan`

Represents a checkout transaction.

Attributes:

- `loan_id`
- `member_id`
- `equipment_id`
- `checkout_date`
- `due_date`
- `return_date`
- `status`

Main behavior:

- `is_active()`
- `is_overdue()`
- Mark a loan as returned.

### `MakerSpaceService`

Coordinates the application workflows.

Responsibilities:

- Register, list, update, and deactivate members.
- Register, list, update, and retire equipment.
- Add and list training records.
- Create checkout loans after validation.
- Return equipment and close active loans.
- Search members and equipment.
- Produce SQL-backed reports.
- Seed sample data for the live demo.

## Database Design

The SQLite schema will use four main tables.

### `members`

Stores registered members.

Columns:

- `member_id INTEGER PRIMARY KEY AUTOINCREMENT`
- `student_id TEXT NOT NULL UNIQUE`
- `name TEXT NOT NULL`
- `email TEXT`
- `phone TEXT`
- `active INTEGER NOT NULL DEFAULT 1`

### `equipment`

Stores MakerSpace inventory.

Columns:

- `equipment_id INTEGER PRIMARY KEY AUTOINCREMENT`
- `name TEXT NOT NULL`
- `category TEXT NOT NULL`
- `safety_level TEXT NOT NULL`
- `training_required INTEGER NOT NULL DEFAULT 0`
- `condition_status TEXT NOT NULL DEFAULT 'Good'`
- `available INTEGER NOT NULL DEFAULT 1`

Expected categories:

- `3D Printing`
- `Electronics`
- `Power Tools`
- `Media`
- `General Tools`

Expected condition statuses:

- `Good`
- `Needs Maintenance`
- `Retired`

### `training_records`

Stores category-specific safety training approvals.

Columns:

- `training_id INTEGER PRIMARY KEY AUTOINCREMENT`
- `member_id INTEGER NOT NULL`
- `category TEXT NOT NULL`
- `completed_date TEXT NOT NULL`
- `FOREIGN KEY (member_id) REFERENCES members(member_id)`
- `UNIQUE(member_id, category)`

### `loans`

Stores checkout and return history.

Columns:

- `loan_id INTEGER PRIMARY KEY AUTOINCREMENT`
- `member_id INTEGER NOT NULL`
- `equipment_id INTEGER NOT NULL`
- `checkout_date TEXT NOT NULL`
- `due_date TEXT NOT NULL`
- `return_date TEXT`
- `status TEXT NOT NULL DEFAULT 'Active'`
- `FOREIGN KEY (member_id) REFERENCES members(member_id)`
- `FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)`

## Menu Design

Main menu:

1. Manage members
2. Manage equipment
3. Manage safety training
4. Checkout equipment
5. Return equipment
6. Search records
7. Reports
8. Seed sample demo data
9. Exit

Member menu:

- Register member
- List members
- Update member
- Deactivate member

Equipment menu:

- Register equipment
- List equipment
- Update equipment
- Mark equipment for maintenance or retirement

Training menu:

- Add training record
- List training records
- Show training by member

Reports menu:

- Currently borrowed equipment
- Overdue loans
- Safety-restricted equipment
- Member training summary
- Equipment needing maintenance

## Validation Rules

The application will show clear messages and avoid crashes for invalid input.

Validation includes:

- Reject blank required fields.
- Reject duplicate student IDs.
- Reject invalid menu choices.
- Reject invalid IDs for members, equipment, and loans.
- Reject checkout for inactive members.
- Reject checkout for unavailable equipment.
- Reject checkout for equipment needing maintenance or retired equipment.
- Reject checkout when category training is required but missing.
- Reject returning a loan that is already closed.
- Reject invalid date formats.

## Reports

The project will include at least five SQL-backed reports:

1. Currently borrowed equipment.
2. Overdue active loans.
3. Safety-restricted equipment.
4. Member training summary.
5. Equipment needing maintenance.

This exceeds the minimum requirement of two meaningful SQL reports and gives a strong live-demonstration path.

## Live Demo Flow

The README will include a suggested demo:

1. Run the application.
2. Seed sample demo data.
3. List members and equipment.
4. Try to checkout a training-required electronics item to a member without electronics training.
5. Show the validation message blocking unsafe checkout.
6. Add electronics training for the member.
7. Repeat checkout successfully.
8. Return the equipment.
9. Run reports.
10. Explain the classes, SQLite tables, and safety validation logic.

## Testing Strategy

Tests will use `unittest` and a temporary SQLite database.

Core tests:

- Schema creation succeeds.
- Member and equipment records can be created and read.
- Checkout is blocked without required training.
- Checkout succeeds after category training is added.
- Return closes the loan and makes equipment available.
- Report queries return expected rows.

## Assessment Mapping

### Object-Oriented Programming Design

The project uses meaningful domain classes and a service layer. Behavior is kept in model methods and coordinated through `MakerSpaceService`, avoiding one large procedural script.

### Database Design and Use

SQLite stores members, equipment, loans, and category-specific training records. The schema uses primary keys, foreign keys, unique constraints, CRUD operations, and multiple SQL reports.

### Application Features and Execution

The CLI covers member management, equipment management, safety training, checkout, return, search, reports, and sample-data seeding.

### Error Handling and Validation

The application validates user input and unsafe actions, especially missing training, unavailable equipment, maintenance status, invalid IDs, and duplicate records.

### Live Demonstration

The safety-focused demo gives a clear story: unsafe checkout is blocked, training is added, checkout succeeds, return is completed, and reports show the result.

### Submission Instructions

The repository will include source files, README, tests, and a minimal `requirements.txt`. The README will also include an AI assistance disclosure.
