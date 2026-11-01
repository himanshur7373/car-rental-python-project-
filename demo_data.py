"""Sample customers and bookings, used for demonstrations (Tools > Load demo data)."""
from datetime import date, timedelta

import service as s

# (car name, customer, phone, licence, start offset, end offset, final state, days returned late)
DEMO = [
    ("Mahindra Thar",      "Rohan Mehta",  "9810000001", "DL01 2019 000101", -80, -77, "returned", 0),
    ("Toyota Fortuner",    "Aman Verma",   "9810000002", "HR26 2018 000202", -62, -56, "returned", 2),
    ("Mercedes A-Class",   "Priya Nair",   "9810000003", "DL03 2020 000303", -45, -44, "returned", 0),
    ("Audi A4",            "Karan Singh",  "9810000004", "UP14 2017 000404", -40, -38, "returned", 0),
    ("Maruti Suzuki Swift", "Neha Kapoor", "9810000005", "HR51 2021 000505", -20, -14, "returned", 0),
    ("Mahindra XUV700",    "Rohan Mehta",  "9810000001", "DL01 2019 000101", -12, -10, "returned", 1),
    ("Kia Seltos",         "Simran Kaur",  "9810000006", "PB10 2019 000606",  -2,   1, "picked_up", 0),
    ("VW Virtus GT",       "Aman Verma",   "9810000002", "HR26 2018 000202",   3,   5, "booked", 0),
    ("Hyundai i20",        "Neha Kapoor",  "9810000005", "HR51 2021 000505",   6,   8, "booked", 0),
    ("Mahindra Scorpio N", "Priya Nair",   "9810000003", "DL03 2020 000303",  10,  12, "cancelled", 0),
]


def load_demo(conn):
    """Add the sample bookings once. Returns False if the database already has bookings."""
    if conn.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]:
        return False
    today = date.today()
    for car, who, phone, lic, a, b, state, late in DEMO:
        car_id = conn.execute("SELECT car_id FROM cars WHERE name = ?", (car,)).fetchone()[0]
        start, end = today + timedelta(days=a), today + timedelta(days=b)
        # 'today' is set to the start date so that old rentals pass the past-date check
        booking = s.create_booking(conn, car_id, who, phone, lic, start, end, today=start)
        if state in ("picked_up", "returned"):
            s.pick_up(conn, booking)
        if state == "returned":
            s.return_car(conn, booking, end + timedelta(days=late))
        if state == "cancelled":
            s.cancel_booking(conn, booking)
    return True
