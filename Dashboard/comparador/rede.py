"""
rede.py — Quem causou o deslocamento do término, pela rede de dependências.

Por que não há cálculo de caminho crítico aqui
----------------------------------------------
A tentação seria reconstruir o CPM e distribuir o atraso ao longo da cadeia
crítica. Medido nos 17 cronogramas da Horizontes, não se sustenta:

  - as tarefas-folha marcadas como críticas cobrem de 3% a 17% do prazo do
    projeto na maioria dos casos (Vila Gilda 8%, Brasilândia 3%);
  - a UBS Santa Rita não tem nenhuma folha crítica;
  - andar do término para trás pelos vínculos percorre a cadeia inteira em
    apenas 7 dos 17 projetos.

O motivo é que esses cronogramas são ancorados por data contratual: o marco
final é fixo, então quase tudo antes dele tem folga e o Project marca pouca
coisa como crítica. Atribuir dias "ao longo da cadeia crítica" produziria
números que parecem precisos e não são.

O que funciona é partir das tarefas que terminam junto com o projeto e subir
pelos vínculos que ESTÃO EMPURRANDO. Ofensor é quem AUMENTOU A DURAÇÃO nessa
rede. Tarefa que só foi deslocada por inteiro herdou o atraso, não o produziu.

Rede, e não trilha
------------------
A primeira versão subia por UMA predecessora a cada passo, e depois passou a
anotar as empatadas sem subir por elas. Isso falhou no 9225 (MPPA Alves
Ribeiro): seis disciplinas correm em ramos paralelos (1a Emissão → Análise →
Atendimento → Análise), a 1a Emissão de cada uma esticou 18 dias úteis e as seis
terminam juntas no fim do projeto. A caminhada escolheu a primeira folha final, a
do Concreto, e o report acusou uma disciplina e absolveu cinco idênticas.

Então a busca é uma varredura: todas as folhas que terminam com o projeto são
pontos de partida, e de cada tarefa ela sobe por TODOS os vínculos que a
empurraram, sem escolher vencedora. Uma causa paralela não tem vencedora.

Quando um vínculo empurrou
--------------------------
Três condições, todas no vínculo:

  1. o lado da sucessora que o vínculo governa andou para depois (o início no
     FS e no SS, o término no FF e no SF);
  2. o lado da predecessora que o vínculo lê também andou para depois (o
     término no FS e no FF, o início no SS e no SF);
  3. o vínculo está justo HOJE: a sucessora está onde o vínculo a coloca, sem
     folga entre as duas (`_apertado`).

A primeira versão pedia, no lugar da 3, que os dois deslocamentos tivessem o
mesmo tamanho. Isso perdia a predecessora que andou 10 dias quando a sucessora,
que tinha 5 de folga, andou só 5: ela empurrou, e a folga engoliu a outra metade.
A folga medida nas datas de hoje não depende dessa coincidência.

A folga é contada em dias úteis, com os feriados nacionais descontados, e o lag
do vínculo (que o pwa_client já entrega em dias úteis) entra na conta. Como o
snapshot não traz o calendário do projeto, feriado municipal e recesso da
empresa ficariam de fora: por isso a tolerância de um dia útil (TOL_UTEIS).
Medido nos cronogramas em 24/09/26, os vãos de um dia útil nos vínculos FS sem
lag caem em 12/10, 02/11 e 20/11, e também em 26/10, que não é nacional.

O lado por onde se chega importa
--------------------------------
Uma tarefa alcançada pelo TÉRMINO (FS e FF) empurrou com o término, então a
duração dela conta: se esticou, é ofensora. Alcançada pelo INÍCIO (SS e SF), ela
empurrou antes de a duração entrar em cena, e o aumento dela não afetou quem
estava à frente. Ela continua na varredura porque as predecessoras dela podem
ter empurrado o início.

Resumos, marcos e tarefas novas
-------------------------------
- Vínculo com um resumo empurra as filhas que coincidem com ele: no término,
  as que terminam no mesmo dia; no início, as que começam no mesmo dia. Todas,
  não só a primeira. E o vínculo que o Project põe num resumo vale para as
  filhas, então a varredura lê também os vínculos dos ancestrais de cada tarefa.
- Marco não tem duração: transmite o deslocamento e nunca é ofensor.
- Tarefa incluída desde o último report não tem par na base. Se ela está no
  caminho, a duração inteira dela foi acrescida ao prazo: entra como ofensora,
  com a sua própria linha.
- Tarefa cuja duração não pôde ser comparada (unidade trocada, campo ausente) e
  que está no caminho é nomeada, sem número. Some da lista só a que também não
  esticou no calendário: essa só foi arrastada.
"""
from __future__ import annotations

from datetime import date, timedelta
from functools import lru_cache

TOL_UTEIS = 1       # folga tolerada num vínculo "justo" (feriado fora do nacional)


def _dias(a: str | None, b: str | None) -> int | None:
    if not a or not b:
        return None
    try:
        ya, ma, da = map(int, a.split("-")); yb, mb, db = map(int, b.split("-"))
        return (date(yb, mb, db) - date(ya, ma, da)).days
    except (ValueError, AttributeError):
        return None


