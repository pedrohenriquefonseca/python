"""Analisador de gastos, orçamentos e (futuramente) patrimônio.

Portal Flask + SQLite. Foco atual: importar OFX, categorizar e acompanhar
orçamentos mensais por categoria em tempo hábil.
"""
import calendar
from collections import defaultdict
from datetime import date

from flask import Flask, flash, redirect, render_template, request, url_for

from categorizer import categorize, load_rules, recategorize_uncategorized
from db import get_db, init_db, tx_fingerprint
from ofx_import import read_ofx_file

app = Flask(__name__)
app.secret_key = "troque-este-segredo-em-producao"

# Ícone (Tabler) fixo por categoria e por tipo de bem.
CATEGORY_ICONS = {
    "Moradia": "home", "Transporte": "car", "Alimentação": "tools-kitchen-2",
    "Mercado": "shopping-cart", "Saúde": "heartbeat", "Lazer": "movie",
    "Assinaturas": "repeat", "Salário": "cash", "Outros": "dots",
    "Transferência": "arrows-exchange",
}
ASSET_ICONS = {
    "Imóvel": "home", "Veículo": "car", "Investimento": "chart-line", "Outros": "diamond",
}


def cat_icon(name: str) -> str:
    return "ti ti-" + CATEGORY_ICONS.get(name, "tag")


def asset_icon(category: str) -> str:
    return "ti ti-" + ASSET_ICONS.get(category, "diamond")


app.jinja_env.globals.update(cat_icon=cat_icon, asset_icon=asset_icon)


@app.template_filter("brl")
def brl(v: float) -> str:
    """Formata em reais no padrão BR: 1.234.567,89."""
    s = f"{abs(v):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return ("-" if v < 0 else "") + s


@app.template_filter("kmil")
def kmil(v: float) -> str:
    """Compacta para milhares: 162110 -> 162,1k."""
    return f"{v / 1000:.1f}".replace(".", ",") + "k"


@app.template_filter("n0")
def n0(v: float) -> str:
    """Inteiro com separador de milhar BR: 7200 -> 7.200."""
    return f"{v:,.0f}".replace(",", ".")


def net_worth_parts() -> tuple[float, float, float]:
    """(saldo em bancos, total em bens, patrimônio líquido).
    Saldo em bancos = saldos iniciais + soma de todos os lançamentos."""
    conn = get_db()
    opening = conn.execute("SELECT COALESCE(SUM(opening_balance), 0) AS v FROM accounts").fetchone()["v"]
    moves = conn.execute("SELECT COALESCE(SUM(amount), 0) AS v FROM transactions WHERE ignored = 0").fetchone()["v"]
    # Crédito automático nas contas de destino das transferências (a perna de saída já está em 'moves').
    moves += conn.execute(
        "SELECT COALESCE(SUM(-amount), 0) AS v FROM transactions WHERE ignored = 0 AND transfer_to IS NOT NULL"
    ).fetchone()["v"]
    assets = conn.execute("SELECT COALESCE(SUM(value), 0) AS v FROM assets").fetchone()["v"]
    conn.close()
    bancos = opening + moves
    return bancos, assets, bancos + assets


@app.context_processor
def inject_net_worth():
    bancos, bens, total = net_worth_parts()
    return {"nw_bancos": bancos, "nw_bens": bens, "nw_total": total}


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


def month_short(month: str) -> str:
    """Rótulo curto para eixos de gráfico, ex.: 'jun/26'."""
    abbr = ["", "jan", "fev", "mar", "abr", "mai", "jun",
            "jul", "ago", "set", "out", "nov", "dez"]
    year, mon = month.split("-")
    return f"{abbr[int(mon)]}/{year[2:]}"


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
            ON t.category_id = c.id AND t.posted_on BETWEEN ? AND ? AND t.ignored = 0
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
        "AND ignored = 0 AND posted_on BETWEEN ? AND ?", (start, end),
    ).fetchone()["n"]

    income = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS v FROM transactions t "
        "JOIN categories c ON c.id = t.category_id "
        "WHERE c.kind = 'income' AND t.ignored = 0 AND t.posted_on BETWEEN ? AND ?", (start, end),
    ).fetchone()["v"]

    # Séries mensais dos gráficos da home.
    charts = build_charts(conn, month)

    # Top 3 estouros de orçamento do mês selecionado.
    overruns = sorted(
        ({"category": c["category"], "color": c["color"],
          "overrun": c["spent"] - c["budget"]}
         for c in budget_cards if c["budget"] and c["spent"] > c["budget"]),
        key=lambda x: x["overrun"], reverse=True,
    )[:3]
    over_h = _scaled_heights([o["overrun"] for o in overruns])
    for o, h in zip(overruns, over_h):
        o["h"] = h

    conn.close()
    return render_template(
        "dashboard.html",
        month=month, month_label=month_label(month),
        prev_month=shift_month(month, -1), next_month=shift_month(month, +1),
        cards=budget_cards, total_spent=total_spent, total_budget=total_budget,
        days_elapsed=days_elapsed, days_total=days_total,
        uncategorized=uncategorized, income=income,
        charts=charts, overruns=overruns,
    )


