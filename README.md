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
python -m unittest discover -s tests -p "test*.py" -v
```

## Main Features

- Register, list, update, and deactivate members.
- Require member emails to use `@alustudent.com` or `@alueducation.com`.
- Register, list, and update equipment.
- Track equipment category, safety level, condition, and availability.
- Add category-specific safety training records.
- Checkout equipment with validation.
- Return equipment and update availability.
- Search members and equipment.
- Run SQL-backed reports.
- Seed sample data for live demonstration.
- Export the SQLite database to `exports/makerspace_export.db`.

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
- Email validation rejects non-school email domains.
- Reports are SQL-backed and available from the CLI.
- The database can be exported locally from the main menu.
- Tests verify the main service workflows.

## AI Assistance Disclosure

AI assistance was used to help design the project structure, plan implementation steps, and draft parts of the code and documentation. I reviewed the design and will be responsible for explaining the code, database schema, and live demo behavior.
