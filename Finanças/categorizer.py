"""Categorização automática por regras de substring.

Cada regra diz: "se a descrição contém X, então categoria Y". A primeira
regra que casar (na ordem de prioridade) vence. Quando você corrige a
categoria de um lançamento na tela, o app pode criar uma regra nova para
acertar da próxima vez.
"""
import re
import unicodedata

from db import get_db

# Prefixos genéricos de tipo de operação nos extratos (Itaú e afins). Não servem
# como palavra-chave de regra porque casam com lançamentos de naturezas distintas.
_GENERIC_PREFIXES = {
    "PAY", "PAG", "PAGTO", "PAGAMENTO", "PIX", "TED", "DOC", "SAQUE", "COMPRA",
    "TRANSF", "TRANSFERENCIA", "DEBITO", "CREDITO", "DEB", "CRED", "TARIFA",
    "QRS", "BOLETO", "REND",
}


def _ascii_upper(token: str) -> str:
    return unicodedata.normalize("NFKD", token).encode("ascii", "ignore").decode().upper()


def is_generic_pattern(pattern: str) -> bool:
    """True se o padrão é curto/genérico demais para virar regra (ex.: 'PIX', 'PAY').
    Esses prefixos casam com lançamentos de naturezas distintas e bagunçam tudo —
    nunca devem ser salvos como regra."""
    norm = _ascii_upper((pattern or "").strip())
    return not norm or norm in _GENERIC_PREFIXES or len(norm) < 3 or norm.isdigit()


def rule_keyword(description: str) -> str:
    """Extrai uma palavra-chave identificadora da descrição para virar regra.
    Pula prefixos genéricos de tipo de operação e números (datas/sequenciais),
    pegando o primeiro termo que de fato identifica o estabelecimento.
    Ex.: 'PAY UBER  17 01' -> 'UBER'; 'PAG BOLETO CONDOMINIO ...' -> 'CONDOMINIO'."""
    tokens = re.findall(r"[0-9A-Za-zÀ-ÿ.]+", description or "")
    for token in tokens:
        norm = _ascii_upper(token)
        if norm in _GENERIC_PREFIXES or norm.isdigit() or len(norm) < 3:
            continue
        return token[:24]
    return tokens[0][:24] if tokens else ""


def categorize(description: str, rules: list) -> int | None:
    """Recebe a descrição e a lista de regras já ordenada; devolve category_id."""
    haystack = (description or "").lower()
    for rule in rules:
        if rule["pattern"].lower() in haystack:
            return rule["category_id"]
    return None


def load_rules(conn) -> list:
    """Regras para categorização automática. NUNCA inclui regras que apontam para
    'Outros': por decisão do usuário, nada é auto-categorizado como Outros — essa
    categoria só pode ser atribuída manualmente."""
    return conn.execute(
        "SELECT r.pattern, r.category_id FROM rules r "
        "JOIN categories c ON c.id = r.category_id "
        "WHERE c.name != 'Outros' "
        "ORDER BY r.priority ASC, length(r.pattern) DESC"
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


def apply_rule_everywhere(conn, pattern: str, category_id: int) -> int:
    """Aplica UMA regra recém-criada a TODO o histórico, inclusive lançamentos que
    já tinham categoria — eles passam a seguir a regra nova. Não toca em
    transferências. Devolve quantos lançamentos foram atualizados."""
    needle = (pattern or "").lower()
    if not needle:
        return 0
    rows = conn.execute(
        "SELECT id, description, category_id FROM transactions WHERE transfer_to IS NULL"
    ).fetchall()
    count = 0
    for tx in rows:
        if needle in (tx["description"] or "").lower() and tx["category_id"] != category_id:
            conn.execute("UPDATE transactions SET category_id = ? WHERE id = ?", (category_id, tx["id"]))
            count += 1
    conn.commit()
    return count
