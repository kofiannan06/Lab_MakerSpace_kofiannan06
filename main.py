from database import DEFAULT_DB_PATH, get_connection, initialize_database
from services import MakerSpaceService, ServiceError


EXPORT_PATH = "exports/makerspace_export.db"


# Input helpers keep the menu functions short and prevent repeated parsing code.
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
    """Display database rows in a simple CLI-friendly format."""
    if not rows:
        print("No records found.")
        return
    for row in rows:
        print(" | ".join(f"{key}: {value}" for key, value in row.items()))


def manage_members(service: MakerSpaceService) -> None:
    """Menu for registering, listing, updating, and deactivating members."""
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
    """Menu for equipment inventory, availability, and safety audit notes."""
    while True:
        print("\nEquipment")
        print("1. Register equipment")
        print("2. List equipment")
        print("3. Update condition")
        print("4. Update availability")
        print("5. Add condition audit note")
        print("6. View condition audit notes")
        print("7. Back")
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
                note_id = service.add_condition_note(
                    prompt_int("Equipment ID"),
                    prompt_required("Audit note"),
                    prompt_required("Logged by"),
                    prompt_required("Logged date YYYY-MM-DD"),
                )
                print(f"Condition audit note created with ID {note_id}.")
            elif choice == "6":
                equipment_id_text = prompt_optional("Equipment ID")
                equipment_id = int(equipment_id_text) if equipment_id_text else None
                print_rows(service.list_condition_notes(equipment_id))
            elif choice == "7":
                return
            else:
                print("Invalid choice.")
        except (ServiceError, ValueError) as exc:
            print(f"Error: {exc}")


def manage_training(service: MakerSpaceService) -> None:
    """Menu for category-specific training records."""
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


def checkout_menu(service: MakerSpaceService) -> None:
    """Run the equipment checkout workflow through the service layer."""
    try:
        loan_id = service.checkout_equipment(
            prompt_int("Member ID"),
            prompt_int("Equipment ID"),
        )
        print(f"Checkout completed. Loan ID: {loan_id}.")
    except (ServiceError, ValueError) as exc:
        print(f"Error: {exc}")


def return_menu(service: MakerSpaceService) -> None:
    """Close an active loan and make the equipment available again."""
    try:
        service.return_equipment(prompt_int("Loan ID"))
        print("Equipment returned.")
    except (ServiceError, ValueError) as exc:
        print(f"Error: {exc}")


def search_menu(service: MakerSpaceService) -> None:
    """Search both member and equipment records from one menu option."""
    query = prompt_required("Search query")
    print("\nMembers")
    print_rows(service.search_members(query))
    print("\nEquipment")
    print_rows(service.search_equipment(query))


def reports_menu(service: MakerSpaceService) -> None:
    """Menu for SQL-backed operational reports."""
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


def export_database_menu(service: MakerSpaceService) -> None:
    """Export the SQLite database to a local backup file."""
    try:
        exported_path = service.export_database(DEFAULT_DB_PATH, EXPORT_PATH)
        print(f"Database exported to {exported_path}.")
    except ServiceError as exc:
        print(f"Error: {exc}")


def main() -> None:
    """Start the CLI application and initialize the database."""
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
            print("9. Export database")
            print("10. Exit")
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
                export_database_menu(service)
            elif choice == "10":
                print("Goodbye.")
                return
            else:
                print("Invalid choice.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