def shift_month(month: str, delta: int) -> str:
    year, mon = (int(p) for p in month.split("-"))
    idx = year * 12 + (mon - 1) + delta
    return f"{idx // 12}-{idx % 12 + 1:02d}"


def _scaled_heights(values: list[float], min_visible: float = 4.0) -> list[float]:
    """Converte valores em alturas 0–100% relativas ao máximo da série.
    Dá uma altura mínima visível a valores positivos para a barra não sumir."""
    mx = max(values) if values else 0
    out = []
    for v in values:
        if mx <= 0 or v <= 0:
            out.append(0.0)
        else:
            out.append(max(v / mx * 100, min_visible))
    return out


def build_charts(conn, month: str, n_months: int = 6) -> dict:
    """Séries mensais (gasto, receita, orçado) dos últimos n meses até `month`."""
    months = [shift_month(month, -i) for i in range(n_months - 1, -1, -1)]
    expense_cats = conn.execute(
        "SELECT id FROM categories WHERE kind = 'expense'"
    ).fetchall()

    gastos, receitas, orcados = [], [], []
    for m in months:
        start, end = month_bounds(m)
        gasto = conn.execute(
            "SELECT COALESCE(SUM(-t.amount), 0) AS v FROM transactions t "
            "JOIN categories c ON c.id = t.category_id "
            "WHERE c.kind = 'expense' AND t.ignored = 0 AND t.amount < 0 AND t.posted_on BETWEEN ? AND ?",
            (start, end),
        ).fetchone()["v"]
        receita = conn.execute(
            "SELECT COALESCE(SUM(t.amount), 0) AS v FROM transactions t "
            "JOIN categories c ON c.id = t.category_id "
            "WHERE c.kind = 'income' AND t.ignored = 0 AND t.posted_on BETWEEN ? AND ?",
            (start, end),
        ).fetchone()["v"]
        orcado = sum(b for b in (budget_for(conn, c["id"], m) for c in expense_cats) if b)
        gastos.append(gasto)
        receitas.append(receita)
        orcados.append(orcado)

    labels = [month_short(m) for m in months]

    # ---- Gráfico de linha "Fluxo mensal" (receita, gasto, orçado) ----
    # Coordenadas em viewBox 480x104; eixo de valor entre y=18 (topo) e y=74 (base = 0).
    W, x0, x1, top, base = 480, 20, 460, 18, 74
    n = len(months)
    xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(n)] if n > 1 else [x0]
    vmax = max(receitas + gastos + orcados + [1])

    def y_of(v):
        return base - (v / vmax) * (base - top)

    def fmt_cur(v):
        return "R$ " + f"{v:,.0f}".replace(",", ".")

    receita_pts = " ".join(f"{x:.0f},{y_of(v):.1f}" for x, v in zip(xs, receitas))
    gasto_pts = " ".join(f"{x:.0f},{y_of(v):.1f}" for x, v in zip(xs, gastos))
    orcado_pts = " ".join(f"{x:.0f},{y_of(v):.1f}" for x, v in zip(xs, orcados))

    flow = {
        "receita_pts": receita_pts, "gasto_pts": gasto_pts, "orcado_pts": orcado_pts,
        "receita_nodes": [{"x": round(x), "y": round(y_of(v), 1), "ly": round(y_of(v) - 6, 1),
                           "label": fmt_cur(v), "current": m == month}
                          for x, v, m in zip(xs, receitas, months)],
        "gasto_nodes": [{"x": round(x), "y": round(y_of(v), 1), "ly": round(y_of(v) + 10, 1),
                         "label": fmt_cur(v), "current": m == month}
                        for x, v, m in zip(xs, gastos, months)],
        "month_nodes": [{"x": round(x), "label": l, "current": m == month}
                        for x, l, m in zip(xs, labels, months)],
        "orcado_label": fmt_cur(orcados[-1]) if orcados else "R$ 0",
        "orcado_y": round(y_of(orcados[-1]) + 10, 1) if orcados else base,
    }

    return {"labels": labels, "flow": flow}


