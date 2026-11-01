"""Business logic: availability, pricing, booking flow, invoices and reports.

Nothing in this file touches the screen, so every rule can be tested on its own.
"""
import os
from datetime import date, datetime

# Pricing rules (sample values; change them here to suit the business)
WEEK_DISCOUNT = 0.10          # 7 days or more
MONTH_DISCOUNT = 0.20         # 30 days or more
TAX_RATE = 0.05
LATE_FEE_MULTIPLIER = 1.5     # each extra day is charged at 1.5 x the daily rate

CATEGORIES = ("sedan", "suv", "auto")


class RentalError(Exception):
    """Raised when a rental rule is broken (bad input, wrong status, and so on)."""


class CarNotAvailable(RentalError):
    """Raised when the car is already booked for some of the requested dates."""


# ---------- helpers ----------
def parse_date(text):
    try:
        return datetime.strptime(str(text).strip(), "%Y-%m-%d").date()
    except ValueError:
        raise RentalError("Enter dates as YYYY-MM-DD (for example 2026-11-15).")


def count_days(start, end):
    """Rental days, counting both the first and the last day."""
    if end < start:
        raise RentalError("The return date cannot be before the pickup date.")
    return (end - start).days + 1


def discount_rate(days):
    if days >= 30:
        return MONTH_DISCOUNT
    if days >= 7:
        return WEEK_DISCOUNT
    return 0.0


def calculate_quote(daily_rate, start, end):
    """Price a rental. All money values are rounded to 2 decimals."""
    days = count_days(start, end)
    base = round(daily_rate * days, 2)
    rate = discount_rate(days)
    discount = round(base * rate, 2)
    tax = round((base - discount) * TAX_RATE, 2)
    return {"days": days, "base": base, "discount_rate": rate,
            "discount": discount, "tax": tax, "total": round(base - discount + tax, 2)}


def money(value):
    return f"Rs {value:,.2f}"


# ---------- fleet ----------
def add_car(conn, name, category, seats, fuel, transmission, daily_rate):
    name = name.strip()
    if not name:
        raise RentalError("Car name is required.")
    if category not in CATEGORIES:
        raise RentalError("Category must be sedan, suv or auto.")
    try:
        seats, daily_rate = int(seats), float(daily_rate)
    except ValueError:
        raise RentalError("Seats and daily rate must be numbers.")
    if seats <= 0 or daily_rate <= 0:
        raise RentalError("Seats and daily rate must be greater than zero.")
    cur = conn.execute(
        "INSERT INTO cars (name, category, seats, fuel, transmission, daily_rate) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, category, seats, fuel.strip() or "Petrol", transmission.strip() or "Manual", daily_rate))
    conn.commit()
    return cur.lastrowid


def list_cars(conn, today=None):
    """Active cars, each with a live status: 'On rent' or 'Available'."""
    today = today or date.today()
    rows = conn.execute("SELECT * FROM cars WHERE active = 1 ORDER BY car_id").fetchall()
    on_rent = {r[0] for r in conn.execute(
        "SELECT DISTINCT car_id FROM bookings WHERE status = 'picked_up'")}
    reserved = {r[0] for r in conn.execute(
        "SELECT DISTINCT car_id FROM bookings WHERE status = 'booked' AND start_date <= ? AND end_date >= ?",
        (today.isoformat(), today.isoformat()))}
    out = []
    for r in rows:
        d = dict(r)
        d["status"] = "On rent" if r["car_id"] in on_rent else ("Reserved" if r["car_id"] in reserved else "Available")
        out.append(d)
    return out


def remove_car(conn, car_id):
    open_count = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE car_id = ? AND status IN ('booked', 'picked_up')",
        (car_id,)).fetchone()[0]
    if open_count:
        raise RentalError("This car has open bookings. Return or cancel them first.")
    conn.execute("UPDATE cars SET active = 0 WHERE car_id = ?", (car_id,))
    conn.commit()


