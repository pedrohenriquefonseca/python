"""
report_base.py — O cronograma como estava no último report gerado.

O comparativo do report semanal tem exatamente dois lados: o cronograma de agora
e o cronograma de quando o último report saiu. Não existe terceira data, então
não existe histórico a manter — existe UM estado por projeto, substituído a cada
report SALVO no histórico. Publicação de cronograma que não virou report não é
comparada com nada e não precisa ser guardada.

Salvo, e não gerado: a tela do report tem um toggle (ligado por padrão) que
decide se aquele relatório entra na história do projeto. Report tirado para
outro fim — conferir uma dúvida, uma reunião fora de época — passa sem tocar
nesta base, e o próximo comparativo continua partindo do último report salvo.

data/report_base_<pid>.json guarda QUATRO campos por tarefa: id, start, end e
duracao. São os únicos que a comparação lê do lado antigo — o pareamento é por
id (GUID estável entre publicações, imune a renomeação) e a variação é de datas
e de duração. Nome, recurso, nível e hierarquia saem sempre do cronograma
ATUAL, que é quem escreve o rótulo de cada linha do relatório; guardá-los aqui
seria copiar dado que ninguém lê.

`duracao` entrou depois dos outros três. Sem ela o lado antigo só tinha datas, e
o aumento de duração era medido pelo vão do calendário — o que promovia a
ofensor qualquer tarefa que tivesse escorregado para cima de um fim de semana ou
de um feriado sem ter esticado um dia sequer. Base gravada antes desta mudança
não tem o campo; o comparador volta ao vão do calendário enquanto for assim, e
cada base se corrige sozinha no próximo report salvo.

A ordem da lista é preservada porque o primeiro item é a tarefa-resumo do
projeto (nível 0), de onde saem o término e a duração totais.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

CAMPOS = ("id", "start", "end", "duracao")


def _caminho(pid: str) -> Path:
    return DATA_DIR / f"report_base_{pid}.json"


def carregar(pid: str) -> dict | None:
    """{pid, publicadoEm, geradoEm, tarefas} do último report — None se não há.

    Arquivo ilegível é tratado como ausente: o report sai sem o comparativo e a
    base é refeita na próxima geração. Não vale derrubar o relatório por causa
    do acessório.
    """
    p = _caminho(pid)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("report_base_%s.json ilegível (%s) — será refeito no "
                       "próximo report.", pid[:8], exc)
        return None


def data(base: dict) -> str:
    """Carimbo que descreve a base: a publicação do cronograma que ela retrata.

    Cai para o instante da geração quando o projeto não tem data de publicação —
    é o que datava o report anterior de qualquer forma.
    """
    return base.get("publicadoEm") or base.get("geradoEm") or ""


def gravar(pid: str, tarefas: list[dict], publicado_em: str | None) -> None:
    """Fixa o cronograma atual como base do próximo report.

    Chamada depois de o relatório ser montado, nunca antes: a base que entra na
    comparação é a do report ANTERIOR. E só quando o usuário decide salvar o
    report no histórico — quem chama é POST /api/report-base, não a geração.
    """
    conteudo = {
        "pid":         pid,
        "publicadoEm": publicado_em,
        "geradoEm":    datetime.now().isoformat(timespec="seconds"),
        "tarefas":     [{c: t.get(c) for c in CAMPOS} for t in tarefas],
    }
    DATA_DIR.mkdir(exist_ok=True)
    alvo = _caminho(pid)
    tmp  = alvo.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(conteudo, ensure_ascii=False), encoding="utf-8")
    tmp.replace(alvo)
    logger.info("Base do report fixada em %s — %d tarefas.",
                data(conteudo), len(conteudo["tarefas"]))