# ----------------------------------------------------------------------------- transações
@app.route("/transactions")
def transactions():
    month = request.args.get("month", current_month())
    start, end = month_bounds(month)
    conn = get_db()
    rows = conn.execute(
        """
        SELECT t.*, c.name AS category_name, c.color AS category_color,
               c.kind AS category_kind, a.name AS account_name
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        LEFT JOIN accounts a ON a.id = t.account_id
        WHERE t.posted_on BETWEEN ? AND ?
        ORDER BY t.posted_on DESC, t.id DESC
        """, (start, end),
    ).fetchall()
    # Dropdown lista categorias normais (kind != transfer) + as contas como destino de transferência.
    categories = conn.execute(
        "SELECT * FROM categories WHERE kind != 'transfer' ORDER BY name"
    ).fetchall()
    accounts_list = conn.execute("SELECT id, name FROM accounts ORDER BY name").fetchall()
    conn.close()
    return render_template(
        "transactions.html", rows=rows, categories=categories, accounts=accounts_list,
        month=month, month_label=month_label(month),
        prev_month=shift_month(month, -1), next_month=shift_month(month, +1),
    )


@app.route("/transactions/<int:tx_id>/categorize", methods=["POST"])
def categorize_tx(tx_id: int):
    value = request.form.get("category_id") or ""
    make_rule = request.form.get("make_rule")
    conn = get_db()

    # Opção "Para <conta>": marca o lançamento como transferência para aquela conta.
    if value.startswith("transfer:"):
        dest_id = int(value.split(":", 1)[1])
        tx = conn.execute("SELECT account_id FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        if tx and dest_id != tx["account_id"]:
            cat = transfer_category_id(conn)
            conn.execute("UPDATE transactions SET category_id = ?, transfer_to = ? WHERE id = ?",
                         (cat, dest_id, tx_id))
            conn.commit()
        conn.close()
        return redirect(request.referrer or url_for("transactions"))

    # Categoria normal: limpa qualquer marcação de transferência.
    category_id = value or None
    conn.execute("UPDATE transactions SET category_id = ?, transfer_to = NULL WHERE id = ?",
                 (category_id, tx_id))
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


@app.route("/transactions/<int:tx_id>/ignore", methods=["POST"])
def ignore_tx(tx_id: int):
    """Alterna 'ignorado': lançamento sai (ou volta) de orçamentos, gráficos, saldo e net worth."""
    conn = get_db()
    conn.execute("UPDATE transactions SET ignored = 1 - ignored WHERE id = ?", (tx_id,))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("transactions"))


