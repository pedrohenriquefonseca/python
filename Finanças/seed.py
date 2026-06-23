"""Popula o banco com dados de exemplo para visualizar o app antes do OFX real.

Rode uma vez:  python seed.py
Para zerar e recomeçar do zero, apague o arquivo financas.db.
"""
import calendar
import random
from datetime import date, timedelta

from db import get_db, init_db

CATEGORIES = [
    ("Alimentação", "#f59f00", "expense"),
    ("Transporte", "#2f6bff", "expense"),
    ("Moradia", "#8b5cf6", "expense"),
    ("Lazer", "#fd7e14", "expense"),
    ("Saúde", "#12b886", "expense"),
    ("Mercado", "#ec4899", "expense"),
    ("Assinaturas", "#06b6d4", "expense"),
    ("Outros", "#9aa0aa", "expense"),
    ("Salário", "#22c55e", "income"),
    ("Transferência", "#9aa0aa", "transfer"),
]

BUDGETS = {
    "Alimentação": 1500, "Transporte": 600, "Moradia": 3000,
    "Lazer": 800, "Saúde": 500, "Mercado": 1200, "Assinaturas": 300,
}

SAMPLE_TX = [
    ("Alimentação", "IFOOD", -45, -120),
    ("Alimentação", "RESTAURANTE FASANO", -90, -260),
    ("Transporte", "UBER", -15, -55),
    ("Transporte", "POSTO SHELL", -150, -300),
    ("Mercado", "PAO DE ACUCAR", -120, -450),
    ("Lazer", "CINEMARK", -40, -90),
    ("Lazer", "SPOTIFY", -22, -22),
    ("Assinaturas", "NETFLIX", -55, -55),
    ("Saúde", "DROGARIA SP", -30, -180),
    ("Moradia", "CONDOMINIO EDIF", -1800, -1800),
]


def seed():
    init_db()
    conn = get_db()

    # Conta corrente de exemplo, com saldo inicial.
    conn.execute("INSERT INTO accounts (name, type, bank, opening_balance) VALUES (?,?,?,?)",
                 ("Conta Corrente (exemplo)", "checking", "Demo", 20000.0))
    account_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

    # Segunda conta (poupança), para demonstrar transferências.
    conn.execute("INSERT INTO accounts (name, type, bank, opening_balance) VALUES (?,?,?,?)",
                 ("Poupança (exemplo)", "investment", "Demo", 8000.0))
    savings_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

    # Bens extra-bancários de exemplo (entram no net worth).
    for name, category, value in [
        ("Apartamento", "Imóvel", 120000.0),
        ("Carro", "Veículo", 32000.0),
        ("Tesouro Direto", "Investimento", 10110.0),
    ]:
        conn.execute("INSERT INTO assets (name, category, value) VALUES (?,?,?)",
                     (name, category, value))

    cat_ids = {}
    for name, color, kind in CATEGORIES:
        conn.execute("INSERT OR IGNORE INTO categories (name, color, kind) VALUES (?,?,?)",
                     (name, color, kind))
    for row in conn.execute("SELECT id, name FROM categories"):
        cat_ids[row["name"]] = row["id"]

    for name, amount in BUDGETS.items():
        conn.execute("INSERT OR IGNORE INTO budgets (category_id, amount, month) VALUES (?,?,NULL)",
                     (cat_ids[name], amount))

    # Lançamentos espalhados pelos últimos 6 meses, para alimentar os gráficos.
    today = date.today()
    fitid = 1000
    for back in range(5, -1, -1):  # do mês -5 até o mês atual
        idx = today.year * 12 + (today.month - 1) - back
        year, mon = idx // 12, idx % 12 + 1
        first = date(year, mon, 1)
        days_in_month = calendar.monthrange(year, mon)[1]
        # No mês corrente só vai até hoje; nos passados, o mês inteiro.
        max_day = today.day if (year, mon) == (today.year, today.month) else days_in_month

        for cat, desc, lo, hi in SAMPLE_TX:
            n = random.randint(1, 4)
            for _ in range(n):
                d = first + timedelta(days=random.randint(0, max_day - 1))
                amount = round(random.uniform(lo, hi), 2)
                fitid += 1
                conn.execute(
                    """INSERT OR IGNORE INTO transactions
                       (account_id, fitid, posted_on, amount, description, raw_memo, category_id)
                       VALUES (?,?,?,?,?,?,?)""",
                    (account_id, str(fitid), d.isoformat(), amount, desc, desc, cat_ids[cat]),
                )

        # Salário do dia 5 de cada mês (varia um pouco para o gráfico não ficar reto).
        fitid += 1
        conn.execute(
            """INSERT OR IGNORE INTO transactions
               (account_id, fitid, posted_on, amount, description, raw_memo, category_id)
               VALUES (?,?,?,?,?,?,?)""",
            (account_id, str(fitid), first.replace(day=5).isoformat(),
             round(random.uniform(11000, 13000), 2),
             "SALARIO EMPRESA XYZ", "SALARIO", cat_ids["Salário"]),
        )

    # Transferência de exemplo: R$ 1.500 da conta corrente para a poupança (mês atual).
    when = first.replace(day=10).isoformat()
    fitid += 1
    conn.execute(
        """INSERT INTO transactions (account_id, fitid, posted_on, amount, description, raw_memo, category_id)
           VALUES (?,?,?,?,?,?,?)""",
        (account_id, str(fitid), when, -1500.0,
         "Transferência → Poupança (exemplo)", "TRANSF", cat_ids["Transferência"]),
    )
    fitid += 1
    conn.execute(
        """INSERT INTO transactions (account_id, fitid, posted_on, amount, description, raw_memo, category_id)
           VALUES (?,?,?,?,?,?,?)""",
        (savings_id, str(fitid), when, 1500.0,
         "Transferência ← Conta Corrente (exemplo)", "TRANSF", cat_ids["Transferência"]),
    )

    conn.commit()
    conn.close()
    print("Dados de exemplo inseridos. Rode:  python app.py")


if __name__ == "__main__":
    seed()
