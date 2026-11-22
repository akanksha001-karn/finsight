"""Run with:  python -m unittest discover -s tests -v"""
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import analytics
from app import create_app, inr


def rows(months):
    """months: list of (ym, income, expense)"""
    out = []
    for ym, inc, exp in months:
        out.append({"date": f"{ym}-01", "type": "income", "amount": inc, "category": "Salary", "description": ""})
        out.append({"date": f"{ym}-10", "type": "expense", "amount": exp, "category": "Food & Dining", "description": ""})
    return out


class AnalyticsTests(unittest.TestCase):
    def test_auto_categorize(self):
        self.assertEqual(analytics.auto_categorize("Swiggy dinner"), "Food & Dining")
        self.assertEqual(analytics.auto_categorize("Uber to office"), "Transport")
        self.assertEqual(analytics.auto_categorize("March salary", "income"), "Salary")
        self.assertEqual(analytics.auto_categorize("something random"), "Other")
        self.assertEqual(analytics.auto_categorize("business class"), "Other")  # 'bus' must not match

    def test_monthly_totals(self):
        t = analytics.monthly_totals(rows([("2025-01", 1000, 400)]))
        self.assertEqual(t["2025-01"]["savings"], 600)

    def test_linear_forecast_follows_trend(self):
        pred, r2, method = analytics.forecast_series([1000, 2000, 3000, 4000])
        self.assertAlmostEqual(pred, 5000, delta=1)
        self.assertEqual(method, "linear-regression")
        self.assertGreater(r2, 0.99)

    def test_forecast_small_data_uses_average(self):
        self.assertEqual(analytics.forecast_series([100, 300])[0], 200)
        self.assertEqual(analytics.forecast_series([])[0], 0)

    def test_predict_next_month(self):
        data = rows([("2025-01", 50000, 20000), ("2025-02", 50000, 22000),
                     ("2025-03", 50000, 24000), ("2025-04", 50000, 26000)])
        p = analytics.predict_next_month(data, today=date(2025, 5, 10))
        self.assertEqual(p["target_month"], "2025-05")
        self.assertAlmostEqual(p["predicted_expense"], 28000, delta=1)
        self.assertAlmostEqual(p["predicted_savings"], 22000, delta=1)

    def test_month_keys(self):
        self.assertEqual(analytics.next_month_key("2025-12"), "2026-01")
        self.assertEqual(analytics.prev_month_key("2025-01"), "2024-12")

    def test_anomaly(self):
        data = [{"date": f"2025-0{m}-05", "type": "expense", "amount": a, "category": "Shopping", "description": "x"}
                for m, a in [(1, 1000), (2, 1100), (3, 900), (4, 1050)]]
        data.append({"date": "2025-05-05", "type": "expense", "amount": 9000, "category": "Shopping", "description": "TV"})
        self.assertEqual(len(analytics.detect_anomalies(data, "2025-05")), 1)

    def test_inr_format(self):
        self.assertEqual(inr(1234567), "₹12,34,567")
        self.assertEqual(inr(999.5), "₹999.50")


class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.app = create_app({"TESTING": True, "DATABASE": self.tmp.name, "SECRET_KEY": "t"})
        self.c = self.app.test_client()

    def tearDown(self):
        os.unlink(self.tmp.name)

    def token(self):
        self.c.get("/login")
        with self.c.session_transaction() as s:
            return s["_csrf"]

    def register_login(self):
        t = self.token()
        self.c.post("/register", data={"name": "A", "email": "a@x.com", "password": "secret1", "_csrf": t})
        self.c.post("/login", data={"email": "a@x.com", "password": "secret1", "_csrf": t})
        self.c.get("/dashboard")          # login resets the session, so read the fresh token
        with self.c.session_transaction() as s:
            return s["_csrf"]

    def test_requires_login(self):
        self.assertEqual(self.c.get("/dashboard").status_code, 302)

    def test_csrf_blocks_post(self):
        self.assertEqual(self.c.post("/login", data={"email": "a", "password": "b"}).status_code, 400)

    def test_full_flow(self):
        t = self.register_login()
        r = self.c.post("/transactions/add", data={"type": "expense", "amount": "250", "category": "auto",
                        "description": "Swiggy dinner", "date": date.today().isoformat(), "_csrf": t})
        self.assertEqual(r.status_code, 302)
        page = self.c.get("/transactions").get_data(as_text=True)
        self.assertIn("Food &amp; Dining", page)
        for url in ("/dashboard", "/reports", "/insights", "/budgets", "/export.csv"):
            self.assertEqual(self.c.get(url).status_code, 200, url)

    def test_rejects_bad_amount(self):
        t = self.register_login()
        self.c.post("/transactions/add", data={"type": "expense", "amount": "-5", "category": "auto",
                    "description": "x", "date": "2025-01-01", "_csrf": t})
        self.assertNotIn("x</td>", self.c.get("/transactions").get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
