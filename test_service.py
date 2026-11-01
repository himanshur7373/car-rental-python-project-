"""Unit tests for the rental rules. Run with:  python -m unittest -v"""
import os
import tempfile
import unittest
from datetime import date

import database
import service as s

D = date  # short alias


class RentalTests(unittest.TestCase):
    def setUp(self):
        self.conn = database.get_connection(":memory:")
        database.init_db(self.conn)
        self.today = D(2026, 11, 1)
        self.thar = self.conn.execute("SELECT car_id FROM cars WHERE name = 'Mahindra Thar'").fetchone()[0]

    def book(self, start, end, car=None, phone="9050737373"):
        return s.create_booking(self.conn, car or self.thar, "Himanshu Rathee", phone, "HR00 0000000",
                                start, end, today=self.today)

    # ---- pricing ----
    def test_days_counts_both_ends(self):
        self.assertEqual(s.count_days(D(2026, 11, 5), D(2026, 11, 5)), 1)
        self.assertEqual(s.count_days(D(2026, 11, 5), D(2026, 11, 7)), 3)

    def test_end_before_start_is_rejected(self):
        with self.assertRaises(s.RentalError):
            s.count_days(D(2026, 11, 7), D(2026, 11, 5))

    def test_discount_tiers(self):
        self.assertEqual(s.discount_rate(6), 0)
        self.assertEqual(s.discount_rate(7), 0.10)
        self.assertEqual(s.discount_rate(29), 0.10)
        self.assertEqual(s.discount_rate(30), 0.20)

    def test_quote_for_two_days(self):
        q = s.calculate_quote(4500, D(2026, 11, 5), D(2026, 11, 6))
        self.assertEqual((q["base"], q["discount"], q["tax"], q["total"]), (9000, 0, 450, 9450))

    def test_quote_with_week_discount(self):
        q = s.calculate_quote(1000, D(2026, 11, 1), D(2026, 11, 7))   # 7 days
        self.assertEqual((q["base"], q["discount"], q["tax"], q["total"]), (7000, 700, 315, 6615))

    # ---- availability ----
    def test_overlapping_dates_are_blocked(self):
        self.book(D(2026, 11, 10), D(2026, 11, 12))
        with self.assertRaises(s.CarNotAvailable):
            self.book(D(2026, 11, 12), D(2026, 11, 14), phone="9999999999")

    def test_back_to_back_dates_are_allowed(self):
        self.book(D(2026, 11, 10), D(2026, 11, 12))
        self.book(D(2026, 11, 13), D(2026, 11, 14), phone="9999999999")

    def test_cancelled_booking_frees_the_car(self):
        b = self.book(D(2026, 11, 10), D(2026, 11, 12))
        s.cancel_booking(self.conn, b)
        self.book(D(2026, 11, 10), D(2026, 11, 12), phone="9999999999")

    def test_find_available_cars_excludes_booked_car(self):
        self.book(D(2026, 11, 10), D(2026, 11, 12))
        names = [c["name"] for c in s.find_available_cars(self.conn, D(2026, 11, 11), D(2026, 11, 11))]
        self.assertNotIn("Mahindra Thar", names)
        self.assertIn("Audi A4", names)

    # ---- validation ----
    def test_past_pickup_date_is_rejected(self):
        with self.assertRaises(s.RentalError):
            self.book(D(2026, 10, 30), D(2026, 11, 2))

    def test_bad_phone_is_rejected(self):
        with self.assertRaises(s.RentalError):
            self.book(D(2026, 11, 10), D(2026, 11, 11), phone="12345")

    def test_bad_date_text_is_rejected(self):
        with self.assertRaises(s.RentalError):
            s.parse_date("15/11/2026")

    def test_same_phone_reuses_customer(self):
        self.book(D(2026, 11, 10), D(2026, 11, 11))
        self.book(D(2026, 11, 20), D(2026, 11, 21))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0], 1)

    # ---- status flow ----
    def test_full_flow_on_time(self):
        b = self.book(D(2026, 11, 10), D(2026, 11, 12))
        s.pick_up(self.conn, b)
        r = s.return_car(self.conn, b, D(2026, 11, 12))
        self.assertEqual(r["late_days"], 0)
        self.assertEqual(r["fine"], 0)
        self.assertEqual(r["total"], 14175)          # 3 days x 4500 = 13500 + 5% tax

    def test_late_return_adds_fine(self):
        b = self.book(D(2026, 11, 10), D(2026, 11, 12))
        s.pick_up(self.conn, b)
        r = s.return_car(self.conn, b, D(2026, 11, 14))     # 2 days late
        self.assertEqual(r["late_days"], 2)
        self.assertEqual(r["fine"], 13500)           # 2 x 4500 x 1.5
        self.assertEqual(r["total"], 14175 + 13500)

    def test_cannot_return_before_pickup(self):
        b = self.book(D(2026, 11, 10), D(2026, 11, 12))
        with self.assertRaises(s.RentalError):
            s.return_car(self.conn, b, D(2026, 11, 12))

    def test_cannot_cancel_after_pickup(self):
        b = self.book(D(2026, 11, 10), D(2026, 11, 12))
        s.pick_up(self.conn, b)
        with self.assertRaises(s.RentalError):
            s.cancel_booking(self.conn, b)

    def test_car_status_changes_to_on_rent(self):
        b = self.book(D(2026, 11, 1), D(2026, 11, 3))
        s.pick_up(self.conn, b)
        status = {c["name"]: c["status"] for c in s.list_cars(self.conn, self.today)}
        self.assertEqual(status["Mahindra Thar"], "On rent")

    def test_cannot_remove_car_with_open_booking(self):
        self.book(D(2026, 11, 10), D(2026, 11, 12))
        with self.assertRaises(s.RentalError):
            s.remove_car(self.conn, self.thar)

    # ---- fleet, invoice, reports ----
    def test_add_car_validates_input(self):
        with self.assertRaises(s.RentalError):
            s.add_car(self.conn, "Test", "bike", 2, "Petrol", "Manual", 500)
        with self.assertRaises(s.RentalError):
            s.add_car(self.conn, "Test", "sedan", 5, "Petrol", "Manual", -10)
        new_id = s.add_car(self.conn, "Hyundai Creta", "suv", 5, "Diesel", "Automatic", 4200)
        self.assertGreater(new_id, 0)

    def test_invoice_text_and_file(self):
        b = self.book(D(2026, 11, 10), D(2026, 11, 12))
        text = s.generate_invoice(self.conn, b)
        self.assertIn("INV-00001", text)
        self.assertIn("Mahindra Thar", text)
        self.assertIn("14,175.00", text)
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(os.path.exists(s.save_invoice(self.conn, b, folder)))

    def test_monthly_revenue_only_counts_returned_bookings(self):
        a = self.book(D(2026, 11, 10), D(2026, 11, 12))
        self.book(D(2026, 11, 20), D(2026, 11, 21), phone="9999999999")   # stays 'booked'
        s.pick_up(self.conn, a)
        s.return_car(self.conn, a, D(2026, 11, 12))
        rev = s.monthly_revenue(self.conn)
        self.assertEqual(rev, [{"month": "2026-11", "revenue": 14175.0, "rentals": 1}])

    def test_dashboard_stats(self):
        b = self.book(D(2026, 11, 1), D(2026, 11, 3))
        s.pick_up(self.conn, b)
        st = s.dashboard_stats(self.conn, self.today)
        self.assertEqual((st["fleet"], st["on_rent"], st["available"], st["open_bookings"]), (10, 1, 9, 1))


if __name__ == "__main__":
    unittest.main()
