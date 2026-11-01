"""Car Rental Billing and Fleet Management System: Tkinter desktop app.

Run with:  python app.py
"""
import os
import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, simpledialog, ttk

import database
import demo_data
import service as s

INVOICE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "invoices")
DARK, RED, AMBER, GREEN, GREY, BG = "#111114", "#E6231E", "#B8860B", "#1E8449", "#6B7280", "#F4F4F6"


class App(tk.Tk):
    def __init__(self, db_path=database.DB_PATH):
        super().__init__()
        self.conn = database.get_connection(db_path)
        database.init_db(self.conn)
        self.title("Car Rental Billing and Fleet Management System")
        self.geometry("1060x680")
        self.minsize(960, 620)
        self.configure(bg=BG)
        self._style()
        self._menu()
        self._header()
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=14, pady=(8, 14))
        for build, label in [(self._dashboard_tab, "Dashboard"), (self._fleet_tab, "Fleet"),
                             (self._booking_tab, "New Booking"), (self._bookings_tab, "Bookings"),
                             (self._reports_tab, "Reports")]:
            frame = ttk.Frame(self.tabs, padding=14)
            self.tabs.add(frame, text=f"  {label}  ")
            build(frame)
        self.refresh_all()

    # ---------- look and feel ----------
    def _style(self):
        st = ttk.Style(self)
        st.theme_use("clam")
        st.configure(".", font=("Arial", 10), background=BG)
        st.configure("TFrame", background=BG)
        st.configure("TLabel", background=BG)
        st.configure("TNotebook", background=BG, borderwidth=0)
        st.configure("TNotebook.Tab", padding=(10, 6), font=("Arial", 10, "bold"))
        st.map("TNotebook.Tab", background=[("selected", "white")], foreground=[("selected", RED)])
        st.configure("Treeview", rowheight=26, font=("Arial", 10))
        st.configure("Treeview.Heading", font=("Arial", 10, "bold"), background="#E5E7EB")
        st.configure("Accent.TButton", background=RED, foreground="white", font=("Arial", 10, "bold"), padding=(12, 6))
        st.map("Accent.TButton", background=[("active", "#B71C18")])
        st.configure("TButton", padding=(10, 5))
        st.configure("Card.TFrame", background="white", relief="solid", borderwidth=1)
        st.configure("CardNum.TLabel", background="white", font=("Arial", 24, "bold"), foreground=RED)
        st.configure("CardTxt.TLabel", background="white", foreground=GREY)
        st.configure("H.TLabel", font=("Arial", 13, "bold"))

    def _menu(self):
        bar = tk.Menu(self)
        tools = tk.Menu(bar, tearoff=0)
        tools.add_command(label="Load demo data", command=self.load_demo)
        tools.add_command(label="Refresh all", command=self.refresh_all)
        tools.add_separator()
        tools.add_command(label="Exit", command=self.destroy)
        bar.add_cascade(label="Tools", menu=tools)
        self.config(menu=bar)

    def _header(self):
        head = tk.Frame(self, bg=DARK, height=62)
        head.pack(fill="x")
        head.pack_propagate(False)
        tk.Label(head, text="LUXURY AUTO RENTAL", bg=DARK, fg="white", font=("Arial", 16, "bold")).pack(side="left", padx=18)
        tk.Label(head, text="Billing and Fleet Management", bg=DARK, fg="#9CA3AF", font=("Arial", 10)).pack(side="left")
        tk.Label(head, text=date.today().strftime("%d %B %Y"), bg=DARK, fg="#9CA3AF").pack(side="right", padx=18)

    def _tree(self, parent, columns, widths, height=10):
        tree = ttk.Treeview(parent, columns=[c[0] for c in columns], show="headings", height=height, selectmode="browse")
        for (key, title), w in zip(columns, widths):
            tree.heading(key, text=title)
            tree.column(key, width=w, anchor="w")
        tree.tag_configure("picked_up", foreground=AMBER)
        tree.tag_configure("returned", foreground=GREEN)
        tree.tag_configure("cancelled", foreground=GREY)
        return tree

    def _scrolled(self, tree, parent):
        sb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

    # ---------- dashboard ----------
    def _dashboard_tab(self, f):
        row = ttk.Frame(f)
        row.pack(fill="x")
        self.stat = {}
        for key, label in [("fleet", "Cars in fleet"), ("available", "Available today"), ("on_rent", "Currently on rent"),
                           ("open_bookings", "Open bookings"), ("revenue", "Revenue (returned rentals)")]:
            card = ttk.Frame(row, style="Card.TFrame", padding=12)
            card.pack(side="left", expand=True, fill="x", padx=5)
            self.stat[key] = ttk.Label(card, text="0", style="CardNum.TLabel")
            self.stat[key].pack(anchor="w")
            ttk.Label(card, text=label, style="CardTxt.TLabel").pack(anchor="w")
        ttk.Label(f, text="Latest bookings", style="H.TLabel").pack(anchor="w", pady=(18, 6))
        box = ttk.Frame(f)
        box.pack(fill="both", expand=True)
        self.dash_tree = self._tree(box, [("id", "ID"), ("car", "Car"), ("cust", "Customer"), ("dates", "Dates"),
                                          ("status", "Status"), ("total", "Total")], [50, 210, 170, 210, 100, 130], 9)
        self._scrolled(self.dash_tree, box)

    # ---------- fleet ----------
    def _fleet_tab(self, f):
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Button(bar, text="Add car", style="Accent.TButton", command=self.add_car_dialog).pack(side="left")
        ttk.Button(bar, text="Remove selected car", command=self.remove_car).pack(side="left", padx=8)
        box = ttk.Frame(f)
        box.pack(fill="both", expand=True)
        self.fleet_tree = self._tree(box, [("id", "ID"), ("name", "Car"), ("cat", "Category"), ("seats", "Seats"),
                                           ("fuel", "Fuel"), ("trans", "Transmission"), ("rate", "Rate / day"), ("status", "Status")],
                                     [50, 220, 90, 60, 80, 110, 120, 110], 15)
        self._scrolled(self.fleet_tree, box)

    def add_car_dialog(self):
        win = tk.Toplevel(self)
        win.title("Add car")
        win.configure(bg=BG)
        win.transient(self)
        win.grab_set()
        fields, vars_ = ["Car name", "Category (sedan / suv / auto)", "Seats", "Fuel", "Transmission", "Rate per day (Rs)"], []
        defaults = ["", "sedan", "5", "Petrol", "Manual", ""]
        for i, (label, default) in enumerate(zip(fields, defaults)):
            ttk.Label(win, text=label).grid(row=i, column=0, sticky="w", padx=14, pady=6)
            v = tk.StringVar(value=default)
            ttk.Entry(win, textvariable=v, width=28).grid(row=i, column=1, padx=14, pady=6)
            vars_.append(v)

        def save():
            try:
                s.add_car(self.conn, *[v.get() for v in vars_])
            except s.RentalError as e:
                messagebox.showerror("Cannot add car", str(e), parent=win)
                return
            win.destroy()
            self.refresh_all()
        ttk.Button(win, text="Save car", style="Accent.TButton", command=save).grid(row=len(fields), column=0, columnspan=2, pady=12)

    def remove_car(self):
        sel = self.fleet_tree.selection()
        if not sel:
            messagebox.showinfo("Remove car", "Select a car in the list first.")
            return
        if not messagebox.askyesno("Remove car", "Remove this car from the fleet?"):
            return
        try:
            s.remove_car(self.conn, int(sel[0]))
        except s.RentalError as e:
            messagebox.showerror("Cannot remove car", str(e))
            return
        self.refresh_all()

    # ---------- new booking ----------
    def _booking_tab(self, f):
        left = ttk.Frame(f)
        left.pack(side="left", fill="both", expand=True, padx=(0, 14))
        ttk.Label(left, text="1. Choose dates", style="H.TLabel").pack(anchor="w")
        row = ttk.Frame(left)
        row.pack(fill="x", pady=6)
        self.start_var = tk.StringVar(value=date.today().isoformat())
        self.end_var = tk.StringVar(value=(date.today() + timedelta(days=2)).isoformat())
        for text, var in [("Pickup (YYYY-MM-DD)", self.start_var), ("Return (YYYY-MM-DD)", self.end_var)]:
            ttk.Label(row, text=text).pack(side="left")
            ttk.Entry(row, textvariable=var, width=12).pack(side="left", padx=(6, 14))
        ttk.Button(row, text="Find available cars", style="Accent.TButton", command=self.find_cars).pack(side="left")
        ttk.Label(left, text="2. Pick a car", style="H.TLabel").pack(anchor="w", pady=(14, 4))
        box = ttk.Frame(left)
        box.pack(fill="both", expand=True)
        self.avail_tree = self._tree(box, [("name", "Car"), ("cat", "Category"), ("seats", "Seats"), ("rate", "Rate / day")],
                                     [210, 80, 60, 110], 12)
        self._scrolled(self.avail_tree, box)
        self.avail_tree.bind("<<TreeviewSelect>>", lambda e: self.update_quote())

        right = ttk.Frame(f, style="Card.TFrame", padding=16)
        right.pack(side="left", fill="y")
        ttk.Label(right, text="3. Customer details", style="H.TLabel", background="white").pack(anchor="w", pady=(0, 8))
        self.cust_vars = {}
        for key, label in [("name", "Full name"), ("phone", "Phone (10 digits)"), ("licence", "Driving licence no.")]:
            ttk.Label(right, text=label, background="white").pack(anchor="w", pady=(6, 0))
            self.cust_vars[key] = tk.StringVar()
            ttk.Entry(right, textvariable=self.cust_vars[key], width=30).pack(anchor="w")
        ttk.Label(right, text="Price quote", style="H.TLabel", background="white").pack(anchor="w", pady=(18, 4))
        self.quote_lbl = ttk.Label(right, text="Select a car to see the price.", background="white", justify="left", foreground=GREY)
        self.quote_lbl.pack(anchor="w")
        ttk.Button(right, text="Create booking", style="Accent.TButton", command=self.create_booking).pack(anchor="w", pady=18)

    def _dates(self):
        return s.parse_date(self.start_var.get()), s.parse_date(self.end_var.get())

    def find_cars(self):
        try:
            start, end = self._dates()
            cars = s.find_available_cars(self.conn, start, end)
        except s.RentalError as e:
            messagebox.showerror("Check the dates", str(e))
            return
        self.avail_tree.delete(*self.avail_tree.get_children())
        for c in cars:
            self.avail_tree.insert("", "end", iid=str(c["car_id"]),
                                   values=(c["name"], c["category"], c["seats"], s.money(c["daily_rate"])))
        self.quote_lbl.config(text=f"{len(cars)} car(s) free for these dates." if cars else "No cars are free for these dates.")

    def update_quote(self):
        sel = self.avail_tree.selection()
        if not sel:
            return
        try:
            start, end = self._dates()
            rate = self.conn.execute("SELECT daily_rate FROM cars WHERE car_id = ?", (int(sel[0]),)).fetchone()[0]
            q = s.calculate_quote(rate, start, end)
        except s.RentalError as e:
            self.quote_lbl.config(text=str(e))
            return
        self.quote_lbl.config(foreground="black", text=(
            f"{q['days']} day(s) x {s.money(rate)}\nBase      {s.money(q['base'])}\n"
            f"Discount  -{s.money(q['discount'])} ({q['discount_rate']:.0%})\nTax       {s.money(q['tax'])}\n"
            f"TOTAL     {s.money(q['total'])}"))

    def create_booking(self):
        sel = self.avail_tree.selection()
        if not sel:
            messagebox.showinfo("New booking", "Find available cars and select one first.")
            return
        try:
            start, end = self._dates()
            booking_id = s.create_booking(self.conn, int(sel[0]), self.cust_vars["name"].get(), self.cust_vars["phone"].get(),
                                          self.cust_vars["licence"].get(), start, end)
        except s.RentalError as e:
            messagebox.showerror("Cannot create booking", str(e))
            return
        messagebox.showinfo("Booking created", f"Booking #{booking_id} saved.\nOpen the Bookings tab to pick up the car.")
        for v in self.cust_vars.values():
            v.set("")
        self.refresh_all()
        self.find_cars()

    # ---------- bookings ----------
    def _bookings_tab(self, f):
        bar = ttk.Frame(f)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Label(bar, text="Show").pack(side="left")
        self.filter_var = tk.StringVar(value="all")
        combo = ttk.Combobox(bar, textvariable=self.filter_var, state="readonly", width=12,
                             values=["all", "booked", "picked_up", "returned", "cancelled"])
        combo.pack(side="left", padx=(6, 16))
        combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_bookings())
        ttk.Button(bar, text="Pick up", command=lambda: self._act("pick")).pack(side="left")
        ttk.Button(bar, text="Return car", style="Accent.TButton", command=lambda: self._act("return")).pack(side="left", padx=8)
        ttk.Button(bar, text="Cancel booking", command=lambda: self._act("cancel")).pack(side="left")
        ttk.Button(bar, text="Invoice", command=self.show_invoice).pack(side="left", padx=8)
        box = ttk.Frame(f)
        box.pack(fill="both", expand=True)
        self.book_tree = self._tree(box, [("id", "ID"), ("car", "Car"), ("cust", "Customer"), ("phone", "Phone"), ("start", "Pickup"),
                                          ("end", "Return"), ("status", "Status"), ("fine", "Fine"), ("total", "Total")],
                                    [45, 170, 130, 100, 90, 90, 90, 90, 110], 15)
        self._scrolled(self.book_tree, box)

    def _selected_booking(self):
        sel = self.book_tree.selection()
        if not sel:
            messagebox.showinfo("Bookings", "Select a booking in the list first.")
            return None
        return int(sel[0])

    def _act(self, action):
        booking_id = self._selected_booking()
        if booking_id is None:
            return
        try:
            if action == "pick":
                s.pick_up(self.conn, booking_id)
            elif action == "cancel":
                if not messagebox.askyesno("Cancel booking", f"Cancel booking #{booking_id}?"):
                    return
                s.cancel_booking(self.conn, booking_id)
            else:
                text = simpledialog.askstring("Return car", "Date the car came back (YYYY-MM-DD):",
                                              initialvalue=date.today().isoformat(), parent=self)
                if not text:
                    return
                r = s.return_car(self.conn, booking_id, s.parse_date(text))
                late = f"{r['late_days']} day(s) late, fine {s.money(r['fine'])}" if r["late_days"] else "returned on time, no fine"
                messagebox.showinfo("Car returned", f"Booking #{booking_id}: {late}.\nFinal total: {s.money(r['total'])}")
        except s.RentalError as e:
            messagebox.showerror("Not allowed", str(e))
            return
        self.refresh_all()

    def show_invoice(self):
        booking_id = self._selected_booking()
        if booking_id is None:
            return
        win = tk.Toplevel(self)
        win.title(f"Invoice #{booking_id}")
        txt = tk.Text(win, width=52, height=22, font=("Courier New", 10), bg="white", padx=12, pady=12)
        txt.insert("1.0", s.generate_invoice(self.conn, booking_id))
        txt.config(state="disabled")
        txt.pack(padx=10, pady=10)

        def save():
            path = s.save_invoice(self.conn, booking_id, INVOICE_DIR)
            messagebox.showinfo("Invoice saved", f"Saved to:\n{path}", parent=win)
        ttk.Button(win, text="Save as text file", style="Accent.TButton", command=save).pack(pady=(0, 12))

    # ---------- reports ----------
    def _reports_tab(self, f):
        ttk.Label(f, text="Revenue per month (returned rentals)", style="H.TLabel").pack(anchor="w")
        self.chart = tk.Canvas(f, width=640, height=270, bg="white", highlightthickness=1, highlightbackground="#D1D5DB")
        self.chart.pack(anchor="w", pady=(6, 14))
        ttk.Label(f, text="Most booked cars", style="H.TLabel").pack(anchor="w")
        box = ttk.Frame(f)
        box.pack(fill="both", expand=True, pady=(6, 0))
        self.pop_tree = self._tree(box, [("car", "Car"), ("n", "Bookings")], [260, 100], 5)
        self._scrolled(self.pop_tree, box)

    def draw_chart(self):
        c = self.chart
        c.delete("all")
        data = s.monthly_revenue(self.conn)[-6:]
        if not data:
            c.create_text(320, 135, text="No returned rentals yet.", fill=GREY)
            return
        top = max(d["revenue"] for d in data)
        width, base_y, plot_h = 640, 225, 170
        slot = width / len(data)
        for i, d in enumerate(data):
            h = plot_h * d["revenue"] / top
            x0 = i * slot + slot * 0.2
            x1 = (i + 1) * slot - slot * 0.2
            c.create_rectangle(x0, base_y - h, x1, base_y, fill=RED, outline="")
            c.create_text((x0 + x1) / 2, base_y - h - 10, text=f"{d['revenue']:,.0f}", font=("Arial", 9, "bold"))
            c.create_text((x0 + x1) / 2, base_y + 14, text=d["month"])
            c.create_text((x0 + x1) / 2, base_y + 30, text=f"{d['rentals']} rental(s)", fill=GREY, font=("Arial", 9))
        c.create_line(10, base_y, width - 10, base_y, fill="#9CA3AF")

    # ---------- refreshing ----------
    def refresh_all(self):
        stats = s.dashboard_stats(self.conn)
        for key, lbl in self.stat.items():
            lbl.config(text=s.money(stats[key]).replace(".00", "") if key == "revenue" else str(stats[key]))
        self.dash_tree.delete(*self.dash_tree.get_children())
        for b in s.list_bookings(self.conn)[:8]:
            self.dash_tree.insert("", "end", iid=str(b["booking_id"]), tags=(b["status"],),
                                  values=(b["booking_id"], b["car_name"], b["customer"], f"{b['start_date']}  to  {b['end_date']}",
                                          b["status"], s.money(b["total"])))
        self.fleet_tree.delete(*self.fleet_tree.get_children())
        for c in s.list_cars(self.conn):
            self.fleet_tree.insert("", "end", iid=str(c["car_id"]), tags=("picked_up" if c["status"] == "On rent" else "",),
                                   values=(c["car_id"], c["name"], c["category"], c["seats"], c["fuel"], c["transmission"],
                                           s.money(c["daily_rate"]), c["status"]))
        self.refresh_bookings()
        self.pop_tree.delete(*self.pop_tree.get_children())
        for p in s.car_popularity(self.conn)[:5]:
            self.pop_tree.insert("", "end", values=(p["name"], p["bookings"]))
        self.draw_chart()
        self.find_cars_quietly()

    def refresh_bookings(self):
        self.book_tree.delete(*self.book_tree.get_children())
        for b in s.list_bookings(self.conn, self.filter_var.get()):
            self.book_tree.insert("", "end", iid=str(b["booking_id"]), tags=(b["status"],),
                                  values=(b["booking_id"], b["car_name"], b["customer"], b["phone"], b["start_date"], b["end_date"],
                                          b["status"], s.money(b["fine"]) if b["fine"] else "-", s.money(b["total"])))

    def find_cars_quietly(self):
        """Keep the 'New Booking' list current without showing error pop-ups."""
        try:
            start, end = self._dates()
            cars = s.find_available_cars(self.conn, start, end)
        except s.RentalError:
            return
        self.avail_tree.delete(*self.avail_tree.get_children())
        for c in cars:
            self.avail_tree.insert("", "end", iid=str(c["car_id"]),
                                   values=(c["name"], c["category"], c["seats"], s.money(c["daily_rate"])))

    def load_demo(self):
        if demo_data.load_demo(self.conn):
            messagebox.showinfo("Demo data", "Sample customers and bookings were added.")
        else:
            messagebox.showinfo("Demo data", "Demo data is only added to a database with no bookings.")
        self.refresh_all()


if __name__ == "__main__":
    App().mainloop()
