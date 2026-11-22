"""FinSight - Personal Finance & Expense Intelligence System (Flask)."""
import csv
import io
import os
import secrets
import sqlite3
from datetime import date, datetime
from functools import wraps

from flask import (Flask, Response, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

import analytics
import db


def inr(value):
    """Format a number in Indian style: 1234567 -> ₹12,34,567"""
    value = float(value or 0)
    neg, value = value < 0, abs(value)
    whole, dec = f"{value:.2f}".split(".")
    if len(whole) > 3:
        head, tail, parts = whole[:-3], whole[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        whole = ",".join(parts + [tail])
    return f"{'-' if neg else ''}₹{whole}{'' if dec == '00' else '.' + dec}"


def month_label(ym):
    return datetime.strptime(ym, "%Y-%m").strftime("%b %Y")


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-secret-change-me"),
        DATABASE=os.path.join(app.instance_path, "finsight.db"),
    )
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)

    app.jinja_env.filters["inr"] = inr
    app.jinja_env.filters["month_label"] = month_label
    app.jinja_env.globals["csrf_token"] = lambda: session.setdefault("_csrf", secrets.token_hex(16))

    # ------------------------------------------------------------------ #
    # request hooks / helpers
    # ------------------------------------------------------------------ #
    @app.before_request
    def csrf_protect():
        if request.method == "POST":
            token = session.get("_csrf")
            if not token or token != request.form.get("_csrf"):
                abort(400, "Invalid CSRF token")

    @app.before_request
    def load_user():
        uid = session.get("user_id")
        g.user = None
        if uid:
            g.user = db.get_db().execute(
                "SELECT id, name, email FROM users WHERE id = ?", (uid,)).fetchone()

    def login_required(view):
        @wraps(view)
        def wrapped(*a, **kw):
            if g.user is None:
                return redirect(url_for("login"))
            return view(*a, **kw)
        return wrapped

    def all_transactions():
        rows = db.get_db().execute(
            "SELECT * FROM transactions WHERE user_id = ? ORDER BY date, id", (g.user["id"],)).fetchall()
        return [dict(r) for r in rows]

    def valid_month(value):
        try:
            datetime.strptime(value, "%Y-%m")
            return value
        except (TypeError, ValueError):
            return date.today().strftime("%Y-%m")

    # ------------------------------------------------------------------ #
    # authentication
    # ------------------------------------------------------------------ #
    @app.route("/")
    def index():
        return redirect(url_for("dashboard" if g.user else "login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            error = None
            if not name or not email or "@" not in email:
                error = "Please enter a valid name and email."
            elif len(password) < 6:
                error = "Password must be at least 6 characters."
            if error is None:
                try:
                    db.get_db().execute(
                        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                        (name, email, generate_password_hash(password, method="pbkdf2:sha256")))
                    db.get_db().commit()
                except sqlite3.IntegrityError:
                    error = "This email is already registered."
                else:
                    flash("Account created. Please log in.", "success")
                    return redirect(url_for("login"))
            flash(error, "error")
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = db.get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                return redirect(url_for("dashboard"))
            flash("Invalid email or password.", "error")
        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # ------------------------------------------------------------------ #
    # dashboard
    # ------------------------------------------------------------------ #
    @app.route("/dashboard")
    @login_required
    def dashboard():
        rows = all_transactions()
        month = date.today().strftime("%Y-%m")
        totals = analytics.monthly_totals(rows)
        cur = totals.get(month, {"income": 0, "expense": 0, "savings": 0})
        rate = (cur["savings"] / cur["income"] * 100) if cur["income"] else 0
        last6 = list(totals.keys())[-6:]
        chart = {
            "months": [month_label(m) for m in last6],
            "income": [round(totals[m]["income"]) for m in last6],
            "expense": [round(totals[m]["expense"]) for m in last6],
            "cat_labels": [c["category"] for c in analytics.category_breakdown(rows, month)],
            "cat_values": [round(c["amount"]) for c in analytics.category_breakdown(rows, month)],
        }
        recent = list(reversed(rows))[:6]
        return render_template("dashboard.html", month=month, cur=cur, rate=rate, chart=chart,
                               recent=recent, budget_status=budget_status(month)[:4],
                               balance=sum(t["savings"] for t in totals.values()))

    # ------------------------------------------------------------------ #
    # transactions CRUD
    # ------------------------------------------------------------------ #
    @app.route("/transactions")
    @login_required
    def transactions():
        month = request.args.get("month", "")
        tx_type = request.args.get("type", "")
        category = request.args.get("category", "")
        q = request.args.get("q", "").strip()
        sql, params = "SELECT * FROM transactions WHERE user_id = ?", [g.user["id"]]
        if month:
            sql += " AND substr(date, 1, 7) = ?"; params.append(month)
        if tx_type in ("income", "expense"):
            sql += " AND type = ?"; params.append(tx_type)
        if category:
            sql += " AND category = ?"; params.append(category)
        if q:
            sql += " AND description LIKE ?"; params.append(f"%{q}%")
        sql += " ORDER BY date DESC, id DESC LIMIT 300"
        rows = db.get_db().execute(sql, params).fetchall()
        months = sorted({t["date"][:7] for t in all_transactions()}, reverse=True)
        inc = sum(r["amount"] for r in rows if r["type"] == "income")
        exp = sum(r["amount"] for r in rows if r["type"] == "expense")
        return render_template("transactions.html", rows=rows, months=months, f=request.args,
                               categories=analytics.EXPENSE_CATEGORIES + analytics.INCOME_CATEGORIES,
                               inc=inc, exp=exp)

    def parse_form():
        tx_type = request.form.get("type", "expense")
        if tx_type not in ("income", "expense"):
            tx_type = "expense"
        description = request.form.get("description", "").strip()[:120]
        category = request.form.get("category", "auto")
        try:
            amount = round(float(request.form.get("amount", "0")), 2)
            tx_date = datetime.strptime(request.form.get("date", ""), "%Y-%m-%d").date().isoformat()
        except ValueError:
            return None, "Please enter a valid amount and date."
        if amount <= 0:
            return None, "Amount must be greater than zero."
        if category == "auto":
            category = analytics.auto_categorize(description, tx_type)
        allowed = analytics.EXPENSE_CATEGORIES if tx_type == "expense" else analytics.INCOME_CATEGORIES
        if category not in allowed:
            return None, "Category does not match the transaction type."
        return dict(type=tx_type, amount=amount, category=category, description=description, date=tx_date), None

    @app.route("/transactions/add", methods=["GET", "POST"])
    @login_required
    def add_transaction():
        if request.method == "POST":
            data, error = parse_form()
            if error:
                flash(error, "error")
            else:
                db.get_db().execute(
                    "INSERT INTO transactions (user_id, type, amount, category, description, date) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (g.user["id"], data["type"], data["amount"], data["category"], data["description"], data["date"]))
                db.get_db().commit()
                flash(f"Saved under '{data['category']}'.", "success")
                return redirect(url_for("transactions"))
        return render_template("transaction_form.html", tx=None, today=date.today().isoformat(),
                               exp_cats=analytics.EXPENSE_CATEGORIES, inc_cats=analytics.INCOME_CATEGORIES)

    @app.route("/transactions/<int:tx_id>/edit", methods=["GET", "POST"])
    @login_required
    def edit_transaction(tx_id):
        tx = db.get_db().execute("SELECT * FROM transactions WHERE id = ? AND user_id = ?",
                                 (tx_id, g.user["id"])).fetchone()
        if tx is None:
            abort(404)
        if request.method == "POST":
            data, error = parse_form()
            if error:
                flash(error, "error")
            else:
                db.get_db().execute(
                    "UPDATE transactions SET type=?, amount=?, category=?, description=?, date=? "
                    "WHERE id=? AND user_id=?",
                    (data["type"], data["amount"], data["category"], data["description"], data["date"],
                     tx_id, g.user["id"]))
                db.get_db().commit()
                flash("Transaction updated.", "success")
                return redirect(url_for("transactions"))
        return render_template("transaction_form.html", tx=tx, today=date.today().isoformat(),
                               exp_cats=analytics.EXPENSE_CATEGORIES, inc_cats=analytics.INCOME_CATEGORIES)

    @app.route("/transactions/<int:tx_id>/delete", methods=["POST"])
    @login_required
    def delete_transaction(tx_id):
        db.get_db().execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (tx_id, g.user["id"]))
        db.get_db().commit()
        flash("Transaction deleted.", "success")
        return redirect(url_for("transactions"))

    @app.route("/export.csv")
    @login_required
    def export_csv():
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["date", "type", "category", "description", "amount"])
        for t in all_transactions():
            writer.writerow([t["date"], t["type"], t["category"], t["description"], t["amount"]])
        return Response(buf.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=finsight_transactions.csv"})

    # ------------------------------------------------------------------ #
    # monthly report
    # ------------------------------------------------------------------ #
    @app.route("/reports")
    @login_required
    def reports():
        rows = all_transactions()
        month = valid_month(request.args.get("month"))
        totals = analytics.monthly_totals(rows)
        cur = totals.get(month, {"income": 0.0, "expense": 0.0, "savings": 0.0})
        prev = totals.get(analytics.prev_month_key(month))
        days = analytics.daily_spending(rows, month)
        y, m = map(int, month.split("-"))
        n_days = (date(y + (m == 12), m % 12 + 1, 1) - date(y, m, 1)).days
        top = sorted([r for r in rows if r["date"][:7] == month and r["type"] == "expense"],
                     key=lambda r: r["amount"], reverse=True)[:5]
        months = sorted({r["date"][:7] for r in rows} | {date.today().strftime("%Y-%m")}, reverse=True)
        return render_template(
            "reports.html", month=month, months=months, cur=cur,
            rate=(cur["savings"] / cur["income"] * 100) if cur["income"] else 0,
            breakdown=analytics.category_breakdown(rows, month),
            income_breakdown=analytics.category_breakdown(rows, month, "income"),
            exp_change=analytics.percent_change(cur["expense"], prev["expense"]) if prev else None,
            inc_change=analytics.percent_change(cur["income"], prev["income"]) if prev else None,
            top=top, anomalies=analytics.detect_anomalies(rows, month),
            chart={"days": list(range(1, n_days + 1)), "values": [round(days.get(d, 0)) for d in range(1, n_days + 1)]})

    # ------------------------------------------------------------------ #
    # intelligence: prediction + tips
    # ------------------------------------------------------------------ #
    @app.route("/insights")
    @login_required
    def insights():
        rows = all_transactions()
        pred = analytics.predict_next_month(rows)
        cats = analytics.forecast_categories(rows)
        advice = analytics.build_tips(pred, cats)
        chart = None
        if pred:
            labels = [month_label(m) for m in pred["months_used"]] + [month_label(pred["target_month"])]
            n = len(pred["months_used"])
            chart = {
                "labels": labels,
                "income": [round(v) for v in pred["history_income"]] + [None],
                "expense": [round(v) for v in pred["history_expense"]] + [None],
                "f_expense": [None] * (n - 1) + [round(pred["history_expense"][-1]), round(pred["predicted_expense"])],
                "f_income": [None] * (n - 1) + [round(pred["history_income"][-1]), round(pred["predicted_income"])],
            }
        return render_template("insights.html", pred=pred, cats=cats, advice=advice, chart=chart)

    # ------------------------------------------------------------------ #
    # budgets
    # ------------------------------------------------------------------ #
    def budget_status(month):
        rows = db.get_db().execute("SELECT category, monthly_limit FROM budgets WHERE user_id = ?",
                                   (g.user["id"],)).fetchall()
        spent = {c["category"]: c["amount"] for c in analytics.category_breakdown(all_transactions(), month)}
        out = []
        for b in rows:
            s = spent.get(b["category"], 0.0)
            pct = s / b["monthly_limit"] * 100
            out.append({"category": b["category"], "limit": b["monthly_limit"], "spent": s, "percent": pct,
                        "state": "bad" if pct >= 100 else "warn" if pct >= 80 else "good"})
        return sorted(out, key=lambda x: x["percent"], reverse=True)

    @app.route("/budgets", methods=["GET", "POST"])
    @login_required
    def budgets():
        if request.method == "POST":
            category = request.form.get("category")
            action = request.form.get("action", "save")
            if category in analytics.EXPENSE_CATEGORIES:
                if action == "delete":
                    db.get_db().execute("DELETE FROM budgets WHERE user_id=? AND category=?", (g.user["id"], category))
                    flash("Budget removed.", "success")
                else:
                    try:
                        limit = float(request.form.get("limit", "0"))
                    except ValueError:
                        limit = 0
                    if limit <= 0:
                        flash("Enter a valid budget amount.", "error")
                        return redirect(url_for("budgets"))
                    db.get_db().execute(
                        "INSERT INTO budgets (user_id, category, monthly_limit) VALUES (?, ?, ?) "
                        "ON CONFLICT(user_id, category) DO UPDATE SET monthly_limit = excluded.monthly_limit",
                        (g.user["id"], category, limit))
                    flash("Budget saved.", "success")
                db.get_db().commit()
            return redirect(url_for("budgets"))
        month = date.today().strftime("%Y-%m")
        return render_template("budgets.html", status=budget_status(month), month=month,
                               categories=analytics.EXPENSE_CATEGORIES)

    return app


if __name__ == "__main__":
    create_app().run(debug=True)
