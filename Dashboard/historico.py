"""
historico.py — Versionamento diferencial dos cronogramas.

Cada projeto tem um data/history_<pid>.json com até MAX_VERSOES versões, no
formato "1 base completa + deltas":

    base    → estado completo da versão mais antiga retida
    deltas  → apenas os campos que mudaram de uma versão para a seguinte

Uma versão nova só nasce quando algo muda de fato: se o cronograma foi
republicado sem alteração nos campos versionados, nada é escrito.

Cada versão é carimbada com o `publicadoEm` do projeto (LastPublishedDate com
hora), não com o instante da coleta — assim o atraso entre publicar e rodar o
fetcher não desloca a versão no tempo, e a busca por data acerta.

Quando a 16ª versão entra, o delta mais antigo é aplicado sobre a base antes de
sair. Guardar só deltas e descartar o mais antigo apagaria o estado das tarefas
que não mudam há muito tempo.

Hierarquia sem ordem global: cada tarefa guarda `parentId` em vez da posição na
lista. Assim uma inserção no meio do cronograma não reescreve o índice de todas
as tarefas seguintes. O que se perde é a ordem exata das linhas (a WBS) — o
comparador ordena por variação, não por posição.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR    = Path(__file__).parent / "data"
MAX_VERSOES = 15

# Campos versionados. Só o que não é recalculável a partir dos demais:
# `days`, `status` e `adh` são derivados e ficam de fora de propósito.
# `preds` entra porque mudança de rede é causa de atraso tanto quanto tarefa que
# esticou, e não dá para inferi-la depois.
CAMPOS_TAREFA  = ("name", "resources", "start", "end", "pct", "critical", "level",
                  "parentId", "preds", "marco")
CAMPOS_PROJETO = ("acStart", "acEnd", "pctConcluido")


# ── Estado corrente ───────────────────────────────────────────────────────────

def _parent_ids(tarefas: list[dict]) -> dict[str, str | None]:
    """Pai de cada tarefa: a anterior mais próxima com nível menor."""
    pais: dict[str, str | None] = {}
    pilha: list[tuple[int, str]] = []          # (nível, id)
    for t in tarefas:
        nivel = t.get("level") or 0
        while pilha and pilha[-1][0] >= nivel:
            pilha.pop()
        pais[str(t.get("id"))] = pilha[-1][1] if pilha else None
        pilha.append((nivel, str(t.get("id"))))
    return pais


def estado_atual(projeto: dict, tarefas: list[dict]) -> dict:
    """Reduz projeto + tarefas ao subconjunto versionado."""
    pais = _parent_ids(tarefas)
    return {
        "projeto": {c: projeto.get(c) for c in CAMPOS_PROJETO},
        "tarefas": {
            str(t.get("id")): {
                **{c: t.get(c) for c in CAMPOS_TAREFA if c != "parentId"},
                "parentId": pais.get(str(t.get("id"))),
            }
            for t in tarefas
        },
    }


# ── Diff / patch ──────────────────────────────────────────────────────────────

def _diff(anterior: dict, atual: dict) -> dict | None:
    """Delta de `anterior` para `atual`. None quando nada mudou.

    Em `tarefas`, o valor None marca tarefa removida; tarefa nova entra com
    todos os campos. Assim o patch é um único merge, sem caso especial.
    """
    proj = {c: atual["projeto"].get(c)
            for c in CAMPOS_PROJETO
            if atual["projeto"].get(c) != anterior["projeto"].get(c)}

    tarefas: dict[str, dict | None] = {}
    ant_t, atu_t = anterior["tarefas"], atual["tarefas"]
    for tid, novo in atu_t.items():
        velho = ant_t.get(tid)
        if velho is None:
            tarefas[tid] = dict(novo)                       # inserida
            continue
        mudou = {c: v for c, v in novo.items() if velho.get(c) != v}
        if mudou:
            tarefas[tid] = mudou
    for tid in ant_t:
        if tid not in atu_t:
            tarefas[tid] = None                             # removida

    if not proj and not tarefas:
        return None
    return {"projeto": proj, "tarefas": tarefas}


def _aplicar(estado: dict, delta: dict) -> dict:
    """Aplica um delta sobre um estado, devolvendo o estado seguinte."""
    projeto = {**estado["projeto"], **delta.get("projeto", {})}
    tarefas = {tid: dict(campos) for tid, campos in estado["tarefas"].items()}
    for tid, campos in (delta.get("tarefas") or {}).items():
        if campos is None:
            tarefas.pop(tid, None)
        else:
            tarefas[tid] = {**tarefas.get(tid, {}), **campos}
    return {"projeto": projeto, "tarefas": tarefas}


# ── Persistência ──────────────────────────────────────────────────────────────

def _caminho(pid: str) -> Path:
    return DATA_DIR / f"history_{pid}.json"


def _fundir_carimbos_repetidos(hist: dict) -> dict:
    """Funde deltas consecutivos que compartilham o mesmo carimbo.

    Autocorreção: carimbo duplicado tornaria reconstruir(versao) ambíguo, já que
    ele para no primeiro delta que casa. `registrar` não gera mais duplicatas,
    mas arquivos escritos antes disso podem tê-las.
    """
    deltas = hist.get("deltas") or []
    fundidos: list[dict] = []
    for d in deltas:
        if fundidos and fundidos[-1]["versao"] == d["versao"]:
            anterior = fundidos[-1]
            anterior["projeto"] = {**anterior.get("projeto", {}), **d.get("projeto", {})}
            tarefas = dict(anterior.get("tarefas") or {})
            for tid, campos in (d.get("tarefas") or {}).items():
                tarefas[tid] = None if campos is None else {
                    **(tarefas.get(tid) or {}), **campos}
            anterior["tarefas"]    = tarefas
            anterior["coletadoEm"] = d.get("coletadoEm") or anterior.get("coletadoEm")
        else:
            fundidos.append(d)
    # O primeiro delta pode repetir o carimbo da própria base: nesse caso ele é
    # dobrado nela, como na expiração por retenção.
    dobrados = 0
    while fundidos and fundidos[0]["versao"] == hist["base"]["versao"]:
        d = fundidos.pop(0)
        base = _aplicar({"projeto": hist["base"]["projeto"],
                         "tarefas": hist["base"]["tarefas"]}, d)
        hist["base"] = {"versao": d["versao"],
                        "coletadoEm": d.get("coletadoEm") or hist["base"].get("coletadoEm"),
                        **base}
        dobrados += 1

    if len(fundidos) != len(deltas) or dobrados:
        logger.info("Histórico normalizado: %d carimbo(s) duplicado(s) resolvido(s).",
                    len(deltas) - len(fundidos))
    hist["deltas"] = fundidos
    return hist


def carregar(pid: str) -> dict | None:
    p = _caminho(pid)
    if not p.exists():
        return None
    try:
        return _fundir_carimbos_repetidos(json.loads(p.read_text(encoding="utf-8")))
    except Exception as exc:
        logger.warning("history_%s.json ilegível (%s) — será recriado.", pid[:8], exc)
        return None


def _gravar(pid: str, hist: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    p   = _caminho(pid)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(hist, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


# ── API ───────────────────────────────────────────────────────────────────────

def versoes(pid: str, hist: dict | None = None) -> list[dict]:
    """Versões retidas, da mais antiga para a mais recente."""
    hist = hist if hist is not None else carregar(pid)
    if not hist:
        return []
    out = [{"versao": hist["base"]["versao"], "coletadoEm": hist["base"].get("coletadoEm")}]
    for d in hist.get("deltas", []):
        out.append({"versao": d["versao"], "coletadoEm": d.get("coletadoEm")})
    return out


def reconstruir(pid: str, versao: str | None = None, hist: dict | None = None) -> dict | None:
    """Estado completo do cronograma numa versão (a mais recente, por padrão)."""
    hist = hist if hist is not None else carregar(pid)
    if not hist:
        return None
    estado = {"projeto": dict(hist["base"]["projeto"]),
              "tarefas": {k: dict(v) for k, v in hist["base"]["tarefas"].items()}}
    if versao is not None and versao == hist["base"]["versao"]:
        return estado
    for d in hist.get("deltas", []):
        estado = _aplicar(estado, d)
        if versao is not None and d["versao"] == versao:
            return estado
    return estado if versao is None else None


def versao_em(pid: str, data: str, hist: dict | None = None) -> dict | None:
    """Versão vigente numa data — a mais recente publicada até `data` inclusive.

    `data` aceita 'YYYY-MM-DD' ou ISO com hora. Se a data for anterior a tudo
    que está retido, devolve None: a versão existiu, mas já saiu da janela, e
    responder com a mais antiga disponível seria apresentar um cronograma que
    não é o daquele dia.
    """
    vs = versoes(pid, hist)
    if not vs:
        return None
    limite = data if len(data) > 10 else data + "T23:59:59"
    candidatas = [v for v in vs if (v["versao"] or "") <= limite]
    return candidatas[-1] if candidatas else None


def registrar(pid: str, projeto: dict, tarefas: list[dict]) -> str | None:
    """Grava uma versão nova se algo mudou. Devolve o carimbo, ou None.

    O carimbo é o `publicadoEm` do projeto; sem ele, cai para o instante da
    coleta (projeto nunca publicado ou campo indisponível no PWA).
    """
    agora  = datetime.now().isoformat(timespec="seconds")
    carimbo = projeto.get("publicadoEm") or agora
    atual   = estado_atual(projeto, tarefas)
    hist    = carregar(pid)

    if not hist:
        _gravar(pid, {
            "pid":    pid,
            "base":   {"versao": carimbo, "coletadoEm": agora, **atual},
            "deltas": [],
        })
        logger.info("Histórico criado (%s) — %d tarefas.", carimbo, len(atual["tarefas"]))
        return carimbo

    # Carimbo repetido: o conteúdo mudou sem que o projeto fosse republicado.
    # Acontece quando o conjunto de campos versionados muda, ou se a coleta
    # anterior pegou um estado intermediário. Em vez de gravar duas versões com
    # o mesmo carimbo — o que tornaria reconstruir() ambíguo —, a última é
    # recalculada.
    if hist["deltas"] and hist["deltas"][-1]["versao"] == carimbo:
        descartado = hist["deltas"].pop()
        anterior   = reconstruir(pid, hist=hist)
        delta      = _diff(anterior, atual)
        if delta is None:
            _gravar(pid, hist)        # o último delta se anulou por completo
            logger.info("Versão %s revertida: o estado voltou ao anterior.", carimbo)
            return None
        delta.update({"versao": carimbo,
                      "coletadoEm": descartado.get("coletadoEm") or agora})
        hist["deltas"].append(delta)
        _gravar(pid, hist)
        logger.info("Versão %s recalculada (mesmo carimbo).", carimbo)
        return carimbo

    if not hist["deltas"] and hist["base"]["versao"] == carimbo:
        hist["base"] = {"versao": carimbo,
                        "coletadoEm": hist["base"].get("coletadoEm") or agora, **atual}
        _gravar(pid, hist)
        logger.info("Base %s recalculada (mesmo carimbo).", carimbo)
        return carimbo

    anterior = reconstruir(pid, hist=hist)
    delta    = _diff(anterior, atual)
    if delta is None:
        return None

    delta.update({"versao": carimbo, "coletadoEm": agora})
    hist["deltas"].append(delta)

    # Retenção: ao passar do limite, o delta mais antigo é dobrado na base.
    while 1 + len(hist["deltas"]) > MAX_VERSOES:
        antigo = hist["deltas"].pop(0)
        base   = _aplicar({"projeto": hist["base"]["projeto"],
                           "tarefas": hist["base"]["tarefas"]}, antigo)
        hist["base"] = {"versao": antigo["versao"],
                        "coletadoEm": antigo.get("coletadoEm"), **base}

    _gravar(pid, hist)
    n_t = sum(1 for v in delta["tarefas"].values() if v is not None)
    n_r = sum(1 for v in delta["tarefas"].values() if v is None)
    logger.info("Versão %s registrada — %d tarefa(s) alterada(s), %d removida(s), "
                "%d campo(s) do projeto.", carimbo, n_t, n_r, len(delta["projeto"]))
    return carimbo


def como_lista(estado: dict) -> list[dict]:
    """Converte o estado reconstruído em lista de tarefas, na ordem hierárquica.

    A ordem exata da WBS não é versionada (ver docstring do módulo); esta é uma
    ordem estável derivada de parentId + nível, suficiente para montar caminhos
    e identificar folhas.
    """
    tarefas = estado["tarefas"]
    filhos: dict[str | None, list[str]] = {}
    for tid, t in tarefas.items():
        filhos.setdefault(t.get("parentId"), []).append(tid)
    for lista in filhos.values():
        lista.sort(key=lambda tid: (tarefas[tid].get("name") or "", tid))

    out: list[dict] = []

    def desce(pai: str | None):
        for tid in filhos.get(pai, []):
            out.append({"id": tid, **tarefas[tid]})
            desce(tid)

    desce(None)
    # Órfãs (pai fora do estado) não podem sumir do resultado.
    vistos = {t["id"] for t in out}
    for tid, t in tarefas.items():
        if tid not in vistos:
            out.append({"id": tid, **t})
    return out
