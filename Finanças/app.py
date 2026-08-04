"""Analisador de gastos, orçamentos e (futuramente) patrimônio.

Portal Flask + SQLite. Foco atual: importar OFX, categorizar e acompanhar
orçamentos mensais por categoria em tempo hábil.
"""
import calendar
import math
import os
from collections import defaultdict
from datetime import date

from flask import Flask, flash, redirect, render_template, request, url_for

from categorizer import (
    apply_rule_everywhere, categorize, is_generic_pattern, load_rules,
    recategorize_uncategorized, rule_keyword,
)
from db import get_db, init_db, tx_fingerprint
from ofx_import import read_ofx_file
from xls_import import read_card_xlsx_file

app = Flask(__name__)
app.secret_key = "troque-este-segredo-em-producao"

# Ícone (Tabler) fixo por categoria e por tipo de bem.
CATEGORY_ICONS = {
    "Moradia": "home", "Transporte": "car", "Alimentação": "tools-kitchen-2",
    "Mercado": "shopping-cart", "Saúde": "heartbeat", "Lazer": "movie",
    "Assinaturas": "repeat", "Salário": "cash", "Outros": "dots",
    "Cuidados Pessoais": "sparkles", "Compras": "shopping-bag",
    "Juros e Impostos": "receipt-tax", "Transferência": "arrows-exchange",
    "Educação": "school", "Viagens": "plane", "Investimentos": "chart-line",
}
ASSET_ICONS = {
    "Imóvel": "home", "Veículo": "car", "Investimento": "chart-line", "Outros": "diamond",
}


def cat_icon(name: str) -> str:
    return "ti ti-" + CATEGORY_ICONS.get(name, "tag")


def asset_icon(category: str) -> str:
    return "ti ti-" + ASSET_ICONS.get(category, "diamond")


def static_v(filename: str) -> str:
    """URL de um arquivo estático com ?v=<mtime> p/ cache-busting: quando o arquivo
    muda, o navegador busca a versão nova em vez de servir do cache."""
    path = os.path.join(app.static_folder, filename)
    ver = int(os.path.getmtime(path)) if os.path.exists(path) else 0
    return url_for("static", filename=filename) + f"?v={ver}"


app.jinja_env.globals.update(cat_icon=cat_icon, asset_icon=asset_icon, static_v=static_v)

DEFAULT_CAT_COLOR = "#b6b9c0"


def is_outros(conn, category_id) -> bool:
    """True se a categoria é 'Outros' — que nunca pode virar regra/automação."""
    if not category_id:
        return False
    row = conn.execute("SELECT name FROM categories WHERE id = ?", (category_id,)).fetchone()
    return bool(row) and row["name"] == "Outros"


@app.context_processor
def inject_cat_color():
    """Disponibiliza cat_color(nome) nos templates, com a MESMA cor que cada
    categoria tem no gráfico "Gastos por categoria" (coluna color do banco).
    Carregado uma vez por render — a tabela de categorias é pequena."""
    conn = get_db()
    colors = {r["name"]: r["color"]
              for r in conn.execute("SELECT name, color FROM categories")}
    conn.close()

    def cat_color(name: str | None) -> str:
        return colors.get(name or "", DEFAULT_CAT_COLOR)

    return {"cat_color": cat_color}


@app.template_filter("brl")
def brl(v: float) -> str:
    """Formata em reais no padrão BR: 1.234.567,89."""
    s = f"{abs(v):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return ("-" if v < 0 else "") + s


@app.template_filter("brl0")
def brl0(v: float) -> str:
    """Reais sem centavos, padrão BR: 1.234.567 (com sinal para negativos)."""
    s = f"{abs(v):,.0f}".replace(",", ".")
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


def category_history(conn, category_id: int, month: str, n_months: int = 6) -> list[dict]:
    """Orçado × gasto da categoria nos últimos n meses (para o popup do dashboard)."""
    months = [shift_month(month, -i) for i in range(n_months - 1, -1, -1)]
    data = []
    for m in months:
        start, end = month_bounds(m)
        # Gasto líquido: débito soma, crédito (estorno/reembolso) abate.
        spent = conn.execute(
            "SELECT COALESCE(SUM(-amount), 0) AS v "
            "FROM transactions WHERE category_id = ? AND ignored = 0 AND posted_on BETWEEN ? AND ?",
            (category_id, start, end),
        ).fetchone()["v"]
        budget = budget_for(conn, category_id, m) or 0
        data.append((m, spent, budget))

    mx = max([s for _, s, _ in data] + [b for _, _, b in data] + [1])
    return [{
        "label": month_short(m), "spent": s, "budget": b,
        "spent_h": round(s / mx * 100, 1), "budget_h": round(b / mx * 100, 1),
        "over": s > b and b > 0, "current": m == month,
    } for m, s, b in data]


