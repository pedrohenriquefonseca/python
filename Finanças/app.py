"""Analisador de gastos, orçamentos e (futuramente) patrimônio.

Portal Flask + SQLite. Foco atual: importar OFX, categorizar e acompanhar
orçamentos mensais por categoria em tempo hábil.
"""
import calendar
from datetime import date

from flask import Flask, flash, redirect, render_template, request, url_for

from categorizer import categorize, load_rules, recategorize_uncategorized
from db import get_db, init_db
from ofx_import import read_ofx_file

app = Flask(__name__)
app.secret_key = "troque-este-segredo-em-producao"


# ----------------------------------------------------------------------------- helpers
def current_month() -> str:
    return date.today().strftime("%Y-%m")


def month_bounds(month: str) -> tuple[str, str]:
    """Devolve (primeiro_dia, ultimo_dia) no formato YYYY-MM-DD para um 'YYYY-MM'."""
    year, mon = (int(p) for p in month.split("-"))
    last = calendar.monthrange(year, mon)[1]
    return f"{month}-01", f"{month}-{last:02d}"


def month_label(month: str) -> str:
    meses = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    year, mon = month.split("-")
    return f"{meses[int(mon)]}/{year}"


def pace_for_month(month: str) -> tuple[int, int]:
    """(dias decorridos, dias no mês). Para meses passados, decorridos == total."""
    year, mon = (int(p) for p in month.split("-"))
    days_in_month = calendar.monthrange(year, mon)[1]
    today = date.today()
    if (today.year, today.month) == (year, mon):
        return today.day, days_in_month
    if (year, mon) < (today.year, today.month):
        return days_in_month, days_in_month
    return 0, days_in_month  # mês futuro


def budget_for(conn, category_id: int, month: str) -> float | None:
    """Teto da categoria no mês: override do mês se existir, senão o padrão recorrente."""
    row = conn.execute(
        "SELECT amount FROM budgets WHERE category_id = ? AND month = ?",
        (category_id, month),
    ).fetchone()
    if row:
        return row["amount"]
    row = conn.execute(
        "SELECT amount FROM budgets WHERE category_id = ? AND month IS NULL",
        (category_id,),
    ).fetchone()
    return row["amount"] if row else None


# ----------------------------------------------------------------------------- dashboard
@app.route("/")
def dashboard():
    month = request.args.get("month", current_month())
    start, end = month_bounds(month)
    days_elapsed, days_total = pace_for_month(month)
    conn = get_db()

    # Gasto por categoria (apenas saídas: amount < 0).
    spent_rows = conn.execute(
        """
        SELECT c.id, c.name, c.color,
               COALESCE(SUM(CASE WHEN t.amount < 0 THEN -t.amount ELSE 0 END), 0) AS spent
        FROM categories c
        LEFT JOIN transactions t
            ON t.category_id = c.id AND t.posted_on BETWEEN ? AND ?
        WHERE c.kind = 'expense'
        GROUP BY c.id
        ORDER BY spent DESC
        """,
        (start, end),
    ).fetchall()

    budget_cards = []
    total_spent = total_budget = 0.0
    for row in spent_rows:
        budget = budget_for(conn, row["id"], month)
        spent = row["spent"]
        total_spent += spent
        if budget:
            total_budget += budget
        pct = (spent / budget * 100) if budget else None
        projected = (spent / days_elapsed * days_total) if days_elapsed else spent
        if budget:
            if spent > budget:
                status = "over"
            elif projected > budget:
                status = "pace_over"
            elif pct and pct >= 80:
                status = "warning"
            else:
                status = "ok"
        else:
            status = "nobudget"
        budget_cards.append({
            "category": row["name"], "color": row["color"],
            "spent": spent, "budget": budget, "pct": pct,
            "projected": projected, "remaining": (budget - spent) if budget else None,
            "status": status,
        })

    # Lançamentos sem categoria pedem atenção.
    uncategorized = conn.execute(
        "SELECT COUNT(*) AS n FROM transactions WHERE category_id IS NULL "
        "AND posted_on BETWEEN ? AND ?", (start, end),
    ).fetchone()["n"]

    income = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS v FROM transactions t "
        "JOIN categories c ON c.id = t.category_id "
        "WHERE c.kind = 'income' AND t.posted_on BETWEEN ? AND ?", (start, end),
    ).fetchone()["v"]

    conn.close()
    return render_template(
        "dashboard.html",
        month=month, month_label=month_label(month),
        prev_month=shift_month(month, -1), next_month=shift_month(month, +1),
        cards=budget_cards, total_spent=total_spent, total_budget=total_budget,
        days_elapsed=days_elapsed, days_total=days_total,
        uncategorized=uncategorized, income=income,
    )