# ---------- availability ----------
def is_available(conn, car_id, start, end, exclude_booking_id=None):
    """A car is free if no open booking overlaps the requested dates."""
    row = conn.execute(
        "SELECT COUNT(*) FROM bookings WHERE car_id = ? AND status IN ('booked', 'picked_up') "
        "AND start_date <= ? AND end_date >= ? AND booking_id != ?",
        (car_id, end.isoformat(), start.isoformat(), exclude_booking_id or -1)).fetchone()
    return row[0] == 0


def find_available_cars(conn, start, end):
    count_days(start, end)
    return [c for c in list_cars(conn) if is_available(conn, c["car_id"], start, end)]


# ---------- booking flow ----------
def create_booking(conn, car_id, name, phone, licence, start, end, today=None):
    today = today or date.today()
    name, phone, licence = name.strip(), phone.strip(), licence.strip()
    if not name:
        raise RentalError("Customer name is required.")
    if not (phone.isdigit() and len(phone) == 10):
        raise RentalError("Phone number must be exactly 10 digits.")
    if not licence:
        raise RentalError("Driving licence number is required.")
    if start < today:
        raise RentalError("The pickup date cannot be in the past.")
    car = conn.execute("SELECT * FROM cars WHERE car_id = ? AND active = 1", (car_id,)).fetchone()
    if car is None:
        raise RentalError("Please select a car.")
    quote = calculate_quote(car["daily_rate"], start, end)
    if not is_available(conn, car_id, start, end):
        raise CarNotAvailable(f"{car['name']} is already booked for some of these dates.")

    row = conn.execute("SELECT customer_id FROM customers WHERE phone = ?", (phone,)).fetchone()
    if row:
        customer_id = row[0]
        conn.execute("UPDATE customers SET name = ?, licence_no = ? WHERE customer_id = ?",
                     (name, licence, customer_id))
    else:
        customer_id = conn.execute(
            "INSERT INTO customers (name, phone, licence_no) VALUES (?, ?, ?)",
            (name, phone, licence)).lastrowid
    cur = conn.execute(
        "INSERT INTO bookings (car_id, customer_id, start_date, end_date, base_amount, discount, tax, total, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (car_id, customer_id, start.isoformat(), end.isoformat(), quote["base"], quote["discount"],
         quote["tax"], quote["total"], datetime.now().isoformat(timespec="seconds")))
    conn.commit()
    return cur.lastrowid


def _get_booking(conn, booking_id):
    row = conn.execute(
        "SELECT b.*, c.name AS car_name, c.daily_rate, cu.name AS customer, cu.phone, cu.licence_no "
        "FROM bookings b JOIN cars c ON c.car_id = b.car_id "
        "JOIN customers cu ON cu.customer_id = b.customer_id WHERE b.booking_id = ?",
        (booking_id,)).fetchone()
    if row is None:
        raise RentalError("Booking not found.")
    return row


def pick_up(conn, booking_id):
    b = _get_booking(conn, booking_id)
    if b["status"] != "booked":
        raise RentalError(f"Only a 'booked' booking can be picked up (this one is '{b['status']}').")
    conn.execute("UPDATE bookings SET status = 'picked_up' WHERE booking_id = ?", (booking_id,))
    conn.commit()


def return_car(conn, booking_id, returned_on=None):
    """Close a rental. Days after the agreed return date are charged as a late fine."""
    b = _get_booking(conn, booking_id)
    if b["status"] != "picked_up":
        raise RentalError(f"Only a picked-up car can be returned (this booking is '{b['status']}').")
    returned_on = returned_on or date.today()
    start, end = parse_date(b["start_date"]), parse_date(b["end_date"])
    if returned_on < start:
        raise RentalError("The return date cannot be before the pickup date.")
    late_days = max(0, (returned_on - end).days)
    fine = round(late_days * b["daily_rate"] * LATE_FEE_MULTIPLIER, 2)
    total = round(b["base_amount"] - b["discount"] + b["tax"] + fine, 2)
    conn.execute("UPDATE bookings SET status = 'returned', returned_on = ?, fine = ?, total = ? "
                 "WHERE booking_id = ?", (returned_on.isoformat(), fine, total, booking_id))
    conn.commit()
    return {"late_days": late_days, "fine": fine, "total": total}