def _data(s: str | None) -> date | None:
    try:
        y, m, d = map(int, s.split("-"))
        return date(y, m, d)
    except (ValueError, AttributeError):
        return None


# ── Calendário ────────────────────────────────────────────────────────────────

@lru_cache(maxsize=None)
def _feriados(ano: int) -> frozenset[date]:
    """Feriados nacionais, e Carnaval e Corpus Christi, que o escritório não trabalha."""
    # Páscoa pelo algoritmo de Meeus/Jones/Butcher.
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 19 * l) // 433
    mes = (h + l - 7 * m + 90) // 25
    pascoa = date(ano, mes, (h + l - 7 * m + 33 * mes + 19) % 32)
    fixos = [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15),
             (11, 20), (12, 25)]
    moveis = [-48, -47, -2, 60]   # Carnaval (seg e ter), Sexta Santa, Corpus Christi
    return frozenset([date(ano, mm, dd) for mm, dd in fixos]
                     + [pascoa + timedelta(n) for n in moveis])


def _util(d: date) -> bool:
    return d.weekday() < 5 and d not in _feriados(d.year)


def _uteis(a: date, b: date) -> int:
    """Dias úteis em (a, b], com sinal: negativo quando `b` vem antes de `a`."""
    if b == a:
        return 0
    ini, fim, sinal = (a, b, 1) if b > a else (b, a, -1)
    n, x = 0, ini + timedelta(1)
    while x <= fim:
        n += _util(x)
        x += timedelta(1)
    return sinal * n


# ── Índice ────────────────────────────────────────────────────────────────────

def indexar(tarefas: list[dict]) -> dict:
    """Índice por id. `tarefas` no formato bruto do snapshot (com `preds`).

    A hierarquia do MSP é posicional (as filhas vêm logo depois da mãe, com
    nível maior): daí a lista na ordem original, a posição de cada tarefa e os
    ancestrais, que são por onde os vínculos de resumo chegam às filhas.
    """
    por_id, pos, pais = {}, {}, {}
    pilha: list[tuple[int, str]] = []
    for i, t in enumerate(tarefas):
        if not t.get("id"):
            continue
        tid, nivel = str(t["id"]), t.get("level") or 0
        while pilha and pilha[-1][0] >= nivel:
            pilha.pop()
        por_id[tid], pos[tid] = t, i
        pais[tid] = [p for _, p in pilha]
        pilha.append((nivel, tid))
    return {"por_id": por_id, "ordem": list(tarefas), "pos": pos, "pais": pais}


def folhas(tarefas: list[dict]) -> set[str]:
    """Ids das tarefas-folha. Depende da ordem hierárquica da lista."""
    out = set()
    for i, t in enumerate(tarefas):
        prox = tarefas[i + 1] if i + 1 < len(tarefas) else None
        if prox is None or (prox.get("level") or 0) <= (t.get("level") or 0):
            out.add(str(t["id"]))
    return out


def _descendentes(sid: str, idx: dict) -> list[dict]:
    """Tarefas sob `sid` na hierarquia — o bloco contíguo de nível maior."""
    ordem = idx.get("ordem") or []
    pos = idx.get("pos", {}).get(sid)
    if pos is None:
        return []
    nivel = ordem[pos].get("level") or 0
    saida = []
    for t in ordem[pos + 1:]:
        if (t.get("level") or 0) <= nivel:
            break
        saida.append(t)
    return saida


# ── Vínculos ──────────────────────────────────────────────────────────────────
# Qual data de cada ponta o vínculo liga: (lado da predecessora, lado da sucessora).
LADOS = {"FS": ("fim", "ini"), "SS": ("ini", "ini"),
         "FF": ("fim", "fim"), "SF": ("ini", "fim")}
_CAMPO = {"ini": "start", "fim": "end"}
_DELTA = {"ini": "dini", "fim": "dfim"}


def _apertado(pred: dict, suc: dict, tipo: str, lag: float) -> bool:
    """A sucessora está onde o vínculo a põe, sem folga (até TOL_UTEIS)?

    No FS a sucessora começa no dia útil SEGUINTE ao término da predecessora,
    daí o -1: vão zero é "dia útil seguinte". Nos outros tipos as duas datas
    coincidem. Vão negativo (sobreposição) conta como justo: é tarefa já
    iniciada, ou lag negativo, e quem filtra isso é o deslocamento.
    """
    lp, ls = LADOS[tipo]
    a, b = _data(pred.get(_CAMPO[lp])), _data(suc.get(_CAMPO[ls]))
    if not a or not b:
        return False
    vao = _uteis(a, b) - (1 if tipo in ("FS", "SF") else 0)
    return vao <= (lag or 0) + TOL_UTEIS


# ── Causalidade ───────────────────────────────────────────────────────────────