def shift_month(month: str, delta: int) -> str:
    year, mon = (int(p) for p in month.split("-"))
    idx = year * 12 + (mon - 1) + delta
    return f"{idx // 12}-{idx % 12 + 1:02d}"


# ----------------------------------------------------------------------------- transações
@app.route("/transactions")
def transactions():
    month = request.args.get("month", current_month())
    start, end = month_bounds(month)
    conn = get_db()
    rows = conn.execute(
        """
        SELECT t.*, c.name AS category_name, c.color AS category_color, a.name AS account_name
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        LEFT JOIN accounts a ON a.id = t.account_id
        WHERE t.posted_on BETWEEN ? AND ?
        ORDER BY t.posted_on DESC, t.id DESC
        """, (start, end),
    ).fetchall()
    categories = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return render_template(
        "transactions.html", rows=rows, categories=categories,
        month=month, month_label=month_label(month),
        prev_month=shift_month(month, -1), next_month=shift_month(month, +1),
    )


@app.route("/transactions/<int:tx_id>/categorize", methods=["POST"])
def categorize_tx(tx_id: int):
    category_id = request.form.get("category_id") or None
    make_rule = request.form.get("make_rule")
    conn = get_db()
    conn.execute("UPDATE transactions SET category_id = ? WHERE id = ?", (category_id, tx_id))
    # Opcional: aprender uma regra a partir desta correção.
    if make_rule and category_id:
        tx = conn.execute("SELECT description FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        if tx:
            keyword = tx["description"].split()[0][:24] if tx["description"] else ""
            if keyword:
                conn.execute(
                    "INSERT INTO rules (pattern, category_id, priority) VALUES (?, ?, 50)",
                    (keyword, category_id),
                )
                flash(f"Regra criada: '{keyword}' → categoria.", "ok")
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("transactions"))


# ----------------------------------------------------------------------------- orçamentos
@app.route("/budgets", methods=["GET", "POST"])
def budgets():
    conn = get_db()
    if request.method == "POST":
        category_id = int(request.form["category_id"])
        amount = float(request.form["amount"].replace(",", "."))
        conn.execute(
            "INSERT INTO budgets (category_id, amount, month) VALUES (?, ?, NULL) "
            "ON CONFLICT(category_id, month) DO UPDATE SET amount = excluded.amount",
            (category_id, amount),
        )
        conn.commit()
        flash("Orçamento salvo.", "ok")
    rows = conn.execute(
        """
        SELECT c.id, c.name, c.color,
               (SELECT amount FROM budgets b WHERE b.category_id = c.id AND b.month IS NULL) AS budget
        FROM categories c WHERE c.kind = 'expense' ORDER BY c.name
        """
    ).fetchall()
    conn.close()
    return render_template("budgets.html", rows=rows)


# ----------------------------------------------------------------------------- import OFX
@app.route("/import", methods=["GET", "POST"])
def import_ofx():
    conn = get_db()
    accounts = conn.execute("SELECT * FROM accounts ORDER BY name").fetchall()
    if request.method == "POST":
        account_id = int(request.form["account_id"])
        file = request.files.get("ofx_file")
        if not file or not file.filename:
            flash("Selecione um arquivo OFX.", "error")
            return redirect(url_for("import_ofx"))

        txns = read_ofx_file(file.read())
        rules = load_rules(conn)
        inserted = skipped = 0
        for t in txns:
            category_id = categorize(t.description, rules)
            try:
                conn.execute(
                    """INSERT INTO transactions
                       (account_id, fitid, posted_on, amount, description, raw_memo, category_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (account_id, t.fitid, t.posted_on, t.amount,
                     t.description, t.raw_memo, category_id),
                )
                inserted += 1
            except Exception:
                # UNIQUE(account_id, fitid) violado = lançamento já importado.
                skipped += 1
        conn.commit()
        conn.close()
        flash(f"Importados {inserted} lançamentos novos. {skipped} já existiam (ignorados).", "ok")
        return redirect(url_for("dashboard"))

    conn.close()
    return render_template("import.html", accounts=accounts)


# ----------------------------------------------------------------------------- contas
@app.route("/accounts", methods=["GET", "POST"])
def accounts():
    conn = get_db()
    if request.method == "POST":
        conn.execute(
            "INSERT INTO accounts (name, type, bank) VALUES (?, ?, ?)",
            (request.form["name"], request.form["type"], request.form.get("bank", "")),
        )
        conn.commit()
        flash("Conta criada.", "ok")
    rows = conn.execute("SELECT * FROM accounts ORDER BY name").fetchall()
    conn.close()
    return render_template("accounts.html", rows=rows)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5005)
