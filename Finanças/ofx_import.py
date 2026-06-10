"""Leitor de arquivos OFX (extrato bancário e fatura de cartão).

OFX vem em dois sabores: 1.x (SGML, tags sem fechamento) e 2.x (XML).
Este parser baseado em regex lida com os dois, porque só nos interessam os
blocos <STMTTRN> (lançamentos), que têm estrutura previsível em ambos.

Não depende de bibliotecas externas de propósito — facilita rodar em qualquer
máquina sem instalar nada além do Flask.
"""
import re
from dataclasses import dataclass
from datetime import date


@dataclass
class OfxTransaction:
    fitid: str | None
    posted_on: str        # YYYY-MM-DD
    amount: float         # negativo = saída
    description: str
    raw_memo: str
    trntype: str


# Captura cada bloco de lançamento, tolerando ou não as tags de fechamento.
_TRN_BLOCK = re.compile(r"<STMTTRN>(.*?)(?:</STMTTRN>|(?=<STMTTRN>)|$)", re.IGNORECASE | re.DOTALL)


def _tag(block: str, name: str) -> str | None:
    """Extrai o valor de uma tag OFX, funcione ela em SGML ou XML."""
    m = re.search(rf"<{name}>([^<\r\n]*)", block, re.IGNORECASE)
    return m.group(1).strip() if m else None


def _parse_ofx_date(raw: str | None) -> str:
    """OFX usa YYYYMMDD[HHMMSS][.xxx][tz]. Pegamos só a data."""
    if not raw:
        return date.today().isoformat()
    digits = re.sub(r"[^0-9]", "", raw)[:8]
    if len(digits) < 8:
        return date.today().isoformat()
    return f"{digits[0:4]}-{digits[4:6]}-{digits[6:8]}"


def parse_ofx(content: str) -> list[OfxTransaction]:
    """Recebe o texto bruto do OFX e devolve a lista de lançamentos."""
    transactions: list[OfxTransaction] = []
    for block in _TRN_BLOCK.findall(content):
        amount_raw = _tag(block, "TRNAMT")
        if amount_raw is None:
            continue
        try:
            amount = float(amount_raw.replace(",", "."))
        except ValueError:
            continue

        name = _tag(block, "NAME") or ""
        memo = _tag(block, "MEMO") or ""
        # Bancos brasileiros às vezes usam só NAME, às vezes só MEMO.
        description = (name or memo or "Sem descrição").strip()
        raw_memo = " | ".join(p for p in (name, memo) if p).strip()

        transactions.append(
            OfxTransaction(
                fitid=_tag(block, "FITID"),
                posted_on=_parse_ofx_date(_tag(block, "DTPOSTED")),
                amount=amount,
                description=description,
                raw_memo=raw_memo,
                trntype=(_tag(block, "TRNTYPE") or "").upper(),
            )
        )
    return transactions


def read_ofx_file(raw_bytes: bytes) -> list[OfxTransaction]:
    """Decodifica os bytes do upload (OFX costuma ser latin-1 ou utf-8)."""
    for encoding in ("utf-8", "latin-1", "cp1252"):
        try:
            text = raw_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw_bytes.decode("utf-8", errors="replace")
    return parse_ofx(text)
