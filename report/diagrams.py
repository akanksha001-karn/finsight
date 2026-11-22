"""Draws the architecture / DFD / ER / flow diagrams used in the report."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = os.path.join(os.path.dirname(__file__), "diagrams")
os.makedirs(OUT, exist_ok=True)
BLUE, GREEN, AMBER, GREY, PURPLE, RED = "#dbeafe", "#d1fae5", "#fef3c7", "#f1f5f9", "#ede9fe", "#fee2e2"


def box(ax, x, y, w, h, text, color=BLUE, fs=10, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
                                fc=color, ec="#334155", lw=1.3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", color="#0f172a", linespacing=1.35)


def arrow(ax, p1, p2, text=None, both=False, rad=0.0, fs=8.5, off=(0, 0.12)):
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="<|-|>" if both else "-|>", mutation_scale=14,
                                 lw=1.4, color="#1e293b", connectionstyle=f"arc3,rad={rad}"))
    if text:
        ax.text((p1[0] + p2[0]) / 2 + off[0], (p1[1] + p2[1]) / 2 + off[1], text, ha="center", fontsize=fs,
                color="#334155", style="italic")


def canvas(w, h):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(0, w); ax.set_ylim(0, h); ax.axis("off")
    return fig, ax


def architecture():
    fig, ax = canvas(8, 6.2)
    ax.add_patch(FancyBboxPatch((0.2, 4.6), 7.6, 1.4, boxstyle="round,pad=0.02", fc="#f8fafc", ec="#94a3b8", ls="--"))
    ax.text(0.4, 5.75, "PRESENTATION LAYER (Browser)", fontsize=8.5, color="#475569", fontweight="bold")
    box(ax, 0.5, 4.75, 2.1, 0.85, "HTML + Jinja2\nTemplates", BLUE)
    box(ax, 2.95, 4.75, 2.1, 0.85, "CSS\n(Responsive UI)", BLUE)
    box(ax, 5.4, 4.75, 2.1, 0.85, "JavaScript\nCanvas Charts", BLUE)

    ax.add_patch(FancyBboxPatch((0.2, 2.35), 7.6, 1.85, boxstyle="round,pad=0.02", fc="#f8fafc", ec="#94a3b8", ls="--"))
    ax.text(0.4, 3.95, "APPLICATION LAYER (Flask)", fontsize=8.5, color="#475569", fontweight="bold")
    box(ax, 0.5, 2.5, 1.65, 1.1, "Auth &\nSession\n(CSRF)", GREEN, 9)
    box(ax, 2.3, 2.5, 1.65, 1.1, "Transaction\nCRUD +\nCSV export", GREEN, 9)
    box(ax, 4.1, 2.5, 1.65, 1.1, "Reports &\nBudgets", GREEN, 9)
    box(ax, 5.9, 2.5, 1.65, 1.1, "Insights\n(Prediction)", GREEN, 9)

    ax.add_patch(FancyBboxPatch((0.2, 0.2), 7.6, 1.75, boxstyle="round,pad=0.02", fc="#f8fafc", ec="#94a3b8", ls="--"))
    ax.text(0.4, 1.7, "INTELLIGENCE + DATA LAYER", fontsize=8.5, color="#475569", fontweight="bold")
    box(ax, 0.5, 0.35, 5.0, 1.15, "analytics.py\nAuto-categoriser | Monthly totals | Linear Regression\nWeighted moving average | Tips engine | Anomaly detection", AMBER, 8.5)
    box(ax, 5.9, 0.35, 1.65, 1.15, "SQLite\nDatabase", PURPLE, 10, True)

    arrow(ax, (4.0, 4.75), (4.0, 4.2), both=True)
    arrow(ax, (3.0, 2.5), (3.0, 1.95), both=True)
    arrow(ax, (6.7, 2.5), (6.7, 1.95), both=True)
    arrow(ax, (5.5, 0.92), (5.9, 0.92), both=True)
    fig.savefig(f"{OUT}/architecture.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def dfd0():
    fig, ax = canvas(8, 3.8)
    box(ax, 0.2, 1.4, 1.6, 1.0, "USER", GREY, 11, True)
    ax.add_patch(plt.Circle((4.0, 1.9), 1.15, fc=GREEN, ec="#334155", lw=1.4))
    ax.text(4.0, 1.9, "FinSight\nFinance\nIntelligence\nSystem", ha="center", va="center", fontsize=10, fontweight="bold")
    box(ax, 6.2, 1.4, 1.6, 1.0, "SQLite\nData Store", PURPLE, 10, True)
    arrow(ax, (1.8, 2.25), (2.85, 2.25), "income / expense\nentries, budgets", fs=8, off=(0, 0.1))
    arrow(ax, (2.85, 1.55), (1.8, 1.55), "reports, charts,\nforecast, tips", fs=8, off=(0, -0.42))
    arrow(ax, (5.15, 2.25), (6.2, 2.25), "store / fetch", fs=8, off=(0, 0.1))
    arrow(ax, (6.2, 1.55), (5.15, 1.55), "records", fs=8, off=(0, -0.3))
    fig.savefig(f"{OUT}/dfd0.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def er():
    fig, ax = canvas(7.4, 5.3)

    def table(x, y, name, fields, color):
        w, rh = 2.6, 0.36
        h = rh * (len(fields) + 1)
        ax.add_patch(plt.Rectangle((x, y - h), w, h, fc="white", ec="#334155", lw=1.3))
        ax.add_patch(plt.Rectangle((x, y - rh), w, rh, fc=color, ec="#334155", lw=1.3))
        ax.text(x + w / 2, y - rh / 2, name, ha="center", va="center", fontweight="bold", fontsize=10)
        for i, f in enumerate(fields):
            ax.text(x + 0.1, y - rh * (i + 1.5), f, va="center", fontsize=8.3, family="monospace")

    table(0.2, 5.1, "users", ["PK id INTEGER", "name TEXT", "email TEXT UNIQUE", "password_hash TEXT", "created_at TEXT"], BLUE)
    table(4.2, 5.1, "transactions", ["PK id INTEGER", "FK user_id INTEGER", "type income/expense", "amount REAL (>0)",
                                     "category TEXT", "description TEXT", "date TEXT (ISO)", "created_at TEXT"], GREEN)
    table(0.2, 2.35, "budgets", ["PK id INTEGER", "FK user_id INTEGER", "category TEXT", "monthly_limit REAL"], AMBER)
    arrow(ax, (2.8, 4.2), (4.2, 4.2), "1 : N", fs=9, off=(0, 0.12))
    arrow(ax, (1.5, 2.95), (1.5, 2.35), "1 : N", fs=9, off=(0.45, -0.02))
    ax.text(3.0, 1.0, "UNIQUE (user_id, category) ensures one\nbudget per category for every user",
            fontsize=8.5, style="italic", color="#334155")
    fig.savefig(f"{OUT}/er.png", dpi=200, bbox_inches="tight"); plt.close(fig)


def flow():
    fig, ax = canvas(6.2, 8.4)
    box(ax, 1.6, 7.6, 3.0, 0.6, "Fetch user's transactions", BLUE, 9.5)
    box(ax, 1.6, 6.6, 3.0, 0.6, "Group by month (income, expense)", BLUE, 9.5)
    box(ax, 1.6, 5.6, 3.0, 0.6, "Use last 6 completed months", BLUE, 9.5)
    ax.add_patch(plt.Polygon([(3.1, 5.15), (4.4, 4.45), (3.1, 3.75), (1.8, 4.45)], fc=AMBER, ec="#334155", lw=1.3))
    ax.text(3.1, 4.45, "months >= 3 ?", ha="center", va="center", fontsize=9.5)
    box(ax, 0.1, 2.7, 2.4, 0.7, "Linear Regression\n(month index vs amount)", GREEN, 9)
    box(ax, 3.7, 2.7, 2.4, 0.7, "Simple average", GREEN, 9)
    box(ax, 1.6, 1.6, 3.0, 0.6, "Forecast income & expense", BLUE, 9.5)
    box(ax, 1.6, 0.6, 3.0, 0.6, "Savings = Income - Expense\n+ tips & confidence (R-squared)", PURPLE, 9)
    for a, b in [((3.1, 7.6), (3.1, 7.2)), ((3.1, 6.6), (3.1, 6.2)), ((3.1, 5.6), (3.1, 5.15))]:
        arrow(ax, a, b)
    arrow(ax, (2.2, 4.1), (1.3, 3.4), "Yes", off=(-0.3, 0.05))
    arrow(ax, (4.0, 4.1), (4.9, 3.4), "No", off=(0.3, 0.05))
    arrow(ax, (1.3, 2.7), (2.4, 2.2)); arrow(ax, (4.9, 2.7), (3.8, 2.2)); arrow(ax, (3.1, 1.6), (3.1, 1.2))
    fig.savefig(f"{OUT}/flow.png", dpi=200, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    architecture(); dfd0(); er(); flow(); print("diagrams ready")