# ----------------------------------------------------------------------------- dashboard
@app.route("/")
def dashboard():
    month = request.args.get("month", current_month())
    start, end = month_bounds(month)
    days_elapsed, days_total = pace_for_month(month)
    conn = get_db()

    # Gasto líquido por categoria: débito soma, crédito (estorno/reembolso) abate.
    spent_rows = conn.execute(
        """
        SELECT c.id, c.name, c.color,
               COALESCE(SUM(-t.amount), 0) AS spent
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
        # Barra "ritmo do mês": o teto fica na marca de 80% da trilha, deixando
        # 20% à direita para o estouro extravasar sem vazar do card (cap 125%).
        FULL = 80.0
        if budget:
            ratio = spent / budget
            main_w = round(min(ratio, 1.0) * FULL, 1)
            over_w = round((min(ratio, 1.25) - 1.0) * FULL, 1) if ratio > 1 else 0.0
            over_txt = ("estourou em R$ " + f"{spent - budget:,.0f}".replace(",", ".")
                        + f" ({pct:.0f}%)") if ratio > 1 else None
            bar_class = "over" if status == "over" else (
                "warn" if status in ("warning", "pace_over") else "ok")
        else:
            main_w = over_w = 0.0
            over_txt = None
            bar_class = "none"
        budget_cards.append({
            "category": row["name"], "category_id": row["id"], "color": row["color"],
            "spent": spent, "budget": budget, "pct": pct,
            "projected": projected, "remaining": (budget - spent) if budget else None,
            "status": status,
            "main_w": main_w, "over_w": over_w, "over_txt": over_txt, "bar_class": bar_class,
            "history": category_history(conn, row["id"], month),
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
    nw_chart = build_networth_chart(conn, month)

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

    # Rosca "gastos por categoria": top 5 + "Demais", com offsets cumulativos
    # para o stroke-dasharray (pathLength=100) do SVG.
    spend_total = sum(c["spent"] for c in budget_cards)
    spent_cats = [c for c in budget_cards if c["spent"] > 0]
    donut_items = [{"category": c["category"], "color": c["color"], "spent": c["spent"]}
                   for c in spent_cats[:5]]
    rest = spent_cats[5:]
    if rest:
        donut_items.append({"category": "Demais", "color": "#b6b9c0",
                            "spent": sum(c["spent"] for c in rest)})
    acc = 0.0
    for d in donut_items:
        frac = (d["spent"] / spend_total * 100) if spend_total else 0.0
        d["pct"] = round(frac)
        d["dash"] = round(frac, 2)
        d["offset"] = round(-acc, 2)
        mid_angle = math.radians((acc + frac / 2) / 100 * 360 - 90)
        d["lbl_x"] = round(21 + 15.9159 * math.cos(mid_angle), 2)
        d["lbl_y"] = round(21 + 15.9159 * math.sin(mid_angle), 2)
        d["show_label"] = frac >= 6
        acc += frac

    # Composição do patrimônio (barra horizontal empilhada): bens por tipo +
    # investimentos + bancos. Saldo atual = inicial + lançamentos + transferências.
    composition = build_composition(conn)

    conn.close()
    return render_template(
        "dashboard.html",
        month=month, month_label=month_label(month),
        prev_month=shift_month(month, -1), next_month=shift_month(month, +1),
        cards=budget_cards, total_spent=total_spent, total_budget=total_budget,
        days_elapsed=days_elapsed, days_total=days_total,
        uncategorized=uncategorized, income=income,
        charts=charts, nw_chart=nw_chart, overruns=overruns,
        donut=donut_items, spend_total=spend_total,
        composition=composition,
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
    """Séries mensais (gasto, receita) dos últimos n meses até `month`."""
    months = [shift_month(month, -i) for i in range(n_months - 1, -1, -1)]

    gastos, receitas = [], []
    for m in months:
        start, end = month_bounds(m)
        gasto = conn.execute(
            "SELECT COALESCE(SUM(-t.amount), 0) AS v FROM transactions t "
            "JOIN categories c ON c.id = t.category_id "
            "WHERE c.kind = 'expense' AND t.ignored = 0 AND t.posted_on BETWEEN ? AND ?",
            (start, end),
        ).fetchone()["v"]
        receita = conn.execute(
            "SELECT COALESCE(SUM(t.amount), 0) AS v FROM transactions t "
            "JOIN categories c ON c.id = t.category_id "
            "WHERE c.kind = 'income' AND t.ignored = 0 AND t.posted_on BETWEEN ? AND ?",
            (start, end),
        ).fetchone()["v"]
        gastos.append(gasto)
        receitas.append(receita)

    labels = [month_short(m) for m in months]

    # ---- Gráfico de linha "Fluxo mensal" (receita x gasto) ----
    # Coordenadas em viewBox 480 x VBH; eixo de valor entre y=top e y=base (=0).
    # VBH alto deixa o gráfico mais "cheio" no card alto do dashboard.
    W, x0, x1, top, base, VBH = 480, 24, 456, 36, 200, 236
    grid_top, grid_bottom = 16, 212
    n = len(months)
    xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(n)] if n > 1 else [x0]
    vmax = max(receitas + gastos + [1])

    def y_of(v):
        return base - (v / vmax) * (base - top)

    def fmt_cur(v):
        return "R$ " + f"{v:,.0f}".replace(",", ".")

    receita_pts = " ".join(f"{x:.0f},{y_of(v):.1f}" for x, v in zip(xs, receitas))
    gasto_pts = " ".join(f"{x:.0f},{y_of(v):.1f}" for x, v in zip(xs, gastos))

    # Rótulo de cada ponto fica do lado OPOSTO à outra linha: a série mais alta
    # no mês recebe o rótulo acima do nó, a mais baixa abaixo. Assim, quando as
    # linhas se cruzam (ex.: receita e gasto próximos), os textos nunca colidem.
    # O rótulo de baixo é limitado para não invadir a faixa dos meses.
    def lbl_y(v, above):
        y = y_of(v) + (-9 if above else 13)
        # Não deixa o rótulo de baixo invadir a faixa dos meses (grid_bottom+14):
        # quando a série está rente à base, o texto flutua logo acima da linha.
        return round(min(y, grid_bottom - 16), 1)

    receita_above = [receitas[i] >= gastos[i] for i in range(n)]

    flow = {
        "vb_h": VBH, "grid_top": grid_top, "grid_bottom": grid_bottom,
        "month_y": round((grid_bottom + 14) / VBH * 100, 2),
        "receita_pts": receita_pts, "gasto_pts": gasto_pts,
        "receita_nodes": [{"x": round(x), "y": round(y_of(v), 1), "ly": lbl_y(v, receita_above[i]),
                           "label": fmt_cur(v), "current": m == month}
                          for i, (x, v, m) in enumerate(zip(xs, receitas, months))],
        "gasto_nodes": [{"x": round(x), "y": round(y_of(v), 1), "ly": lbl_y(v, not receita_above[i]),
                         "label": fmt_cur(v), "current": m == month}
                        for i, (x, v, m) in enumerate(zip(xs, gastos, months))],
        "month_nodes": [{"x": round(x), "label": l, "current": m == month}
                        for x, l, m in zip(xs, labels, months)],
    }

    return {"labels": labels, "flow": flow}


def build_networth_chart(conn, month: str, n_months: int = 6) -> dict:
    """Série do patrimônio líquido ao fim de cada um dos últimos n meses."""
    # Um mês extra para trás dá o valor anterior da primeira barra (variação m/m).
    months = [shift_month(month, -i) for i in range(n_months, -1, -1)]
    opening = conn.execute("SELECT COALESCE(SUM(opening_balance), 0) AS v FROM accounts").fetchone()["v"]
    assets = conn.execute("SELECT COALESCE(SUM(value), 0) AS v FROM assets").fetchone()["v"]

    values = []
    for m in months:
        end = month_bounds(m)[1]
        moves = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS v FROM transactions "
            "WHERE ignored = 0 AND posted_on <= ?", (end,),
        ).fetchone()["v"]
        moves += conn.execute(
            "SELECT COALESCE(SUM(-amount), 0) AS v FROM transactions "
            "WHERE ignored = 0 AND transfer_to IS NOT NULL AND posted_on <= ?", (end,),
        ).fetchone()["v"]
        values.append(opening + moves + assets)

    # Linha/área com eixo "zoom" (min..max dos meses exibidos). Como o patrimônio
    # varia pouco (~0,2%/mês), barras empilhadas exageravam micro-variações; a linha
    # mostra honestamente a estabilidade e o rótulo de cada ponto traz o delta m/m.
    disp = values[1:]                       # meses exibidos (sem o mês extra)
    vmin, vmax = min(disp), max(disp)
    span = (vmax - vmin) or 1

    # Geometria do viewBox (mesma largura do "Fluxo mensal" p/ o overlay de rótulos).
    W, x0, x1, VBH = 480, 30, 450, 176
    ytop, ybot, base_y, month_y = 44, 140, 156, 168
    grid_top, grid_bottom = 20, 156
    n = len(disp)
    xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(n)] if n > 1 else [x0]

    def y_of(v):
        return ybot - (v - vmin) / span * (ybot - ytop)

    def fmt_full(v):
        return "R$ " + f"{v:,.0f}".replace(",", ".")

    def fmt_delta(d):
        return ("+" if d >= 0 else "−") + "R$ " + f"{abs(d):,.0f}".replace(",", ".")

    def fmt_pct(p):
        return ("+" if p >= 0 else "−") + f"{abs(p):.1f}%".replace(".", ",")

    ys = [round(y_of(v), 1) for v in disp]
    line_pts = " ".join(f"{x:.0f},{y}" for x, y in zip(xs, ys))
    area_d = (f"M{xs[0]:.0f},{ys[0]} "
              + " ".join(f"L{x:.0f},{y}" for x, y in zip(xs, ys))
              + f" L{xs[-1]:.0f},{base_y} L{xs[0]:.0f},{base_y} Z")

    dots, delta_nodes, month_nodes = [], [], []
    for i in range(n):
        m, v = months[i + 1], disp[i]
        prev = values[i]                    # mês imediatamente anterior
        delta = v - prev
        dots.append({"x": round(xs[i]), "y": ys[i], "current": m == month})
        delta_nodes.append({
            "x": round(xs[i]), "ly": round(max(ys[i] - 9, 12), 1),
            "label": fmt_delta(delta), "up": delta >= 0, "current": m == month,
        })
        month_nodes.append({"x": round(xs[i]), "label": month_short(m), "current": m == month})

    last_delta = disp[-1] - values[-2]
    last_pct = (last_delta / abs(values[-2]) * 100) if values[-2] else 0.0

    return {
        "vb_h": VBH,
        "base_y": base_y,
        "grid_top": grid_top, "grid_bottom": grid_bottom,
        "month_y": round(month_y / VBH * 100, 2),
        "line_pts": line_pts, "area_d": area_d,
        "dots": dots, "delta_nodes": delta_nodes, "month_nodes": month_nodes,
        "pct": fmt_pct(last_pct), "up": last_delta >= 0,
        "value_label": fmt_full(disp[-1]),
        "value_x": round(xs[-1]), "value_y": round(min(ys[-1] + 15, base_y - 4), 1),
    }


def build_composition(conn) -> dict:
    """Composição do patrimônio para a barra horizontal empilhada: bens por
    tipo + investimentos + bancos. Só valores positivos ganham largura; valores
    negativos (ex.: conta no vermelho) aparecem apenas na legenda."""
    bal = conn.execute(
        "SELECT a.type, a.opening_balance "
        "  + COALESCE((SELECT SUM(amount) FROM transactions "
        "              WHERE account_id = a.id AND ignored = 0), 0) "
        "  + COALESCE((SELECT SUM(-amount) FROM transactions "
        "              WHERE transfer_to = a.id AND ignored = 0), 0) AS v "
        "FROM accounts a"
    ).fetchall()
    bancos = sum(r["v"] for r in bal if r["type"] in ("checking", "credit"))
    invest_contas = sum(r["v"] for r in bal if r["type"] == "investment")

    assets = conn.execute("SELECT category, SUM(value) AS v FROM assets GROUP BY category").fetchall()
    by_cat = {r["category"]: r["v"] for r in assets}
    imovel = by_cat.get("Imóvel", 0)
    veiculo = by_cat.get("Veículo", 0)
    invest = invest_contas + by_cat.get("Investimento", 0)
    outros = by_cat.get("Outros", 0)

    raw = [
        ("Imóvel", imovel, "var(--indigo)"),
        ("Investimentos", invest, "var(--green)"),
        ("Veículo", veiculo, "var(--amber)"),
        ("Outros bens", outros, "#7a8aa0"),
        ("Bancos", bancos, "var(--faint)"),
    ]
    segs = [(n, v, c) for n, v, c in raw if v != 0]
    total = sum(v for _, v, _ in segs) or 1          # patrimônio líquido
    pos_total = sum(v for _, v, _ in segs if v > 0) or 1

    def fmt(v):
        return ("−" if v < 0 else "") + "R$ " + f"{abs(v):,.0f}".replace(",", ".")

    out = []
    for name, v, color in sorted(segs, key=lambda s: s[1], reverse=True):
        width = (v / pos_total * 100) if v > 0 else 0.0
        out.append({
            "name": name, "color": color, "value": fmt(v),
            "pct": round(v / total * 100),
            "width": round(width, 2), "show_name": width >= 16, "positive": v > 0,
        })
    return {"segs": out, "total": fmt(total)}


# ----------------------------------------------------------------------------- transações
def build_tx_chart(conn, month: str, account_id, category_ids, n_months: int = 6) -> dict:
    """Linha de "Gastos" mensais dos últimos n meses, respeitando os mesmos filtros da
    lista (conta + categorias). Cada ponto é só o TOTAL de despesas (kind='expense') do
    mês; entradas são ignoradas. Mesmo design do gráfico Patrimônio líquido."""
    months = [shift_month(month, -i) for i in range(n_months - 1, -1, -1)]
    base_sql = ("SELECT COALESCE(SUM(-t.amount), 0) AS v FROM transactions t "
                "JOIN categories c ON c.id = t.category_id "
                "WHERE c.kind = 'expense' AND t.ignored = 0 AND t.posted_on BETWEEN ? AND ?")
    extra, extra_params = "", []
    if account_id:
        extra += " AND t.account_id = ?"
        extra_params.append(account_id)
    if category_ids:
        extra += " AND t.category_id IN (%s)" % ",".join("?" * len(category_ids))
        extra_params.extend(category_ids)

    values = []
    for m in months:
        s, e = month_bounds(m)
        values.append(conn.execute(base_sql + extra, [s, e, *extra_params]).fetchone()["v"])

    # Mesma geometria/escala "zoom" do gráfico Patrimônio líquido (build_networth_chart),
    # para o design ficar idêntico: área até a base, linha indigo, pontos, rótulo por ponto.
    W, x0, x1, VBH = 480, 30, 450, 176
    ytop, ybot, base_y, month_y = 44, 140, 156, 168
    grid_top, grid_bottom = 20, 156
    n = len(values)
    xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(n)] if n > 1 else [x0]
    lo, hi = min(values), max(values)
    span = (hi - lo) or 1

    def y_of(v):
        return ybot - (v - lo) / span * (ybot - ytop)

    def fmt(v):
        return "R$ " + f"{v:,.0f}".replace(",", ".")

    ys = [round(y_of(v), 1) for v in values]
    line_pts = " ".join(f"{x:.0f},{y}" for x, y in zip(xs, ys))
    area_d = (f"M{xs[0]:.0f},{ys[0]} "
              + " ".join(f"L{x:.0f},{y}" for x, y in zip(xs, ys))
              + f" L{xs[-1]:.0f},{base_y} L{xs[0]:.0f},{base_y} Z")
    dots, delta_nodes, month_nodes = [], [], []
    for i, m in enumerate(months):
        dots.append({"x": round(xs[i]), "y": ys[i], "current": m == month})
        delta_nodes.append({
            "x": round(xs[i]), "ly": round(max(ys[i] - 9, 12), 1),
            "label": fmt(values[i]), "current": m == month,
        })
        month_nodes.append({"x": round(xs[i]), "label": month_short(m), "current": m == month})
    cur = values[-1] if values else 0
    return {
        "vb_h": VBH, "base_y": base_y,
        "grid_top": grid_top, "grid_bottom": grid_bottom,
        "month_y": round(month_y / VBH * 100, 2),
        "line_pts": line_pts, "area_d": area_d,
        "dots": dots, "delta_nodes": delta_nodes, "month_nodes": month_nodes,
        "cur_label": fmt(cur),
    }


@app.route("/transactions")
def transactions():
    month = request.args.get("month", current_month())
    account_id = request.args.get("account_id", type=int)
    category_ids = [int(c) for c in request.args.getlist("category_id") if c.isdigit()]
    uncat = request.args.get("uncat") == "1"
    start, end = month_bounds(month)
    conn = get_db()
    query = """
        SELECT t.*, c.name AS category_name, c.color AS category_color,
               c.kind AS category_kind, a.name AS account_name
        FROM transactions t
        LEFT JOIN categories c ON c.id = t.category_id
        LEFT JOIN accounts a ON a.id = t.account_id
        WHERE t.posted_on BETWEEN ? AND ?
    """
    params = [start, end]
    if account_id:
        query += " AND t.account_id = ?"
        params.append(account_id)
    if category_ids:
        query += " AND t.category_id IN (%s)" % ",".join("?" * len(category_ids))
        params.extend(category_ids)
    if uncat:
        query += " AND t.category_id IS NULL AND t.ignored = 0"
    query += " ORDER BY t.posted_on DESC, t.id DESC"
    rows = conn.execute(query, params).fetchall()
    tx_chart = build_tx_chart(conn, month, account_id, category_ids)
    # Dropdown lista categorias normais (kind != transfer) + as contas como destino de transferência.
    categories = conn.execute(
        "SELECT * FROM categories WHERE kind != 'transfer' ORDER BY name"
    ).fetchall()
    # Categoria "Transferência" (kind='transfer'): opção para marcar um lançamento
    # como transferência sem creditar a outra conta — usada quando as duas pontas já
    # foram importadas (ex.: pagamento do cartão). Fica fora de gastos/receitas.
    transfer_cat = conn.execute(
        "SELECT id, name FROM categories WHERE kind = 'transfer' ORDER BY id LIMIT 1"
    ).fetchone()
    accounts_list = conn.execute("SELECT id, name FROM accounts ORDER BY name").fetchall()
    conn.close()
    return render_template(
        "transactions.html", rows=rows, categories=categories, accounts=accounts_list,
        transfer_cat=transfer_cat, account_id=account_id, category_ids=category_ids, uncat=uncat,
        tx_chart=tx_chart,
        month=month, month_label=month_label(month),
        prev_month=shift_month(month, -1), next_month=shift_month(month, +1),
    )


@app.route("/transactions/<int:tx_id>/categorize", methods=["POST"])
def categorize_tx(tx_id: int):
    value = request.form.get("category_id") or ""
    make_rule = request.form.get("make_rule")
    conn = get_db()

    # Categoria normal: limpa qualquer marcação de transferência.
    category_id = value or None
    conn.execute("UPDATE transactions SET category_id = ?, transfer_to = NULL WHERE id = ?",
                 (category_id, tx_id))
    # Opcional: aprender uma regra a partir desta correção. "Outros" nunca vira regra.
    if make_rule and category_id and not is_outros(conn, category_id):
        tx = conn.execute("SELECT description FROM transactions WHERE id = ?", (tx_id,)).fetchone()
        if tx:
            keyword = rule_keyword(tx["description"])
            if keyword and not is_generic_pattern(keyword):
                conn.execute(
                    "INSERT INTO rules (pattern, category_id, priority) VALUES (?, ?, 50)",
                    (keyword, category_id),
                )
                applied = apply_rule_everywhere(conn, keyword, int(category_id))
                flash(f"Regra criada: '{keyword}' → categoria ({applied} lançamento(s) atualizados).", "ok")
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("transactions"))


@app.route("/transactions/save", methods=["POST"])
def transactions_save():
    """Salva em lote as categorias escolhidas na tela (campos cat:<id>) e, para os
    itens marcados como regra (rule:<id>), cria a regra e a aplica a TODO o histórico."""
    conn = get_db()
    rules_created = 0
    for key, value in request.form.items():
        if not key.startswith("cat:"):
            continue
        tx_id = int(key.split(":", 1)[1])

        category_id = value or None
        conn.execute("UPDATE transactions SET category_id = ?, transfer_to = NULL WHERE id = ?",
                     (category_id, tx_id))

        # Marcado como "regra": aprende a regra a partir desta correção. "Outros" nunca
        # vira regra — é categoria de uso manual, não de automação.
        if request.form.get(f"rule:{tx_id}") and category_id and not is_outros(conn, category_id):
            tx = conn.execute("SELECT description FROM transactions WHERE id = ?", (tx_id,)).fetchone()
            keyword = rule_keyword(tx["description"]) if tx else ""
            if keyword and not is_generic_pattern(keyword) and not conn.execute(
                "SELECT 1 FROM rules WHERE pattern = ? AND category_id = ?", (keyword, category_id)
            ).fetchone():
                conn.execute("INSERT INTO rules (pattern, category_id, priority) VALUES (?, ?, 50)",
                             (keyword, category_id))
                rules_created += 1
                # A regra nova vale para todo o histórico, inclusive lançamentos que já
                # tinham outra categoria — eles passam a seguir a regra.
                apply_rule_everywhere(conn, keyword, int(category_id))

    # "Ignorar": cada caixa não marcada não é enviada pelo navegador, então usamos
    # a lista de ids da página (tx_ids) para saber quais devem voltar a ignored=0.
    tx_ids = [int(i) for i in (request.form.get("tx_ids") or "").split(",") if i]
    for tx_id in tx_ids:
        ignored = 1 if request.form.get(f"ignore:{tx_id}") else 0
        conn.execute("UPDATE transactions SET ignored = ? WHERE id = ?", (ignored, tx_id))
    conn.commit()

    # Aplica todas as regras ao histórico inteiro (lançamentos ainda sem categoria).
    applied = recategorize_uncategorized(conn)
    conn.close()
    flash(f"Salvo. {rules_created} regra(s) nova(s); {applied} lançamento(s) categorizado(s) "
          f"automaticamente em todo o histórico.", "ok")
    return redirect(url_for(
        "transactions",
        month=request.form.get("month") or current_month(),
        account_id=request.form.get("account_id") or None,
        category_id=request.form.getlist("category_id") or None,
        uncat=request.form.get("uncat") or None,
    ))


@app.route("/transactions/<int:tx_id>/ignore", methods=["POST"])
def ignore_tx(tx_id: int):
    """Alterna 'ignorado': lançamento sai (ou volta) de orçamentos, gráficos, saldo e net worth."""
    conn = get_db()
    conn.execute("UPDATE transactions SET ignored = 1 - ignored WHERE id = ?", (tx_id,))
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
    total = sum(r["budget"] for r in rows if r["budget"])

    # Gasto médio mensal dos últimos 6 meses (incl. o mês atual) por categoria.
    # Soma das saídas na janela ÷ 6 meses — meses sem gasto contam como zero.
    n_months = 6
    cur = current_month()
    win_start = month_bounds(shift_month(cur, -(n_months - 1)))[0]
    win_end = month_bounds(cur)[1]
    avg_rows = conn.execute(
        """
        SELECT category_id, SUM(-amount) / ? AS avg_month
        FROM transactions
        WHERE ignored = 0 AND category_id IS NOT NULL
          AND posted_on BETWEEN ? AND ?
        GROUP BY category_id
        """,
        (n_months, win_start, win_end),
    ).fetchall()
    avg6 = {r["category_id"]: r["avg_month"] for r in avg_rows}

    conn.close()
    return render_template("budgets.html", rows=rows, total=total, avg6=avg6, avg_months=n_months)


# ----------------------------------------------------------------------------- import OFX
def lca_resgate_target(conn, description: str, src_account_id: int):
    """Resgate de LCA: o crédito cai na Conta Corrente mas o dinheiro sai da
    aplicação. Se a descrição indicar um resgate de LCA, devolve o id da conta de
    investimento (LCA) para registrar a perna de SAÍDA — assim o patrimônio fica
    neutro (o dinheiro só mudou de conta). Senão, None."""
    d = (description or "").upper()
    if "LCA" not in d or "RESGATE" not in d:
        return None
    row = conn.execute(
        "SELECT id FROM accounts WHERE type = 'investment' "
        "AND (UPPER(name) LIKE '%LCA%' OR UPPER(name) LIKE '%LETRAS DE CR%') "
        "AND id != ? ORDER BY id LIMIT 1", (src_account_id,),
    ).fetchone()
    return row["id"] if row else None


@app.route("/import", methods=["GET", "POST"])
def import_ofx():
    conn = get_db()
    accounts = conn.execute("SELECT * FROM accounts ORDER BY name").fetchall()
    if request.method == "POST":
        account_id = int(request.form["account_id"])
        files = [f for f in request.files.getlist("ofx_file") if f and f.filename]
        if not files:
            flash("Selecione ao menos um arquivo.", "error")
            return redirect(url_for("import_ofx"))

        rules = load_rules(conn)
        transfer_cat = conn.execute(
            "SELECT id FROM categories WHERE kind = 'transfer' ORDER BY id LIMIT 1"
        ).fetchone()
        transfer_cat_id = transfer_cat["id"] if transfer_cat else None

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
        errors = []
        for file in files:
            # Aceita OFX (extrato/cartão) e XLSX (fatura do cartão do Itaú, que não
            # exporta OFX). O parser certo é escolhido pela extensão.
            raw = file.read()
            name = file.filename.lower()
            try:
                if name.endswith((".xlsx", ".xls")):
                    txns = read_card_xlsx_file(raw)
                else:
                    txns = read_ofx_file(raw)
            except Exception as exc:
                errors.append(f"{file.filename}: {exc}")
                continue

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
                    # Resgate de LCA: registra automaticamente a saída espelhada na
                    # conta da aplicação, para o patrimônio não inflar (o dinheiro só
                    # mudou da LCA para a Conta Corrente).
                    target = (lca_resgate_target(conn, t.description, account_id)
                              if t.amount > 0 else None)
                    if target:
                        mirror_fp = tx_fingerprint(t.posted_on, -t.amount, t.description)
                        dup = conn.execute(
                            "SELECT 1 FROM transactions WHERE account_id = ? AND fingerprint = ?",
                            (target, mirror_fp),
                        ).fetchone()
                        if not dup:
                            conn.execute(
                                """INSERT INTO transactions
                                   (account_id, posted_on, amount, description, category_id, fingerprint)
                                   VALUES (?, ?, ?, ?, ?, ?)""",
                                (target, t.posted_on, -t.amount, "Resgate → Conta Corrente",
                                 transfer_cat_id, mirror_fp),
                            )
                except Exception:
                    # Backstop: UNIQUE(account_id, fitid) violado = já importado.
                    skipped += 1
        conn.commit()
        conn.close()
        if errors:
            flash(f"Não consegui ler {len(errors)} arquivo(s): " + "; ".join(errors), "error")
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
    # Rendimento dos investimentos: diferença entre os dois últimos valores informados.
    rendimentos = {}
    for r in rows:
        if r["type"] == "investment":
            snaps = conn.execute(
                "SELECT balance FROM account_snapshots WHERE account_id = ? "
                "ORDER BY on_date DESC, id DESC LIMIT 2", (r["id"],),
            ).fetchall()
            if len(snaps) == 2:
                rendimentos[r["id"]] = snaps[0]["balance"] - snaps[1]["balance"]
    conn.close()
    return render_template("accounts.html", rows=rows, rendimentos=rendimentos)


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
        SELECT a.type, a.opening_balance,
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
        # Investimentos: guarda o valor informado para calcular o rendimento entre atualizações.
        if row["type"] == "investment":
            conn.execute(
                "INSERT INTO account_snapshots (account_id, on_date, balance) VALUES (?, ?, ?)",
                (account_id, date.today().isoformat(), desired),
            )
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


@app.route("/assets/<int:asset_id>/update", methods=["POST"])
def update_asset(asset_id: int):
    """Atualiza o valor de um bem já cadastrado."""
    raw = (request.form.get("value") or "").strip()
    if raw:
        value = float(raw.replace(".", "").replace(",", "."))
        conn = get_db()
        conn.execute("UPDATE assets SET value = ?, updated_at = ? WHERE id = ?",
                     (value, date.today().isoformat(), asset_id))
        conn.commit()
        conn.close()
        flash("Valor do bem atualizado.", "ok")
    return redirect(url_for("assets"))


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
