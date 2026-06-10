"""Popula o banco com dados de exemplo para visualizar o app antes do OFX real.

Rode uma vez:  python seed.py
Para zerar e recomeçar do zero, apague o arquivo financas.db.
"""
import random
from datetime import date, timedelta

from db import get_db, init_db

CATEGORIES = [
    ("Alimentação", "#e3b341", "expense"),
    ("Transporte", "#5b8def", "expense"),
    ("Moradia", "#a06be0", "expense"),
    ("Lazer", "#e08a3c", "expense"),
    ("Saúde", "#3fb27f", "expense"),
    ("Mercado", "#d96ba0", "expense"),
    ("Assinaturas", "#6be0d4", "expense"),
    ("Salário", "#3fb27f", "income"),
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

    # Conta corrente de exemplo.
    conn.execute("INSERT INTO accounts (name, type, bank) VALUES (?,?,?)",
                 ("Conta Corrente (exemplo)", "checking", "Demo"))
    account_id = conn.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

    cat_ids = {}
    for name, color, kind in CATEGORIES:
        conn.execute("INSERT OR IGNORE INTO categories (name, color, kind) VALUES (?,?,?)",
                     (name, color, kind))
    for row in conn.execute("SELECT id, name FROM categories"):
        cat_ids[row["name"]] = row["id"]

    for name, amount in BUDGETS.items():
        conn.execute("INSERT OR IGNORE INTO budgets (category_id, amount, month) VALUES (?,?,NULL)",
                     (cat_ids[name], amount))

    # Lançamentos espalhados pelos últimos ~25 dias do mês atual.
    today = date.today()
    first = today.replace(day=1)
    fitid = 1000
    for cat, desc, lo, hi in SAMPLE_TX:
        n = random.randint(1, 4)
        for _ in range(n):
            day_offset = random.randint(0, (today - first).days)
            d = first + timedelta(days=day_offset)
            amount = round(random.uniform(lo, hi), 2)
            fitid += 1
            conn.execute(
                """INSERT OR IGNORE INTO transactions
                   (account_id, fitid, posted_on, amount, description, raw_memo, category_id)
                   VALUES (?,?,?,?,?,?,?)""",
                (account_id, str(fitid), d.isoformat(), amount, desc, desc, cat_ids[cat]),
            )

    # Salário do dia 5.
    fitid += 1
    conn.execute(
        """INSERT OR IGNORE INTO transactions
           (account_id, fitid, posted_on, amount, description, raw_memo, category_id)
           VALUES (?,?,?,?,?,?,?)""",
        (account_id, str(fitid), first.replace(day=5).isoformat(), 12000.0,
         "SALARIO EMPRESA XYZ", "SALARIO", cat_ids["Salário"]),
    )

    conn.commit()
    conn.close()
    print("Dados de exemplo inseridos. Rode:  python app.py")


if __name__ == "__main__":
    seed()
