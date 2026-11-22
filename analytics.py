"""
Analytics engine of FinSight.

Pure functions (no Flask / DB code) so they are easy to test:
  * auto_categorize     - keyword based expense / income categorisation
  * monthly_totals      - income, expense, savings per month
  * category_breakdown  - spending split by category for a month
  * predict_next_month  - Linear Regression forecast of income, expense & savings
  * forecast_categories - weighted moving average forecast per category
  * build_tips          - rule based savings suggestions (50/30/20 rule etc.)
  * detect_anomalies    - unusually large expenses (mean + 2 * std)
"""
import re
from collections import defaultdict
from datetime import date
from statistics import mean, pstdev

import numpy as np
from sklearn.linear_model import LinearRegression

EXPENSE_CATEGORIES = [
    "Food & Dining", "Groceries", "Rent", "Transport", "Bills & Utilities",
    "Shopping", "Entertainment", "Health", "Education", "Travel", "Other",
]
INCOME_CATEGORIES = ["Salary", "Freelance", "Business", "Investments", "Gift", "Other Income"]

NEEDS = {"Rent", "Groceries", "Bills & Utilities", "Transport", "Health", "Education"}
WANTS = {"Food & Dining", "Shopping", "Entertainment", "Travel", "Other"}

KEYWORDS = {
    # ---- expenses ----
    "Food & Dining": ["swiggy", "zomato", "restaurant", "cafe", "pizza", "burger", "dominos",
                      "mcdonald", "kfc", "dinner", "lunch", "breakfast", "chai", "coffee",
                      "starbucks", "biryani", "dhaba", "snacks", "momos"],
    "Groceries": ["grocery", "groceries", "bigbasket", "blinkit", "zepto", "vegetables", "fruits",
                  "milk", "dmart", "supermarket", "kirana", "atta"],
    "Rent": ["rent", "pg", "hostel", "landlord", "maintenance"],
    "Transport": ["uber", "ola", "rapido", "petrol", "diesel", "fuel", "metro", "bus", "train",
                  "irctc", "auto", "cab", "parking", "toll"],
    "Bills & Utilities": ["electricity", "wifi", "broadband", "jio", "airtel", "recharge", "gas",
                          "bill", "insurance", "emi", "dth", "water"],
    "Shopping": ["amazon", "flipkart", "myntra", "ajio", "shopping", "clothes", "shoes", "mall",
                 "nykaa", "gadget", "headphones"],
    "Entertainment": ["netflix", "hotstar", "spotify", "movie", "cinema", "pvr", "game", "prime",
                      "concert", "youtube"],
    "Health": ["doctor", "medicine", "pharmacy", "hospital", "clinic", "gym", "medical", "apollo",
               "checkup"],
    "Education": ["course", "udemy", "tuition", "book", "books", "fees", "exam", "coaching",
                  "college", "stationery"],
    "Travel": ["flight", "hotel", "trip", "makemytrip", "goibibo", "resort", "holiday", "airbnb"],
    # ---- income ----
    "Salary": ["salary", "payroll", "stipend", "wages"],
    "Freelance": ["freelance", "client", "upwork", "fiverr", "gig"],
    "Business": ["sales", "business", "shop"],
    "Investments": ["dividend", "interest", "mutual", "stocks", "sip", "returns", "fd"],
    "Gift": ["gift", "birthday", "bonus", "cashback"],
}


# --------------------------------------------------------------------------- #
# 1. Categorisation
# --------------------------------------------------------------------------- #
def auto_categorize(description, tx_type="expense"):
    """Return the best matching category for a free-text description."""
    text = (description or "").lower()
    allowed = EXPENSE_CATEGORIES if tx_type == "expense" else INCOME_CATEGORIES
    best, best_hits = None, 0
    for category in allowed:
        hits = sum(1 for kw in KEYWORDS.get(category, []) if re.search(rf"\b{re.escape(kw)}\b", text))
        if hits > best_hits:
            best, best_hits = category, hits
    if best:
        return best
    return "Other" if tx_type == "expense" else "Other Income"


