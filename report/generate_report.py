"""
Generates FinSight_Training_Report.pdf  (A4, 1.5" binding margin, TOC + Table of Figures).

Edit the CONFIG block below, then run:   python report/generate_report.py
Needs: reportlab, matplotlib, numpy, scikit-learn  (pip install -r requirements-report.txt)
"""
import os
import sqlite3
import sys
import unittest

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, PageBreak, PageTemplate,
                                Paragraph, Preformatted, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import analytics  # noqa: E402
import diagrams  # noqa: E402

# ----------------------------- CONFIG ------------------------------------ #
CONFIG = dict(
    title="FinSight – Personal Finance & Expense Intelligence System",
    short_title="FINSIGHT – PERSONAL FINANCE & EXPENSE INTELLIGENCE SYSTEM",
    student="Lakshay Bansal", roll="210280071",
    guide="Dr Swati Bansal", guide_role="DTPI",
    hod="Dr. Paramjit Singh",
    university="MAHARAJA RANJIT SINGH PUNJAB TECHNICAL UNIVERSITY",
    degree="B.TECH", branch="COMPUTER SCIENCE & ENGINEERING",
    department="DEPARTMENT OF COMPUTER SCIENCE & ENGINEERING",
    college_line1="GIANI ZAIL SINGH CAMPUS COLLEGE OF ENGINEERING",
    college_line2="& TECHNOLOGY, MRSPTU, BATHINDA-151001",
    month_year="NOVEMBER 2026",
    output=os.path.join(ROOT, "FinSight_Training_Report.pdf"),
)
SHOTS = os.path.join(ROOT, "docs", "screenshots")
DIAG = os.path.join(HERE, "diagrams")
LOGO = os.path.join(HERE, "assets", "university_logo.png")
DB = os.path.join(ROOT, "instance", "finsight.db")

# ----------------------------- styles ------------------------------------ #
F, FB, FI = "Times-Roman", "Times-Bold", "Times-Italic"
S = dict(
    body=ParagraphStyle("body", fontName=F, fontSize=12, leading=18, alignment=TA_JUSTIFY, spaceAfter=7),
    bullet=ParagraphStyle("bullet", fontName=F, fontSize=12, leading=17, alignment=TA_JUSTIFY, leftIndent=18,
                          bulletIndent=4, spaceAfter=4),
    h1=ParagraphStyle("H1", fontName=FB, fontSize=18, leading=22, alignment=TA_CENTER, spaceAfter=16),
    h2=ParagraphStyle("H2", fontName=FB, fontSize=14, leading=18, spaceBefore=10, spaceAfter=7),
    h3=ParagraphStyle("H3", fontName=FB, fontSize=12.5, leading=16, spaceBefore=6, spaceAfter=5),
    caption=ParagraphStyle("Caption", fontName=FI, fontSize=11, leading=14, alignment=TA_CENTER, spaceBefore=4,
                           spaceAfter=10),
    code=ParagraphStyle("code", fontName="Courier", fontSize=8.2, leading=10.4, backColor=colors.HexColor("#f3f4f6"),
                        borderPadding=6, spaceBefore=4, spaceAfter=10),
    cell=ParagraphStyle("cell", fontName=F, fontSize=10.5, leading=13),
    cellb=ParagraphStyle("cellb", fontName=FB, fontSize=10.5, leading=13),
    center=ParagraphStyle("center", fontName=F, fontSize=12, leading=18, alignment=TA_CENTER),
    tocl0=ParagraphStyle("tocl0", fontName=FB, fontSize=11.5, leading=15, leftIndent=0),
    tocl1=ParagraphStyle("tocl1", fontName=F, fontSize=11, leading=13.6, leftIndent=18),
    tocl2=ParagraphStyle("tocl2", fontName=F, fontSize=10.5, leading=13, leftIndent=36),
    tof=ParagraphStyle("tof", fontName=F, fontSize=11, leading=15, leftIndent=0),
)
FIG = [0, 0]   # chapter, counter


class Doc(BaseDocTemplate):
    def __init__(self, path, **kw):
        super().__init__(path, pagesize=A4, leftMargin=38 * mm, rightMargin=25 * mm, topMargin=25 * mm,
                         bottomMargin=24 * mm, title=CONFIG["title"], author=CONFIG["student"], **kw)
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=self.draw_footer)])

    def draw_footer(self, canv, doc):
        if doc.page > 1:
            canv.setFont(F, 11)
            canv.drawCentredString(A4[0] / 2 + 6 * mm, 13 * mm, str(doc.page - 1))

    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph):
            name = fl.style.name
            text = fl.getPlainText()
            if name in ("H1", "H2", "H3"):
                level = int(name[1]) - 1
                key = f"h{id(fl)}"
                self.canv.bookmarkPage(key)
                self.notify("TOCEntry", (level, text, self.page - 1, key))
            elif name == "Caption" and text.startswith("Fig"):
                self.notify("TOFEntry", (0, text, self.page - 1))


class TableOfFigures(TableOfContents):
    def notify(self, kind, stuff):
        if kind == "TOFEntry":
            self.addEntry(*stuff)


# ----------------------------- helpers ----------------------------------- #
def P(t, style="body"):
    return Paragraph(t, S[style])


def H1(t):
    return [PageBreak(), P(t, "h1")]


def H2(t):
    return P(t, "h2")


def H3(t):
    return P(t, "h3")


def BL(items):
    return [Paragraph(i, S["bullet"], bulletText="•") for i in items]


def fig(path, caption, width=147 * mm):
    from PIL import Image as PI
    w, h = PI.open(path).size
    width = min(width, 147 * mm)
    height = width * h / w
    if height > 175 * mm:
        height, width = 175 * mm, 175 * mm * w / h
    FIG[1] += 1
    return KeepTogether([Image(path, width=width, height=height), P(f"Fig {FIG[0]}.{FIG[1]}. {caption}", "caption")])