def cancel_booking(conn, booking_id):
    b = _get_booking(conn, booking_id)
    if b["status"] != "booked":
        raise RentalError("Only a booking that has not been picked up can be cancelled.")
    conn.execute("UPDATE bookings SET status = 'cancelled' WHERE booking_id = ?", (booking_id,))
    conn.commit()


def list_bookings(conn, status=None):
    sql = ("SELECT b.*, c.name AS car_name, cu.name AS customer, cu.phone "
           "FROM bookings b JOIN cars c ON c.car_id = b.car_id "
           "JOIN customers cu ON cu.customer_id = b.customer_id")
    params = ()
    if status and status != "all":
        sql += " WHERE b.status = ?"
        params = (status,)
    return [dict(r) for r in conn.execute(sql + " ORDER BY b.booking_id DESC", params)]


# ---------- invoice ----------
def generate_invoice(conn, booking_id):
    b = _get_booking(conn, booking_id)
    days = count_days(parse_date(b["start_date"]), parse_date(b["end_date"]))
    line = "-" * 46
    rows = [
        "LUXURY AUTO RENTAL: INVOICE", line,
        f"Invoice no : INV-{b['booking_id']:05d}",
        f"Status     : {b['status']}",
        f"Customer   : {b['customer']} ({b['phone']})",
        f"Licence no : {b['licence_no']}",
        f"Car        : {b['car_name']}",
        f"Period     : {b['start_date']} to {b['end_date']} ({days} day{'s' if days != 1 else ''})",
    ]
    if b["returned_on"]:
        rows.append(f"Returned   : {b['returned_on']}")
    rows += [line,
             f"Rate per day        {money(b['daily_rate']):>24}",
             f"Rental ({days} days)".ljust(20) + f"{money(b['base_amount']):>26}",
             "Discount".ljust(20) + f"{'- ' + money(b['discount']):>26}",
             f"Tax ({TAX_RATE:.0%})".ljust(20) + f"{money(b['tax']):>26}",
             "Late fine".ljust(20) + f"{money(b['fine']):>26}",
             line, "TOTAL".ljust(20) + f"{money(b['total']):>26}", line,
             "Thank you for choosing Luxury Auto Rental."]
    return "\n".join(rows)


def save_invoice(conn, booking_id, folder):
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"INV-{booking_id:05d}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(generate_invoice(conn, booking_id) + "\n")
    return path


# ---------- reports ----------
def monthly_revenue(conn):
    """Money earned per month, counted on the day the car was returned."""
    rows = conn.execute(
        "SELECT substr(returned_on, 1, 7) AS month, ROUND(SUM(total), 2) AS revenue, COUNT(*) AS rentals "
        "FROM bookings WHERE status = 'returned' GROUP BY month ORDER BY month").fetchall()
    return [dict(r) for r in rows]


def car_popularity(conn):
    rows = conn.execute(
        "SELECT c.name, COUNT(b.booking_id) AS bookings FROM cars c "
        "LEFT JOIN bookings b ON b.car_id = c.car_id AND b.status != 'cancelled' "
        "WHERE c.active = 1 GROUP BY c.car_id ORDER BY bookings DESC, c.name").fetchall()
    return [dict(r) for r in rows]


def dashboard_stats(conn, today=None):
    cars = list_cars(conn, today)
    open_b = conn.execute("SELECT COUNT(*) FROM bookings WHERE status IN ('booked', 'picked_up')").fetchone()[0]
    revenue = conn.execute("SELECT COALESCE(SUM(total), 0) FROM bookings WHERE status = 'returned'").fetchone()[0]
    return {"fleet": len(cars),
            "available": sum(1 for c in cars if c["status"] == "Available"),
            "on_rent": sum(1 for c in cars if c["status"] == "On rent"),
            "open_bookings": open_b, "revenue": round(revenue, 2)}
