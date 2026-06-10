"""Categorização automática por regras de substring.

Cada regra diz: "se a descrição contém X, então categoria Y". A primeira
regra que casar (na ordem de prioridade) vence. Quando você corrige a
categoria de um lançamento na tela, o app pode criar uma regra nova para
acertar da próxima vez.
"""
from db import get_db


def categorize(description: str, rules: list) -> int | None:
    """Recebe a descrição e a lista de regras já ordenada; devolve category_id."""
    haystack = (description or "").lower()
    for rule in rules:
        if rule["pattern"].lower() in haystack:
            return rule["category_id"]
    return None


def load_rules(conn) -> list:
    return conn.execute(
        "SELECT pattern, category_id FROM rules ORDER BY priority ASC, length(pattern) DESC"
    ).fetchall()


def recategorize_uncategorized(conn) -> int:
    """Aplica as regras a todos os lançamentos ainda sem categoria. Devolve quantos foram marcados."""
    rules = load_rules(conn)
    if not rules:
        return 0
    pending = conn.execute(
        "SELECT id, description FROM transactions WHERE category_id IS NULL"
    ).fetchall()
    count = 0
    for tx in pending:
        cat = categorize(tx["description"], rules)
        if cat is not None:
            conn.execute("UPDATE transactions SET category_id = ? WHERE id = ?", (cat, tx["id"]))
            count += 1
    conn.commit()
    return count
