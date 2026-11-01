# Car Rental Billing and Fleet Management System

A desktop application written in **Python** (Tkinter + SQLite) for a self-drive car rental business.
It handles the fleet, date-based bookings with automatic double-booking prevention, billing with
discounts and late fines, invoices, and revenue reports.

**Author:** Himanshu Rathee (26MCA20258)

## Features
- **Dashboard:** fleet size, cars available / on rent, open bookings, revenue, latest bookings.
- **Fleet:** add and remove cars; each car shows a live status (Available, Reserved, On rent).
- **New booking:** choose dates, see only the cars that are really free, get an instant price quote.
- **Bookings:** pick up, return (with late-fine calculation), cancel, filter by status.
- **Invoices:** view on screen and save as a text file in the `invoices/` folder.
- **Reports:** revenue per month (bar chart) and most booked cars.

## Rules built into the system
| Rule | Value (change in `service.py`) |
|---|---|
| Days are counted from pickup to return, both days included | |
| Discount for 7 or more days | 10% |
| Discount for 30 or more days | 20% |
| Tax on the discounted amount | 5% (sample value) |
| Late fine per extra day | 1.5 x the daily rate |
| Same car, overlapping dates | rejected |
| Phone number | exactly 10 digits |
| Pickup date in the past | rejected |

## How to run
Python 3.9 or later is needed. There is nothing to install: Tkinter and SQLite come with Python.

```
python app.py
```

The database file `car_rental.db` is created on the first run with a sample fleet.
Use **Tools > Load demo data** to add sample customers and bookings for a demonstration.

## Run the tests
```
python -m unittest -v
```
23 tests cover pricing, discounts, overlap checks, validation, the booking flow, late fines,
invoices and reports.

## Project structure
```
database.py      SQLite connection, tables, sample fleet
service.py       all business rules (no screen code, so it can be tested)
app.py           Tkinter user interface
demo_data.py     sample bookings for demonstrations
test_service.py  unit tests
screenshots/     screenshots of the running application
```

## Notes and limitations
- Rates and the tax percentage are sample values for demonstration.
- Returning a car early does not give a refund.
- There is no login screen; it is meant for one counter computer.
