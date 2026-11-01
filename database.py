"""Database layer: SQLite connection, schema and sample fleet."""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "car_rental.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS cars (
    car_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT    NOT NULL,
    category     TEXT    NOT NULL CHECK (category IN ('sedan', 'suv', 'auto')),
    seats        INTEGER NOT NULL CHECK (seats > 0),
    fuel         TEXT    NOT NULL,
    transmission TEXT    NOT NULL,
    daily_rate   REAL    NOT NULL CHECK (daily_rate > 0),
    active       INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    phone       TEXT NOT NULL UNIQUE,
    licence_no  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    booking_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    car_id       INTEGER NOT NULL REFERENCES cars(car_id),
    customer_id  INTEGER NOT NULL REFERENCES customers(customer_id),
    start_date   TEXT    NOT NULL,
    end_date     TEXT    NOT NULL,
    returned_on  TEXT,
    status       TEXT    NOT NULL DEFAULT 'booked'
                 CHECK (status IN ('booked', 'picked_up', 'returned', 'cancelled')),
    base_amount  REAL    NOT NULL,
    discount     REAL    NOT NULL DEFAULT 0,
    tax          REAL    NOT NULL DEFAULT 0,
    fine         REAL    NOT NULL DEFAULT 0,
    total        REAL    NOT NULL,
    created_at   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_bookings_car ON bookings(car_id, start_date, end_date);
"""

# (name, category, seats, fuel, transmission, daily_rate): sample rates for demonstration
SAMPLE_FLEET = [
    ("Mercedes A-Class", "sedan", 5, "Petrol", "Automatic", 9000),
    ("Audi A4", "sedan", 5, "Petrol", "Manual", 8000),
    ("VW Virtus GT", "sedan", 5, "Petrol", "Manual", 3500),
    ("Hyundai i20", "sedan", 5, "Petrol", "Manual", 2200),
    ("Maruti Suzuki Swift", "sedan", 5, "Petrol", "Manual", 1800),
    ("Mahindra Thar", "suv", 4, "Diesel", "Manual", 4500),
    ("Toyota Fortuner", "suv", 7, "Diesel", "Automatic", 7000),
    ("Mahindra XUV700", "suv", 7, "Diesel", "Automatic", 5500),
    ("Mahindra Scorpio N", "suv", 7, "Diesel", "Automatic", 5000),
    ("Kia Seltos", "auto", 5, "Diesel", "Automatic", 4000),
]


def get_connection(path=DB_PATH):
    """Open a connection with rows accessible by column name and foreign keys on."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    """Create the tables and load the sample fleet if the database is new."""
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM cars").fetchone()[0] == 0:
        conn.executemany(
            "INSERT INTO cars (name, category, seats, fuel, transmission, daily_rate) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            SAMPLE_FLEET,
        )
    conn.commit()