def causa_do_prazo(saldo: int | None, fim_atual: str | None,
                   deltas: dict[str, dict], idx: dict,
                   ids_folha: set[str] | None = None,
                   novas: set[str] | frozenset = frozenset()) -> dict:
    """A rede que leva ao término do projeto, e quem esticou dentro dela.

    `deltas` traz, por id, o deslocamento de início e término (dini, dfim) de
    TODAS as tarefas pareadas, resumos inclusive; nas folhas, também a variação
    de duração (ddur, unidade) ou o motivo de ela não existir. `novas` são as
    tarefas sem par na base. `saldo` vem calculado de fora.

    Devolve `cadeia` (toda tarefa alcançada, na ordem da varredura) e
    `geradores` (as ofensoras, ordenadas para o report). Cada ofensora tem
    `tipo`: "aumento", "nova" ou "sem_medida".
    """
    if not saldo:
        return {"saldo": saldo or 0, "tipo": "sem_mudanca", "cadeia": [], "geradores": []}

    por_id = idx["por_id"]
    folha = ids_folha if ids_folha is not None else folhas(idx["ordem"])

    def ativa(tid: str) -> bool:
        t = por_id.get(tid)
        return bool(t) and t.get("ativa") is not False

    def andou(tid: str, lado: str) -> bool:
        if tid in novas:
            return True
        return ((deltas.get(tid) or {}).get(_DELTA[lado]) or 0) > 0

    # Todas as folhas que terminam com o projeto: se várias terminam juntas,
    # todas seguram o término, e escolher uma era o erro do 9225.
    fila = [(tid, "fim", 0) for tid, t in por_id.items()
            if t.get("end") == fim_atual and tid in folha and ativa(tid)
            and andou(tid, "fim")]
    if not fila:
        return {"saldo": saldo, "tipo": "indeterminado", "cadeia": [], "geradores": []}

    nos: dict[str, dict] = {}
    vistos: set[tuple[str, str]] = set()
    while fila:
        tid, lado, prof = fila.pop(0)
        if (tid, lado) in vistos:
            continue
        vistos.add((tid, lado))
        t = por_id[tid]

        if tid not in folha:
            # Resumo: quem empurra são as filhas que coincidem com ele no lado
            # por onde se chegou. Os vínculos do próprio resumo são lidos pelas
            # filhas, via ancestrais, logo abaixo.
            campo = _CAMPO[lado]
            for f in _descendentes(tid, idx):
                fid = str(f.get("id"))
                if (fid in folha and ativa(fid) and f.get(campo) == t.get(campo)
                        and andou(fid, lado)):
                    fila.append((fid, lado, prof + 1))
            continue

        no = nos.get(tid)
        if no is None:
            v = deltas.get(tid) or {}
            no = nos[tid] = {
                "id": tid, "nome": t.get("name"), "recurso": t.get("resources") or "",
                "marco": bool(t.get("marco")), "nova": tid in novas,
                "ddur": v.get("ddur"), "dini": v.get("dini"), "dfim": v.get("dfim"),
                "unidade": v.get("unidade") or t.get("duracaoUn"),
                "motivo": v.get("motivo"), "duracao": t.get("duracao"),
                "prof": prof, "pelo_fim": False}
        no["pelo_fim"] |= lado == "fim"
        no["prof"] = max(no["prof"], prof)

        # Os vínculos da tarefa e os dos resumos acima dela. Chegando pelo
        # início, só contam os que governam o início (FS e SS).
        vinculos = list(t.get("preds") or [])
        for anc in idx["pais"].get(tid, []):
            vinculos += por_id[anc].get("preds") or []
        for pr in vinculos:
            tipo = pr.get("tipo")
            if tipo not in LADOS:
                continue
            lp, ls = LADOS[tipo]
            if lado == "ini" and ls != "ini":
                continue
            pid = str(pr["id"])
            p = por_id.get(pid)
            if (p and ativa(pid) and andou(tid, ls) and andou(pid, lp)
                    and _apertado(p, t, tipo, pr.get("lag") or 0)):
                fila.append((pid, lp, prof + 1))

    cadeia = list(nos.values())
    geradores = []
    for c in cadeia:
        if c["marco"] or not c["pelo_fim"]:
            continue
        if c["nova"]:
            c["tipo"] = "nova"
        elif (c["ddur"] or 0) > 0:
            c["tipo"] = "aumento"
        elif c["motivo"] and (c["dfim"] or 0) > (c["dini"] or 0):
            c["tipo"] = "sem_medida"
        else:
            continue
        geradores.append(c)

    # Maior peso primeiro; no empate, quem está mais a montante (a origem), e
    # depois o nome, para a ordem não depender da ordem do dicionário. Dia
    # corrido pesa 5/7 de dia útil: é o que permite ordenar as duas unidades
    # juntas. Sem medida vai para o fim — não tem número para ordenar.
    def peso(c: dict) -> float:
        if c["tipo"] == "sem_medida":
            return -1
        n = (c["duracao"] if c["tipo"] == "nova" else c["ddur"]) or 0
        return n * 5 / 7 if c["unidade"] == "corrido" else n

    geradores.sort(key=lambda c: (-peso(c), -c["prof"], c["nome"] or ""))
    return {"saldo": saldo,
            "tipo": "propagacao" if geradores else "indeterminado",
            "cadeia": cadeia, "geradores": geradores}