# --------------------------------------------------------------------------- #
# 2. Monthly reports
# --------------------------------------------------------------------------- #
def monthly_totals(rows):
    """{'2025-06': {'income':..,'expense':..,'savings':..}, ...} sorted by month."""
    data = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for r in rows:
        data[r["date"][:7]][r["type"]] += float(r["amount"])
    return {m: {**v, "savings": v["income"] - v["expense"]} for m, v in sorted(data.items())}


def category_breakdown(rows, month, tx_type="expense"):
    """Spending (or income) per category for one month, largest first, with % share."""
    totals = defaultdict(float)
    for r in rows:
        if r["date"][:7] == month and r["type"] == tx_type:
            totals[r["category"]] += float(r["amount"])
    grand = sum(totals.values())
    out = [{"category": c, "amount": a, "percent": (a / grand * 100) if grand else 0.0}
           for c, a in totals.items()]
    return sorted(out, key=lambda x: x["amount"], reverse=True)


def daily_spending(rows, month):
    """{day_number: total expense} for the month."""
    days = defaultdict(float)
    for r in rows:
        if r["date"][:7] == month and r["type"] == "expense":
            days[int(r["date"][8:10])] += float(r["amount"])
    return dict(days)


def prev_month_key(ym):
    y, m = map(int, ym.split("-"))
    m -= 1
    if m == 0:
        y, m = y - 1, 12
    return f"{y:04d}-{m:02d}"


def next_month_key(ym):
    y, m = map(int, ym.split("-"))
    m += 1
    if m == 13:
        y, m = y + 1, 1
    return f"{y:04d}-{m:02d}"


def percent_change(new, old):
    if not old:
        return None
    return (new - old) / old * 100


# --------------------------------------------------------------------------- #
# 3. Prediction
# --------------------------------------------------------------------------- #
def forecast_series(values):
    """
    Forecast the next value of a monthly series.
    Returns (prediction, r2_score, method_name).
      * < 3 data points -> simple average
      * otherwise       -> Linear Regression on month index
    """
    n = len(values)
    if n == 0:
        return 0.0, 0.0, "no-data"
    if n < 3:
        return float(mean(values)), 0.0, "average"
    X = np.arange(n).reshape(-1, 1)
    y = np.array(values, dtype=float)
    model = LinearRegression().fit(X, y)
    pred = float(model.predict(np.array([[n]]))[0])
    return max(pred, 0.0), float(model.score(X, y)), "linear-regression"


def _history_months(totals, today, window):
    """Use completed months for training (current month is partial)."""
    current = today.strftime("%Y-%m")
    months = [m for m in totals if m < current] or list(totals)
    return months[-window:]


def predict_next_month(rows, today=None, window=6):
    """Forecast income, expense and savings for the upcoming month."""
    today = today or date.today()
    totals = monthly_totals(rows)
    if not totals:
        return None
    months = _history_months(totals, today, window)
    inc, inc_r2, method = forecast_series([totals[m]["income"] for m in months])
    exp, exp_r2, _ = forecast_series([totals[m]["expense"] for m in months])
    return {
        "target_month": next_month_key(months[-1]),
        "months_used": months,
        "history_income": [totals[m]["income"] for m in months],
        "history_expense": [totals[m]["expense"] for m in months],
        "history_savings": [totals[m]["savings"] for m in months],
        "predicted_income": inc,
        "predicted_expense": exp,
        "predicted_savings": inc - exp,
        "predicted_savings_rate": ((inc - exp) / inc * 100) if inc else 0.0,
        "method": method,
        "r2": exp_r2,
        "confidence": "High" if exp_r2 >= 0.6 else "Medium" if exp_r2 >= 0.3 else "Low",
    }


