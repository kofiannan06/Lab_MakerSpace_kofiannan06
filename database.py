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

        CREATE TABLE IF NOT EXISTS condition_notes (
            note_id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER NOT NULL,
            note TEXT NOT NULL,
            logged_by TEXT NOT NULL,
            logged_date TEXT NOT NULL,
            FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
        );
        """
    )
    conn.commit()


def dict_from_row(row: sqlite3.Row) -> dict:
    return dict(row)
