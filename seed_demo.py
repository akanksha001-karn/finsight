"""Fill the database with 8 months of realistic demo data.

Usage:  python seed_demo.py
Login:  demo@finsight.app / demo1234
"""
import random
from datetime import date

from werkzeug.security import generate_password_hash

import db
from app import create_app

random.seed(42)

# (description, category, min, max, times per month)
EXPENSE_PLAN = [
    ("Rent for PG", "Rent", 9000, 9000, 1),
    ("Electricity bill", "Bills & Utilities", 900, 1500, 1),
    ("Jio recharge", "Bills & Utilities", 399, 399, 1),
    ("Bigbasket groceries", "Groceries", 600, 1800, 4),
    ("Uber to office", "Transport", 120, 400, 6),
    ("Petrol", "Transport", 500, 900, 2),
    ("Swiggy dinner", "Food & Dining", 250, 700, 6),
    ("Zomato lunch", "Food & Dining", 200, 550, 4),
    ("Amazon shopping", "Shopping", 500, 3000, 2),
    ("Netflix subscription", "Entertainment", 649, 649, 1),
    ("Movie at PVR", "Entertainment", 400, 900, 1),
    ("Pharmacy medicine", "Health", 200, 800, 1),
    ("Udemy course", "Education", 449, 899, 1),
]


def last_months(n):
    today = date.today()
    y, m = today.year, today.month
    out = []
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return list(reversed(out))


def run():
    app = create_app()
    with app.app_context():
        conn = db.get_db()
        conn.execute("DELETE FROM users WHERE email = ?", ("demo@finsight.app",))
        cur = conn.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                           ("Demo User", "demo@finsight.app", generate_password_hash("demo1234", method="pbkdf2:sha256")))
        uid = cur.lastrowid
        rows = []
        months = last_months(8)
        for idx, (y, m) in enumerate(months):
            is_current = (y, m) == (date.today().year, date.today().month)
            max_day = date.today().day if is_current else 28
            growth = 1 + idx * 0.045          # lifestyle inflation: spending rises every month
            rows.append(("income", 45000 + (idx % 3) * 500, "Salary", "Monthly salary", date(y, m, 1)))
            if idx % 3 == 1:
                rows.append(("income", random.randint(4000, 9000), "Freelance", "Freelance client project", date(y, m, min(15, max_day))))
            for desc, cat, lo, hi, times in EXPENSE_PLAN:
                scale = growth if cat in ("Food & Dining", "Shopping", "Entertainment", "Transport") else 1.0
                for _ in range(times):
                    day = random.randint(1, max_day)
                    amt = round(random.uniform(lo, hi) * scale, 0)
                    rows.append(("expense", amt, cat, desc, date(y, m, day)))
        rows = [r for r in rows if r[4] <= date.today()]
        conn.executemany(
            "INSERT INTO transactions (user_id, type, amount, category, description, date) VALUES (?,?,?,?,?,?)",
            [(uid, t, a, c, d, dt.isoformat()) for t, a, c, d, dt in rows])
        conn.executemany("INSERT INTO budgets (user_id, category, monthly_limit) VALUES (?,?,?)",
                         [(uid, "Food & Dining", 6000), (uid, "Shopping", 4000),
                          (uid, "Transport", 4500), (uid, "Entertainment", 2000)])
        conn.commit()
        print(f"Seeded {len(rows)} transactions. Login: demo@finsight.app / demo1234")


if __name__ == "__main__":
    run()