def forecast_categories(rows, today=None, window=6):
    """Weighted moving average (weights 1,2,3 on last 3 months) per expense category."""
    today = today or date.today()
    totals = monthly_totals(rows)
    if not totals:
        return []
    months = _history_months(totals, today, window)
    per_cat = defaultdict(lambda: defaultdict(float))
    for r in rows:
        if r["type"] == "expense" and r["date"][:7] in months:
            per_cat[r["category"]][r["date"][:7]] += float(r["amount"])
    out = []
    for cat, by_month in per_cat.items():
        series = [by_month.get(m, 0.0) for m in months]
        last = series[-3:]
        weights = list(range(1, len(last) + 1))
        predicted = sum(v * w for v, w in zip(last, weights)) / sum(weights)
        prior = series[:-1]
        base = mean(prior) if prior else 0.0
        out.append({
            "category": cat, "predicted": predicted, "last_month": series[-1],
            "average": mean(series), "growth": percent_change(series[-1], base),
        })
    return sorted(out, key=lambda x: x["predicted"], reverse=True)


# --------------------------------------------------------------------------- #
# 4. Savings suggestions
# --------------------------------------------------------------------------- #
def build_tips(prediction, cat_forecast, reduce_pct=15):
    """Rule based advice. Returns dict(tips=[...], potential_savings=float, ...)."""
    if not prediction:
        return {"tips": [], "potential_savings": 0.0, "ideal_savings": 0.0}
    inc, exp = prediction["predicted_income"], prediction["predicted_expense"]
    rate = prediction["predicted_savings_rate"]
    tips = []

    if rate >= 20:
        tips.append(("good", f"Great! Your forecast savings rate is {rate:.0f}% - above the recommended 20%."))
    elif rate >= 10:
        tips.append(("warn", f"Your forecast savings rate is {rate:.0f}%. Aim for 20% to build wealth faster."))
    else:
        tips.append(("bad", f"Your forecast savings rate is only {rate:.0f}%. Expenses are eating most of your income."))

    wants_total = sum(c["predicted"] for c in cat_forecast if c["category"] in WANTS)
    if inc and wants_total / inc > 0.30:
        tips.append(("warn", f"Discretionary spending (food outside, shopping, entertainment...) is "
                             f"{wants_total / inc * 100:.0f}% of income; the 50/30/20 rule suggests 30%."))

    if cat_forecast:
        top = cat_forecast[0]
        share = top["predicted"] / exp * 100 if exp else 0
        tips.append(("info", f"'{top['category']}' is your biggest expense (~{share:.0f}% of spending)."))
        growing = [c for c in cat_forecast if c["growth"] is not None and c["growth"] > 15 and c["last_month"] >= 500]
        if growing:
            g = max(growing, key=lambda c: c["growth"])
            tips.append(("warn", f"'{g['category']}' grew {g['growth']:.0f}% last month compared with your earlier average. Keep an eye on it."))

    potential = sum(c["predicted"] for c in cat_forecast if c["category"] in WANTS) * reduce_pct / 100
    ideal = inc * 0.20
    if potential > 0:
        tips.append(("good", f"Cutting discretionary categories by {reduce_pct}% could save about ₹{potential:,.0f} every month."))
    if exp:
        target = exp * 3
        sv = max(prediction["predicted_savings"], 0)
        months_needed = target / sv if sv else None
        msg = f"Emergency fund goal (3 x monthly expenses) = ₹{target:,.0f}."
        msg += f" At the forecast savings it takes ~{months_needed:.0f} months." if months_needed else " Start saving to reach it."
        tips.append(("info", msg))
    return {"tips": tips, "potential_savings": potential, "ideal_savings": ideal}


def detect_anomalies(rows, month):
    """Expenses in `month` that are > mean + 2*std of that category's earlier expenses."""
    history = defaultdict(list)
    current = []
    for r in rows:
        if r["type"] != "expense":
            continue
        if r["date"][:7] == month:
            current.append(r)
        elif r["date"][:7] < month:
            history[r["category"]].append(float(r["amount"]))
    flagged = []
    for r in current:
        past = history.get(r["category"], [])
        if len(past) >= 4:
            limit = mean(past) + 2 * pstdev(past)
            if pstdev(past) > 0 and float(r["amount"]) > limit:
                flagged.append({**dict(r), "limit": limit})
    return flagged
