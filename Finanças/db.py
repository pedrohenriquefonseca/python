"""Camada de acesso ao banco SQLite.

Mantém o schema e helpers simples de conexão. Nada de ORM: sqlite3 puro
para deixar o app leve e fácil de inspecionar.
"""
import hashlib
import re
import sqlite3
import unicodedata
from pathlib import Path

DB_PATH = Path(__file__).parent / "financas.db"


def _norm_desc(text: str) -> str:
    """Normaliza a descrição para comparação estável entre exportações:
    remove acentos, pontuação e variações de espaço; tudo em maiúsculas."""
    text = text or ""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", " ", text).strip().upper()


def tx_fingerprint(posted_on: str, amount: float, description: str) -> str:
    """Impressão digital de conteúdo de um lançamento (independe do FITID).
    Usa data + valor em centavos + descrição normalizada."""
    cents = int(round(float(amount) * 100))
    key = f"{posted_on}|{cents}|{_norm_desc(description)}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    type            TEXT NOT NULL DEFAULT 'checking',  -- checking | credit | investment
    bank            TEXT,
    opening_balance REAL NOT NULL DEFAULT 0,           -- saldo inicial; saldo atual = este + soma dos lançamentos
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS assets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT 'Outros',  -- Imóvel | Veículo | Investimento | Outros
    value       REAL NOT NULL DEFAULT 0,         -- valor atual em R$ (positivo)
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
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
    ignored     INTEGER NOT NULL DEFAULT 0,   -- 1 = ignorado: fora de orçamentos, gráficos, saldo e net worth
    transfer_to INTEGER,                       -- se preenchido: transferência; conta destino creditada automaticamente
    fingerprint TEXT,                          -- impressão digital de conteúdo (dedup quando não há FITID)
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


# Colunas adicionadas após a versão inicial. Bancos antigos recebem essas colunas
# automaticamente (sem recriar a tabela, preservando os dados existentes).
MIGRATIONS = {
    "accounts": [("opening_balance", "REAL NOT NULL DEFAULT 0")],
    "transactions": [
        ("ignored", "INTEGER NOT NULL DEFAULT 0"),
        ("transfer_to", "INTEGER"),
        ("fingerprint", "TEXT"),
    ],
}


def _migrate(conn) -> None:
    """Garante que tabelas pré-existentes tenham as colunas novas e calcula
    a impressão digital de lançamentos antigos (para a dedup funcionar com eles)."""
    for table, columns in MIGRATIONS.items():
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
        for name, decl in columns:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")

    # Backfill da impressão digital onde estiver ausente.
    pendentes = conn.execute(
        "SELECT id, posted_on, amount, description FROM transactions WHERE fingerprint IS NULL"
    ).fetchall()
    for r in pendentes:
        conn.execute(
            "UPDATE transactions SET fingerprint = ? WHERE id = ?",
            (tx_fingerprint(r["posted_on"], r["amount"], r["description"]), r["id"]),
        )


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)  # cria tabelas/índices que faltam (inclui 'assets')
    _migrate(conn)              # adiciona colunas novas a bancos antigos, sem perder dados
    # Índice da impressão digital só pode ser criado após a coluna existir (migração acima).
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_fp ON transactions(account_id, fingerprint)")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Banco inicializado em {DB_PATH}")