def table(data, widths, header=True, align_last_center=False):
    rows = [[Paragraph(str(c), S["cellb"] if (header and i == 0) else S["cell"]) for c in r] for i, r in enumerate(data)]
    t = Table(rows, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#6b7280")), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e5e7eb")))
    t.setStyle(TableStyle(st))
    return [t, Spacer(1, 10)]


def inr(v):
    return f"Rs. {v:,.0f}"


# ----------------------------- live numbers ------------------------------ #
def live_numbers():
    out = {"ok": False}
    if not os.path.exists(DB):
        return out
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    uid = con.execute("SELECT id FROM users WHERE email='demo@finsight.app'").fetchone()
    if not uid:
        return out
    rows = [dict(r) for r in con.execute("SELECT * FROM transactions WHERE user_id=? ORDER BY date", (uid[0],))]
    totals = analytics.monthly_totals(rows)
    pred = analytics.predict_next_month(rows)
    cats = analytics.forecast_categories(rows)
    tips = analytics.build_tips(pred, cats)
    # back-test: forecast each of the last 3 completed months using only the months before it
    from datetime import date
    cur = date.today().strftime("%Y-%m")
    done = [m for m in totals if m < cur]
    back = []
    for m in done[-3:]:
        idx = done.index(m)
        hist = done[max(0, idx - 6):idx]
        p, _, _ = analytics.forecast_series([totals[x]["expense"] for x in hist])
        a = totals[m]["expense"]
        back.append((m, p, a, abs(p - a) / a * 100))
    out.update(ok=True, n=len(rows), months=len(totals), first=list(totals)[0], last=list(totals)[-1], pred=pred,
               cats=cats, tips=tips, back=back, totals=totals)
    return out


HELD_OUT = [("Dominos pizza with friends", "Food & Dining"), ("Ola cab to airport", "Transport"),
            ("Apollo pharmacy", "Health"), ("Spotify premium", "Entertainment"), ("Flipkart shoes", "Shopping"),
            ("IRCTC train ticket", "Transport"), ("Monthly wifi bill", "Bills & Utilities"),
            ("Dmart vegetables", "Groceries"), ("Gym membership", "Health"), ("Goibibo hotel booking", "Travel"),
            ("Myntra clothes", "Shopping"), ("Coaching fees", "Education"), ("Starbucks coffee", "Food & Dining"),
            ("Blinkit milk", "Groceries"), ("Hostel rent", "Rent"), ("Recharge Airtel", "Bills & Utilities"),
            ("Petrol pump", "Transport"), ("Concert tickets", "Entertainment"), ("Doctor consultation", "Health"),
            ("Tuition fees", "Education")]


def run_tests():
    suite = unittest.defaultTestLoader.discover(os.path.join(ROOT, "tests"))
    res = unittest.TestResult()
    suite.run(res)
    bad = {str(t[0]).split(" ")[0] for t in res.failures + res.errors}
    return res.testsRun, bad


# ----------------------------- content ----------------------------------- #
def build():
    N = live_numbers()
    diagrams.architecture(); diagrams.dfd0(); diagrams.er(); diagrams.flow()
    tests_run, failed = run_tests()
    held_ok = sum(1 for d, c in HELD_OUT if analytics.auto_categorize(d) == c)
    c = CONFIG
    s = []

    # ---- cover + title page ----
    def cover():
        out = [Spacer(1, 22 * mm), P("<b>TRAINING REPORT</b>", "center"), P("On", "center"),
               Paragraph(f"<b>{c['short_title']}</b>", ParagraphStyle("t", parent=S["center"], fontSize=19, leading=25)),
               Spacer(1, 6),
               P(f"Submitted to {c['university']} in partial fulfilment of the requirement for the award of the degree of", "center"),
               Spacer(1, 6), P(f"<b>{c['degree']}</b>", "center"), P("<b>In</b>", "center"), P(f"<b>{c['branch']}</b>", "center"),
               Spacer(1, 14)]
        t = Table([[Paragraph("<b>Submitted By</b>", S["body"]), Paragraph("<b>Submitted To</b>", S["body"])],
                   [Paragraph(c["student"], S["body"]), Paragraph(c["guide"], S["body"])],
                   [Paragraph(f"({c['roll']})", S["body"]), Paragraph(c["guide_role"], S["body"])]],
                  colWidths=[70 * mm, 55 * mm])
        t.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("TOPPADDING", (0, 0), (-1, -1), 0),
                               ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
        out += [t, Spacer(1, 14)]
        if os.path.exists(LOGO):
            out += [Image(LOGO, width=40 * mm, height=40 * mm * 0.65 if False else 40 * mm * 0.93)]
        out += [Spacer(1, 12), P(f"<b>{c['department']}</b>", "center"),
                Paragraph(f"<b>{c['college_line1']}<br/>{c['college_line2']}</b>", ParagraphStyle("c", parent=S["center"], fontSize=13.5, leading=19)),
                Spacer(1, 10), P(f"<b>{c['month_year']}</b>", "center")]
        return out

    s += cover() + [PageBreak()] + cover()

    # ---- preface / acknowledgement / declaration ----
    s += [PageBreak(), P("<b>PREFACE</b>", "h1"),
          P("Practical training is an integral part of the B.Tech programme. It gives every student a chance to move beyond "
            "classroom theory and build something that works for real users. This report records the practical project "
            "carried out during the 8<super>th</super> semester of B.Tech in Computer Science &amp; Engineering."),
          P(f"The project, <b>{c['title']}</b>, is a full-stack web application written in Python. It helps a person "
            "record daily income and expenses, automatically categorises spending, produces monthly financial reports and "
            "predicts the possible savings of the coming month using a machine-learning model."),
          P("While working on this project I learnt how a complete product is designed - from requirement analysis, database "
            "design and secure authentication to data analytics, testing and deployment. Every day of the work was an "
            "experience in itself, an experience which theoretical study alone cannot provide.")]
    s += [PageBreak(), P("<b>ACKNOWLEDGEMENT</b>", "h1"),
          P("It is a pleasure to be indebted to the various people who directly or indirectly contributed to the development "
            "of this work and who influenced my thinking, behaviour and acts during the course of study."),
          P(f"I express my sincere gratitude to {c['hod']}, worthy Head of the Department, and to {c['guide']}, "
            "Department Training &amp; Placement In-charge, for providing me an opportunity to undertake this project and for "
            "their constant encouragement and guidance."),
          P("I am also thankful to all the faculty members of the Department of Computer Science &amp; Engineering for their "
            "support, cooperation and motivation during the project."),
          P("Lastly, I would like to thank the almighty and my parents for their moral support, and my friends with whom I "
            "shared my day-to-day experience and who gave me many suggestions that improved the quality of my work."),
          Spacer(1, 18), P(f"<b>{c['student']}</b><br/>({c['roll']})")]
    s += [PageBreak(), P("<b>CANDIDATE’S DECLARATION</b>", "h1"),
          P(f"I, {c['student']}, Roll. No. {c['roll']}, B.Tech (Semester-VIII) of the Giani Zail Singh Campus College of "
            "Engineering &amp; Technology, Maharaja Ranjit Singh Punjab Technical University, Bathinda hereby declare that "
            f"the Training Report entitled “{c['title']}” is an original work and the data provided in the study is "
            "authentic to the best of my knowledge. This report has not been submitted to any other Institute for the "
            "award of any other degree."),
          Spacer(1, 18), P(f"<b>{c['student']}</b><br/>({c['roll']})")]

    # ---- TOC + TOF ----
    toc = TableOfContents()
    toc.levelStyles = [S["tocl0"], S["tocl1"], S["tocl2"]]
    toc.dotsMinLevel = 0
    s += [PageBreak(), P("<b>Table of Contents</b>", "h1"), toc]
    tof = TableOfFigures()
    tof.levelStyles = [S["tof"]]
    tof.dotsMinLevel = 0
    s += [PageBreak(), P("<b>Table of Figures</b>", "h1"), tof]

    # =================== CH 1 ===================
    FIG[:] = [1, 0]
    s += H1("1. Introduction to the Project")
    s += [H2("1.1. Introduction"),
          P("Money management is a skill that almost every person needs but very few practise in a systematic way. Most "
            "students and young professionals know roughly how much they earn, but they cannot say where the money goes at "
            "the end of the month. Small daily payments - a coffee, a cab ride, an online order, a subscription - look "
            "harmless one by one, yet together they decide whether a person saves or runs short before the next salary."),
          P("<b>FinSight</b> is a web-based Personal Finance &amp; Expense Intelligence System built with Python and the Flask "
            "framework. It turns raw income and expense entries into meaningful information: where the money was spent, how "
            "this month compares with the previous one, which category is growing too fast, and how much the user can "
            "probably save next month if the present pattern continues."),
          H2("1.2. Problem Statement"),
          P("Existing methods of tracking expenses have several drawbacks:")]
    s += BL(["Paper notebooks and memory-based tracking are inaccurate and are rarely maintained for more than a few weeks.",
             "Spreadsheets need manual formulas and manual categorisation of every entry, which is boring and error-prone.",
             "Many mobile applications only <i>store</i> records and do not analyse them; they cannot tell the user what is likely to happen in the future.",
             "Users have no early warning when a category is about to cross its budget or when an unusually large expense appears."])
    s += [P("There is therefore a need for a simple, secure and intelligent system that records transactions quickly, organises "
            "them automatically and gives forward-looking advice. FinSight is designed to fill this gap."),
          H2("1.3. Objective of the Project"),
          P("The main objective of FinSight is to build a full-stack, data-driven personal finance platform that tracks "
            "income and expenses and helps the user take better financial decisions.")]
    s += BL(["<b>Expense and Income Tracking:</b> allow users to add, edit, delete, search and filter daily transactions.",
             "<b>Automatic Categorisation:</b> detect the category (food, transport, rent, salary, etc.) from the text description of a transaction.",
             "<b>Monthly Financial Reports:</b> present income, expense, savings, category-wise split, top expenses and month-over-month change.",
             "<b>Savings Prediction:</b> use Linear Regression on past months to forecast the next month’s income, expense and savings.",
             "<b>Budget Control:</b> let users set monthly limits per category and warn them as the limit is approached.",
             "<b>Security and Privacy:</b> keep every user’s data private using hashed passwords, sessions and CSRF protection.",
             "<b>Simple Deployment:</b> keep the project light (SQLite, Flask) so that it can be run locally or deployed on a free cloud platform."])
    s += [H2("1.4. Features of the Project")]
    s += BL(["<b>Secure Registration and Login</b> with password hashing and session handling.",
             "<b>Interactive Dashboard</b> showing current-month income, expense, savings, savings rate, 6-month income vs expense chart, category doughnut chart, recent transactions and budget alerts.",
             "<b>Transaction Management</b> with filters (month, type, category, text search) and one-click CSV export.",
             "<b>Smart Auto-Detect Category</b> - the user only types a description such as “Swiggy dinner”; the system selects “Food &amp; Dining”.",
             "<b>Monthly Report</b> with category-wise percentage bars, daily spending chart, top 5 expenses, income sources and unusual-expense alerts.",
             "<b>Prediction and Insights</b> page with next-month forecast, trend chart, category-wise forecast table, confidence level and personalised suggestions.",
             "<b>Budgets</b> with progress bars that turn amber at 80% and red at 100%.",
             "<b>Responsive Design</b> that works on laptops, tablets and mobile phones, with Indian-style currency formatting (Rs. 12,34,567)."])
    s += [H2("1.5. Scope and Limitations"),
          P("FinSight is meant for personal use. Transactions are entered manually (or imported later through CSV in future "
            "versions); the system does not connect to bank accounts. Predictions are statistical estimates based on the "
            "history available - the more months of data a user has, the better the forecast. With fewer than three months of "
            "data the system falls back to a simple average and clearly reports a low confidence level."),
          H2("1.6. Modules of the Project"),
          P("The project is divided into interconnected modules, each handling one part of the functionality.")]
    mods = [("1.6.1. Authentication Module", ["Registers new users and logs them in using email and password.", "Stores only salted password hashes (Werkzeug) and protects every form with a CSRF token.", "Restricts every page except login and register to authenticated users."]),
            ("1.6.2. Dashboard Module", ["Shows a one-screen summary of the current month.", "Draws charts using a small custom JavaScript canvas library (no external dependency).", "Displays the four most critical budget alerts."]),
            ("1.6.3. Transaction Module", ["Create, read, update and delete (CRUD) operations for income and expense records.", "Server-side validation of amount, date, type and category.", "Search, filters and CSV export."]),
            ("1.6.4. Auto-Categorisation Module", ["Keyword-based classifier with about 130 keywords across 10 expense and 5 income categories.", "Uses whole-word matching so that “bus” does not match “business”.", "Falls back to “Other” / “Other Income” when nothing matches."]),
            ("1.6.5. Monthly Report Module", ["Aggregates transactions by month and category.", "Computes savings, savings rate and percentage change compared with the previous month.", "Flags unusual expenses using the mean + 2 standard deviations rule."]),
            ("1.6.6. Prediction and Insights Module", ["Forecasts next month’s income and expense using Linear Regression (scikit-learn).", "Forecasts every expense category using a weighted moving average.", "Generates rule-based suggestions: savings-rate check, 50/30/20 rule, fastest growing category, emergency-fund target."]),
            ("1.6.7. Budget Module", ["Lets the user define a monthly limit for each expense category.", "Compares the limit with the current month’s spending and colours the progress bar green, amber or red."])]
    for t, b in mods:
        s += [H3(t)] + BL(b)

    # =================== CH 2 ===================
    FIG[:] = [2, 0]
    s += H1("2. System Analysis and Design")
    s += [H2("2.1. Requirement Analysis"), H3("Functional Requirements")]
    s += BL(["The system shall allow a user to create an account and log in.",
             "The system shall allow a user to add income and expense transactions with date, amount, description and category.",
             "The system shall automatically suggest a category from the description.",
             "The system shall allow editing, deleting, searching and filtering of transactions.",
             "The system shall generate a monthly report for any month that has data.",
             "The system shall predict the next month’s income, expense and savings.",
             "The system shall allow budgets to be set and shall show how much of each budget is used.",
             "The system shall allow the user to export all transactions as a CSV file."])
    s += [H3("Non-Functional Requirements")]
    s += BL(["<b>Security:</b> passwords are never stored in plain text; every state-changing request is CSRF protected; users can access only their own records.",
             "<b>Usability:</b> a transaction can be added in less than 15 seconds; the interface is responsive on small screens.",
             "<b>Performance:</b> every page loads in well under one second for thousands of records because queries are indexed on (user_id, date).",
             "<b>Maintainability:</b> analytics code is separated from web code, which makes it testable.",
             "<b>Portability:</b> runs on Windows, Linux and macOS with only Python installed."])
    s += [H2("2.2. Hardware and Software Requirements")]
    s += table([["Component", "Requirement"],
                ["Processor / RAM", "Any dual-core processor, 2 GB RAM or more"],
                ["Operating System", "Windows 11 / Linux / macOS"],
                ["Language", "Python 3.10 or above"],
                ["Framework and Libraries", "Flask, NumPy, scikit-learn, Gunicorn (production server)"],
                ["Database", "SQLite 3 (bundled with Python)"],
                ["Browser", "Any modern browser (Chrome, Edge, Firefox, Safari)"],
                ["Editor / Tools", "Visual Studio Code, Git, GitHub"]], [50, 75])
    s += [H2("2.3. System Architecture"),
          P("FinSight follows a three-layer architecture. The <b>presentation layer</b> consists of HTML pages produced by "
            "Jinja2 templates, CSS and a small JavaScript file that draws the charts. The <b>application layer</b> is the "
            "Flask application that receives requests, validates input and decides which page or action to run. The "
            "<b>intelligence and data layer</b> contains the analytics engine (categoriser, report calculations, prediction "
            "model, suggestion rules) and the SQLite database."),
          fig(os.path.join(DIAG, "architecture.png"), "Three-layer architecture of FinSight", 120 * mm),
          H2("2.4. Data Flow Diagram (Level 0)"),
          P("The context diagram below shows that the user interacts with a single system. The user supplies income and "
            "expense entries and budget limits; the system returns reports, charts, forecasts and suggestions. All records "
            "are stored in and read from the SQLite data store."),
          fig(os.path.join(DIAG, "dfd0.png"), "Level 0 Data Flow Diagram", 125 * mm),
          H2("2.5. Database Design"),
          P("The database has three tables. The <b>users</b> table holds account information. The <b>transactions</b> table "
            "stores every income or expense record and is linked to its owner with a foreign key. The <b>budgets</b> table "
            "stores one monthly limit per category per user; a UNIQUE constraint on (user_id, category) guarantees that "
            "there is never more than one limit for the same category. CHECK constraints make sure the transaction "
            "type is either ‘income’ or ‘expense’ and that amounts are positive. An index on (user_id, date) keeps monthly "
            "queries fast."),
          fig(os.path.join(DIAG, "er.png"), "Entity-Relationship diagram (database schema)", 115 * mm)]
    s += table([["Table", "Important columns", "Purpose"],
                ["users", "id, name, email (unique), password_hash", "Stores registered users with hashed passwords"],
                ["transactions", "id, user_id, type, amount, category, description, date", "Every income or expense entry of a user"],
                ["budgets", "id, user_id, category, monthly_limit", "Monthly spending limit per category"]], [28, 55, 42])
    s += [H2("2.6. Project Folder Structure"),
          Preformatted(
              "finsight/\n"
              "|-- app.py                # Flask application, routes, validation\n"
              "|-- analytics.py          # categoriser, reports, ML forecast, tips\n"
              "|-- db.py                 # SQLite connection + schema\n"
              "|-- seed_demo.py          # creates 8 months of demo data\n"
              "|-- requirements.txt      # Flask, NumPy, scikit-learn, Gunicorn\n"
              "|-- Procfile              # command used by cloud platforms\n"
              "|-- templates/            # Jinja2 pages (dashboard, reports, ...)\n"
              "|-- static/css/style.css  # responsive styling\n"
              "|-- static/js/charts.js   # bar, line and doughnut charts (canvas)\n"
              "|-- tests/                # 12 automated unit tests\n"
              "`-- report/               # generator of this report", S["code"])]

    # =================== CH 3 ===================
    FIG[:] = [3, 0]
    s += H1("3. Tools &amp; Technologies Used in the Project")
    tech = [("3.1. Python", "Python is a high-level, general-purpose programming language known for its readable syntax and rich ecosystem of libraries. In FinSight, Python is used for the web back-end, the database operations and the entire analytics and machine-learning engine, so one language covers the whole application."),
            ("3.2. Flask", "Flask is a lightweight Python micro-framework for building web applications. It provides routing, request handling, sessions and template rendering while leaving the choice of other components to the developer. FinSight uses Flask’s application-factory pattern, which also makes testing easy."),
            ("3.3. Jinja2", "Jinja2 is the template engine bundled with Flask. It allows HTML pages to contain loops, conditions, filters and template inheritance. A common base template gives all pages the same navigation, while custom filters format money in Indian style (Rs. 12,34,567)."),
            ("3.4. HTML, CSS and JavaScript", "HTML defines the structure of the pages, CSS gives the responsive layout, cards and colours, and JavaScript adds interactivity such as the dynamic category list in the transaction form. A small JavaScript library written for this project draws bar, line and doughnut charts on the HTML5 canvas without any external dependency."),
            ("3.5. SQLite", "SQLite is a serverless, file-based relational database that ships with Python. It supports SQL, constraints, indexes and transactions, requires no installation and is ideal for a single-server personal application. Parameterised queries are used everywhere to prevent SQL injection."),
            ("3.6. NumPy", "NumPy provides fast n-dimensional arrays and numerical operations. It prepares the month-index and amount arrays that are given to the regression model."),
            ("3.7. scikit-learn", "scikit-learn is the most popular machine-learning library for Python. FinSight uses its <i>LinearRegression</i> model to learn the trend of monthly expenses and income and to forecast the next month, and the model’s R-squared score as a measure of confidence."),
            ("3.8. Werkzeug Security", "Werkzeug, the toolkit underneath Flask, offers <i>generate_password_hash</i> and <i>check_password_hash</i>. Passwords are salted and hashed so that even the database owner cannot read them."),
            ("3.9. CSRF Protection", "Cross-Site Request Forgery is an attack in which a malicious site makes a logged-in user’s browser send an unwanted request. FinSight generates a random token per session, embeds it in every form and rejects any POST request that does not carry the correct token."),
            ("3.10. Gunicorn", "Gunicorn is a production-grade WSGI HTTP server for Python. The Procfile starts the application with Gunicorn on cloud platforms such as Render."),
            ("3.11. unittest", "unittest is Python’s built-in testing framework. Twelve automated tests verify the analytics functions and the main web flows (login, add transaction, report pages, CSV export)."),
            ("3.12. Git and GitHub", "Git is a distributed version-control system and GitHub is a web platform that hosts Git repositories. The complete source code of FinSight is maintained on GitHub for version history, backup and sharing."),
            ("3.13. Visual Studio Code", "Visual Studio Code is a lightweight code editor with IntelliSense, debugging, an integrated terminal and Git integration. It was used as the IDE for the project on the Windows 11 platform.")]
    for h, t in tech:
        s += [H2(h), P(t)]

    # =================== CH 4 ===================
    FIG[:] = [4, 0]
    s += H1("4. Intelligence Engine and Core Algorithms")
    s += [P("All the logic that turns raw records into knowledge is written in a single module, <i>analytics.py</i>. "
            "The module is independent of Flask and the database - it receives a list of transactions and returns plain "
            "Python data - therefore every function can be unit tested."),
          H2("4.1. Automatic Expense Categorisation"),
          P("When the user leaves the category on “Auto-detect”, the description is converted to lower case and compared with "
            "a dictionary of keywords. For each allowed category, the number of keywords found as <i>whole words</i> is "
            "counted; the category with the highest count wins. If no keyword matches, the transaction is stored as "
            "“Other” (or “Other Income”). Whole-word matching is done with a regular-expression word boundary so that the "
            "keyword “bus” does not wrongly match the word “business”."),
          Preformatted(
              "def auto_categorize(description, tx_type='expense'):\n"
              "    text = description.lower()\n"
              "    allowed = EXPENSE_CATEGORIES if tx_type == 'expense' else INCOME_CATEGORIES\n"
              "    best, best_hits = None, 0\n"
              "    for category in allowed:\n"
              "        hits = sum(1 for kw in KEYWORDS[category]\n"
              "                   if re.search(rf'\\b{re.escape(kw)}\\b', text))\n"
              "        if hits > best_hits:\n"
              "            best, best_hits = category, hits\n"
              "    return best or ('Other' if tx_type == 'expense' else 'Other Income')", S["code"]),
          H2("4.2. Monthly Report Generation"),
          P("Transactions are grouped by the first seven characters of the ISO date (YYYY-MM). For every month the "
            "system computes <b>income</b>, <b>expense</b> and <b>savings = income - expense</b>. The <b>savings rate</b> is "
            "savings divided by income. The category breakdown gives each category’s amount and its percentage share of the "
            "month’s spending, and the month-over-month change is <i>(this month - previous month) / previous month x 100</i>."),
          H2("4.3. Savings Prediction using Linear Regression"),
          P("The system treats the monthly totals as a time series. Let <i>x</i> be the month index (0, 1, 2, ...) and "
            "<i>y</i> the expense (or income) of that month. Linear Regression finds the straight line "
            "<i>y = a + b·x</i> that minimises the sum of squared errors, where the slope is "
            "<i>b = sum[(x - x_mean)(y - y_mean)] / sum[(x - x_mean)<super>2</super>]</i> and the intercept is "
            "<i>a = y_mean - b·x_mean</i>. The next month’s value is obtained by substituting the next index in the line."),
          P("Only <b>completed months</b> are used for training because the current month is still incomplete and would "
            "make the line look as if spending were falling. At most the latest six months are used so that very old "
            "behaviour does not dominate. If fewer than three months exist, a regression line is not reliable, so the "
            "average is used instead. The <b>R-squared</b> value of the fitted line is reported as confidence: "
            "High (0.6 or above), Medium (0.3 to 0.6) or Low (below 0.3). "
            "<b>Predicted savings = predicted income - predicted expense.</b>"),
          fig(os.path.join(DIAG, "flow.png"), "Flow of the savings prediction", 80 * mm),
          Preformatted(
              "def forecast_series(values):\n"
              "    n = len(values)\n"
              "    if n == 0: return 0.0, 0.0, 'no-data'\n"
              "    if n < 3:  return mean(values), 0.0, 'average'\n"
              "    X = np.arange(n).reshape(-1, 1)\n"
              "    model = LinearRegression().fit(X, np.array(values))\n"
              "    pred = float(model.predict([[n]])[0])\n"
              "    return max(pred, 0.0), model.score(X, values), 'linear-regression'", S["code"]),
          H2("4.4. Category-wise Forecast"),
          P("For every expense category a <b>weighted moving average</b> of the last three months is calculated with weights "
            "1, 2 and 3 (the latest month has the highest weight). This responds quickly when a category starts rising "
            "or falling. The <i>trend</i> column compares last month’s spending with the average of the earlier months."),
          H2("4.5. Savings Suggestions (Rule Engine)"),
          P("The suggestion engine converts the forecast into human-readable advice using the following rules:")]
    s += BL(["<b>Savings-rate check:</b> 20% or more is “good”, 10-20% is a warning, below 10% is “bad”.",
             "<b>50/30/20 rule:</b> expenses are divided into <i>needs</i> (rent, groceries, bills, transport, health, education) and <i>wants</i> (dining out, shopping, entertainment, travel, other). If wants exceed 30% of income, a warning is shown.",
             "<b>Biggest expense:</b> tells the user which category takes the largest share of spending.",
             "<b>Fast-growing category:</b> a category whose last month is more than 15% above its earlier average (and at least Rs. 500) is highlighted.",
             "<b>Potential savings:</b> shows how much can be saved every month by trimming the “wants” categories by 15%.",
             "<b>Emergency fund:</b> target of three times the monthly expense and the number of months needed to reach it at the forecast savings."])
    s += [H2("4.6. Unusual-Expense Detection"),
          P("For each category the mean and the standard deviation of earlier expenses are calculated (at least four past "
            "records are required). A transaction of the selected month is flagged as unusual if its amount is greater "
            "than <b>mean + 2 x standard deviation</b> of that category. This simple statistical rule helps the user to "
            "notice a wrong entry, a fraudulent payment or a one-time big purchase."),
          H2("4.7. Security Measures")]
    s += BL(["Passwords are stored only as salted hashes; the login failure message does not reveal whether the email exists.",
             "Each POST request is verified with a random per-session CSRF token.",
             "All SQL statements are parameterised, which prevents SQL injection; Jinja2 auto-escapes output, which prevents cross-site scripting.",
             "Every query includes the logged-in user’s id, so one user can never read or modify another user’s data.",
             "The session is cleared on login and logout; the secret key is read from an environment variable in production."])

    # =================== CH 5 ===================
    FIG[:] = [5, 0]
    s += H1("5. Project Implementation")
    shot = lambda n: os.path.join(SHOTS, n)
    s += [H2("5.1. Login and Registration"),
          fig(shot("01_login.png"), "Login page of FinSight", 125 * mm),
          P("<b>Description:</b> New users create an account with name, email and password (minimum six characters). Existing "
            "users log in with email and password. Invalid credentials show an error message, and all other pages "
            "redirect to this page when the user is not logged in."),
          H2("5.2. Dashboard"),
          fig(shot("02_dashboard.png"), "Dashboard with summary cards, charts, recent transactions and budget alerts"),
          P("<b>Description:</b> The dashboard gives the current month at a glance: income, expenses, savings and the "
            "savings rate. The bar chart compares income and expense for the last six months, and the doughnut chart shows "
            "how this month’s spending is divided among categories. The lower part lists the most recent transactions and "
            "the budgets that are close to or beyond their limits."),
          H2("5.3. Transactions Page"),
          fig(shot("03_transactions.png"), "Transactions page with filters (month, type, category, search)"),
          P("<b>Description:</b> All records are shown in a table with colour-coded categories. The user can filter by "
            "month, type and category, search in the description, edit or delete a record, and export every transaction as a "
            "CSV file. The total income and expense of the filtered records are displayed above the table."),
          H2("5.4. Add Transaction with Auto-Detect Category"),
          fig(shot("04_add.png"), "Add transaction form - category left on Auto-detect"),
          P("<b>Description:</b> The user selects Expense or Income, enters the amount, description and date, and can keep the "
            "category on “Auto-detect”. For example, the description “Zomato biryani dinner” is saved under "
            "<i>Food &amp; Dining</i>. The category list changes automatically when the type is switched between expense and "
            "income. The server validates the amount (must be positive), the date format and that the category matches the type."),
          H2("5.5. Monthly Report"),
          fig(shot("05_report.png"), "Monthly report with category split, daily spending and unusual-expense alerts"),
          P("<b>Description:</b> The report shows total income, total expense, net savings and savings rate together with the "
            "percentage change compared with the previous month (green for a good change, red for a bad one). Category-wise "
            "progress bars, a day-by-day spending chart, the five biggest expenses, the income sources and any unusual "
            "expenses give a complete picture of the selected month. A drop-down allows the user to open any earlier month."),
          H2("5.6. Savings Prediction and Insights"),
          fig(shot("06_insights.png"), "Insights page - next-month forecast, trend chart, suggestions and category forecast"),
          P("<b>Description:</b> The top cards show the forecast month and the predicted income, expense and savings. The "
            "trend chart draws the actual history as solid lines and the forecast as dashed lines. The model name, the number "
            "of months used and the confidence level are shown below the chart. The “Smart suggestions” panel lists "
            "personalised advice and the ideal savings amount according to the 20% rule, while the table gives a "
            "category-wise forecast with a rising or falling trend arrow."),
          H2("5.7. Budgets"),
          fig(shot("07_budgets.png"), "Budget page - set monthly limits and track progress", 125 * mm),
          P("<b>Description:</b> The user selects an expense category and sets a monthly limit. The progress section "
            "compares the current month’s spending with each limit; the bar is green below 80%, amber from 80% and red at "
            "100% or more. The same information appears as alerts on the dashboard.")]

    # =================== CH 6 ===================
    FIG[:] = [6, 0]
    s += H1("6. Testing")
    s += [P("Testing was done at two levels. <b>Unit tests</b> check the analytics functions with known input and known "
            "output, and <b>integration tests</b> use Flask’s test client to simulate a real user registering, logging in, "
            "adding a transaction and opening every page. All tests use a temporary database, so the real data is never "
            "touched. The suite is run with the command <i>python -m unittest discover -s tests -v</i>."),
          ]
    desc = [("test_auto_categorize", "Descriptions such as ‘Swiggy dinner’, ‘Uber to office’ and ‘March salary’ get the correct category; ‘business class’ must not match the keyword ‘bus’."),
            ("test_monthly_totals", "Income, expense and savings of a month are calculated correctly."),
            ("test_linear_forecast_follows_trend", "For the series 1000, 2000, 3000, 4000 the forecast is 5000 and R-squared is above 0.99."),
            ("test_forecast_small_data_uses_average", "With fewer than 3 months the average is used; an empty series returns 0."),
            ("test_predict_next_month", "Four months of rising expense produce the correct target month, expense and savings."),
            ("test_month_keys", "Month arithmetic works across year boundaries (2025-12 to 2026-01 and back)."),
            ("test_anomaly", "A Rs. 9,000 shopping expense against a Rs. 1,000 average is flagged as unusual."),
            ("test_inr_format", "Currency is formatted in Indian style, e.g. Rs. 12,34,567."),
            ("test_requires_login", "Opening the dashboard without login redirects to the login page."),
            ("test_csrf_blocks_post", "A POST request without a CSRF token is rejected with HTTP 400."),
            ("test_full_flow", "Register, login, add an auto-categorised transaction and open dashboard, reports, insights, budgets and CSV export (HTTP 200)."),
            ("test_rejects_bad_amount", "A negative amount is rejected and nothing is saved.")]
    rows = [["No.", "Test case", "What is verified", "Result"]]
    for i, (n, d) in enumerate(desc, 1):
        rows.append([i, n, d, "Fail" if n in failed else "Pass"])
    s += table(rows, [10, 38, 63, 14])
    s += [P(f"<b>Result:</b> {tests_run} tests executed, {tests_run - len(failed)} passed, {len(failed)} failed.")]

    # =================== CH 7 ===================
    FIG[:] = [7, 0]
    s += H1("7. Results")
    s += [P("FinSight was evaluated with a demo user created by <i>seed_demo.py</i>, which generates realistic income and "
            "expense records with a gradual rise in lifestyle spending.")]
    if N["ok"]:
        p = N["pred"]
        s += table([["Measure", "Value"],
                    ["Transactions in demo data", f"{N['n']} records"],
                    ["Period covered", f"{N['months']} months ({N['first']} to {N['last']})"],
                    ["Predicted income (" + p["target_month"] + ")", inr(p["predicted_income"])],
                    ["Predicted expense", inr(p["predicted_expense"])],
                    ["Predicted savings", f"{inr(p['predicted_savings'])} ({p['predicted_savings_rate']:.0f}% of income)"],
                    ["Model / confidence", f"{p['method']} / {p['confidence']} (R-squared = {p['r2']:.2f})"],
                    ["Potential saving by trimming wants by 15%", inr(N['tips']['potential_savings']) + " per month"]],
                   [70, 55])
        s += [P("<b>Back-test of the expense forecast.</b> To check the model honestly, each of the last three completed "
                "months was forecast using only the months before it and compared with what really happened:")]
        bt = [["Month", "Forecast expense", "Actual expense", "Error"]]
        for m, f_, a_, e in N["back"]:
            bt.append([m, inr(f_), inr(a_), f"{e:.1f}%"])
        s += table(bt, [30, 38, 38, 19])
        avg = sum(e for *_, e in N["back"]) / len(N["back"])
        s += [P(f"The average absolute error is <b>{avg:.1f}%</b>. The R-squared value is low because monthly spending "
                "contains random day-to-day variation; this is why the application shows the confidence level instead of "
                "presenting the forecast as a certain fact.")]
    s += [P(f"<b>Categorisation accuracy.</b> The auto-categoriser was tried on a separate list of {len(HELD_OUT)} new "
            f"descriptions written independently of the demo data (for example “Ola cab to airport”, “Spotify premium”, "
            f"“Hostel rent”). It chose the correct category in <b>{held_ok} of {len(HELD_OUT)}</b> cases "
            f"({held_ok / len(HELD_OUT) * 100:.0f}%). This result should be read with care: the classifier is keyword based, "
            "so it works very well for common merchants and words that are in its dictionary, while descriptions with "
            "unknown words are stored as “Other” and can be changed by the user in one click. The dictionary can be "
            "extended easily, and a learning-based classifier is listed in the future scope.")]
    s += BL(["<b>Faster tracking:</b> automatic categorisation removes the most time-consuming step of manual entry.",
             "<b>Clear monthly picture:</b> the report answers “where did my money go?” in one screen.",
             "<b>Forward-looking advice:</b> the forecast and suggestions help the user to plan the next month instead of only reviewing the past.",
             "<b>Better control:</b> budget bars and unusual-expense alerts warn the user before overspending becomes a habit.",
             "<b>Reliable code:</b> all automated tests pass and every page is protected from unauthorised access and CSRF.",
             "<b>Low cost:</b> the application needs no paid service and can be hosted on a free cloud tier."])
    s += [P("Overall, FinSight converts a simple list of daily entries into a personal finance assistant that explains the "
            "past, warns about the present and estimates the future.")]

    # =================== CH 8 ===================
    s += H1("8. Future Scope")
    s += [P("FinSight provides a solid foundation, and many enhancements are possible:")]
    s += BL(["<b>Bank SMS / statement import:</b> read CSV or PDF statements and UPI messages so that entries are added automatically.",
             "<b>Better machine learning:</b> use seasonal models (e.g. festive-season spending) or a classifier such as Naive Bayes trained on the user’s corrected categories.",
             "<b>Receipt scanning:</b> extract amount and merchant from a photograph using OCR.",
             "<b>Savings goals:</b> let users define goals (laptop, trip, emergency fund) and track progress with projected completion dates.",
             "<b>Recurring transactions and reminders:</b> automatic entry of rent, EMI and subscriptions, with bill-due notifications by e-mail.",
             "<b>Shared / family accounts</b> and multi-currency support.",
             "<b>PDF report download</b> and monthly e-mail summaries.",
             "<b>Mobile application and PWA</b> for offline entry, and a PostgreSQL database for large-scale deployment."])

    # =================== CH 9 ===================
    s += H1("9. Conclusion")
    s += [P("FinSight – Personal Finance &amp; Expense Intelligence System is a full-stack Python web application that "
            "tracks daily income and expenses, categorises spending automatically, generates monthly financial reports and "
            "predicts the potential savings of the next month from the user’s own spending pattern. The system combines a "
            "clean and responsive interface with a testable analytics engine that uses Linear Regression, weighted moving "
            "averages and statistical rules."),
          P("By using Flask, SQLite, NumPy and scikit-learn the project remains simple to understand, easy to deploy and "
            "free of cost, yet it demonstrates real software-engineering practice: layered architecture, input validation, "
            "secure authentication, CSRF protection, automated testing and version control with GitHub."),
          P("During the development of this project I gained practical knowledge of web development, database design, data "
            "analytics, machine learning and deployment. The project shows that even a small, well-designed application "
            "can help people to understand their money better and to build the habit of saving. It also opens the door for "
            "future innovations in the field of personal FinTech.")]

    s += H1("References")
    s += BL(["Flask Documentation – https://flask.palletsprojects.com",
             "Jinja2 Documentation – https://jinja.palletsprojects.com",
             "Python sqlite3 module – https://docs.python.org/3/library/sqlite3.html",
             "scikit-learn: LinearRegression – https://scikit-learn.org",
             "NumPy Documentation – https://numpy.org/doc",
             "OWASP Cross-Site Request Forgery Prevention Cheat Sheet – https://owasp.org",
             "Werkzeug Security Utilities – https://werkzeug.palletsprojects.com",
             "Gunicorn Documentation – https://docs.gunicorn.org",
             "Warren, E. and Tyagi, A. W., <i>All Your Worth: The Ultimate Lifetime Money Plan</i> (50/30/20 budgeting rule)."])
    return s


def main():
    story = build()
    doc = Doc(CONFIG["output"])
    doc.multiBuild(story)
    print("Report written:", CONFIG["output"])


if __name__ == "__main__":
    main()
