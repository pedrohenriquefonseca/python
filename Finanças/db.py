"""Camada de acesso ao banco SQLite.

Mantém o schema e helpers simples de conexão. Nada de ORM: sqlite3 puro
para deixar o app leve e fácil de inspecionar.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "financas.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    type        TEXT NOT NULL DEFAULT 'checking',  -- checking | credit | investment
    bank        TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name    TEXT NOT NULL UNIQUE,
    color   TEXT NOT NULL DEFAULT '#6b7280',
    kind    TEXT NOT NULL DEFAULT 'expense'  -- expense | income | transfer
);

CREATE TABLE IF NOT EXISTS rules (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern     TEXT NOT NULL,          -- substring (case-insensitive) a procurar na descrição
    category_id INTEGER NOT NULL,
    priority    INTEGER NOT NULL DEFAULT 100,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id  INTEGER NOT NULL,
    fitid       TEXT,                   -- id único do lançamento vindo do OFX
    posted_on   TEXT NOT NULL,          -- YYYY-MM-DD
    amount      REAL NOT NULL,          -- negativo = saída, positivo = entrada
    description TEXT NOT NULL,
    raw_memo    TEXT,
    category_id INTEGER,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (account_id)  REFERENCES accounts(id)   ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    UNIQUE (account_id, fitid)
);

CREATE TABLE IF NOT EXISTS budgets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL,
    amount      REAL NOT NULL,          -- teto mensal (valor positivo em R$)
    month       TEXT,                   -- NULL = padrão recorrente; 'YYYY-MM' = override do mês
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE (category_id, month)
);

CREATE INDEX IF NOT EXISTS idx_tx_posted ON transactions(posted_on);
CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id);
"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Banco inicializado em {DB_PATH}")