# ----------------------------------------------------------------------------- transferências
def transfer_category_id(conn) -> int:
    """Id da categoria 'Transferência' (kind='transfer'), criando-a se não existir."""
    row = conn.execute("SELECT id FROM categories WHERE kind = 'transfer' ORDER BY id LIMIT 1").fetchone()
    if row:
        return row["id"]
    conn.execute("INSERT INTO categories (name, color, kind) VALUES ('Transferência', '#9aa0aa', 'transfer')")
    return conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]


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
    total = sum(r["budget"] for r in rows if r["budget"])
    conn.close()
    return render_template("budgets.html", rows=rows, total=total)


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

        # Dedup robusta em camadas, por conta:
        #  1) FITID (quando o banco fornece) é autoritativo — mesma id = mesmo lançamento.
        #  2) Sem FITID, usa-se a impressão digital de conteúdo com alinhamento por ocorrência:
        #     a k-ésima ocorrência idêntica do arquivo só entra se o banco ainda não tiver k delas.
        #     Isso barra reimportações mas preserva duplicatas legítimas (ex.: 2 cafés iguais no dia).
        existing = conn.execute(
            "SELECT fitid, fingerprint FROM transactions WHERE account_id = ?", (account_id,)
        ).fetchall()
        existing_fitids = {r["fitid"] for r in existing if r["fitid"]}
        db_fp_counts = defaultdict(int)
        for r in existing:
            if r["fingerprint"]:
                db_fp_counts[r["fingerprint"]] += 1
        file_fp_seen = defaultdict(int)

        inserted = skipped = 0
        for t in txns:
            fp = tx_fingerprint(t.posted_on, t.amount, t.description)
            if t.fitid and t.fitid in existing_fitids:
                skipped += 1
                continue
            if not t.fitid:
                idx = file_fp_seen[fp]
                file_fp_seen[fp] += 1
                if idx < db_fp_counts[fp]:
                    skipped += 1
                    continue
            category_id = categorize(t.description, rules)
            try:
                conn.execute(
                    """INSERT INTO transactions
                       (account_id, fitid, posted_on, amount, description, raw_memo, category_id, fingerprint)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (account_id, t.fitid, t.posted_on, t.amount,
                     t.description, t.raw_memo, category_id, fp),
                )
                inserted += 1
                if t.fitid:
                    existing_fitids.add(t.fitid)
            except Exception:
                # Backstop: UNIQUE(account_id, fitid) violado = já importado.
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
        opening = float((request.form.get("opening_balance") or "0").replace(".", "").replace(",", ".")) \
            if request.form.get("opening_balance") else 0.0
        conn.execute(
            "INSERT INTO accounts (name, type, bank, opening_balance) VALUES (?, ?, ?, ?)",
            (request.form["name"], request.form["type"], request.form.get("bank", ""), opening),
        )
        conn.commit()
        flash("Conta criada.", "ok")
    rows = conn.execute(
        """
        SELECT a.*,
               a.opening_balance
               + COALESCE((SELECT SUM(t.amount) FROM transactions t
                           WHERE t.account_id = a.id AND t.ignored = 0), 0)
               + COALESCE((SELECT SUM(-t.amount) FROM transactions t
                           WHERE t.transfer_to = a.id AND t.ignored = 0), 0) AS balance
        FROM accounts a ORDER BY a.name
        """
    ).fetchall()
    conn.close()
    return render_template("accounts.html", rows=rows)


@app.route("/accounts/<int:account_id>/balance", methods=["POST"])
def set_balance(account_id: int):
    """Ajusta o saldo inicial para que o saldo atual bata com o valor informado."""
    raw = (request.form.get("balance") or "").strip()
    if not raw:
        return redirect(url_for("accounts"))
    desired = float(raw.replace(".", "").replace(",", "."))
    conn = get_db()
    row = conn.execute(
        """
        SELECT a.opening_balance,
               a.opening_balance
               + COALESCE((SELECT SUM(t.amount) FROM transactions t
                           WHERE t.account_id = a.id AND t.ignored = 0), 0)
               + COALESCE((SELECT SUM(-t.amount) FROM transactions t
                           WHERE t.transfer_to = a.id AND t.ignored = 0), 0) AS balance
        FROM accounts a WHERE a.id = ?
        """, (account_id,),
    ).fetchone()
    if row:
        movimentos = row["balance"] - row["opening_balance"]
        conn.execute("UPDATE accounts SET opening_balance = ? WHERE id = ?",
                     (desired - movimentos, account_id))
        conn.commit()
        flash("Saldo ajustado.", "ok")
    conn.close()
    return redirect(url_for("accounts"))


# ----------------------------------------------------------------------------- patrimônio (bens)
ASSET_CATEGORIES = ["Imóvel", "Veículo", "Investimento", "Outros"]


@app.route("/assets", methods=["GET", "POST"])
def assets():
    conn = get_db()
    if request.method == "POST":
        value = float((request.form.get("value") or "0").replace(".", "").replace(",", "."))
        conn.execute(
            "INSERT INTO assets (name, category, value) VALUES (?, ?, ?)",
            (request.form["name"], request.form.get("category", "Outros"), value),
        )
        conn.commit()
        flash("Bem cadastrado.", "ok")
        return redirect(url_for("assets"))
    rows = conn.execute("SELECT * FROM assets ORDER BY value DESC").fetchall()
    total = sum(r["value"] for r in rows)
    conn.close()
    return render_template(
        "assets.html", rows=rows, total=total, categories=ASSET_CATEGORIES,
    )


@app.route("/assets/<int:asset_id>/delete", methods=["POST"])
def delete_asset(asset_id: int):
    conn = get_db()
    conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
    conn.commit()
    conn.close()
    flash("Bem removido.", "ok")
    return redirect(url_for("assets"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5005)
