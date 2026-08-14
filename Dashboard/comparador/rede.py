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

O que funciona é caminhar para trás pelos vínculos a partir da tarefa que
termina junto com o projeto, seguindo em cada passo a predecessora cujo
deslocamento explica o da sucessora. A cobertura de vínculos é alta (89–100%
das folhas têm predecessora) e a aderência também (86–100% dos FS são coerentes
com as datas), o que sustenta a afirmação de que A empurrou B sem depender de o
cronograma inteiro ser um CPM conectado.

Ofensor é quem AUMENTOU A DURAÇÃO dentro dessa cadeia. Tarefa que só foi
deslocada por inteiro herdou o atraso, não o produziu.

Tolerância de dias
------------------
As datas são de calendário e os vínculos são em dias úteis. Um empurrão de 5
dias úteis aparece como 7 corridos, e feriados deslocam mais. Por isso o
casamento entre o deslocamento de uma tarefa e o da sua predecessora usa
TOL_DIAS de folga em vez de exigir igualdade exata.
"""
from __future__ import annotations

from datetime import date

TOL_DIAS = 3        # folga ao casar deslocamentos (dias úteis vs corridos)
MAX_SALTOS = 8      # marcos encadeados que empurrador() atravessa


def _dias(a: str | None, b: str | None) -> int | None:
    if not a or not b:
        return None
    try:
        ya, ma, da = map(int, a.split("-")); yb, mb, db = map(int, b.split("-"))
        return (date(yb, mb, db) - date(ya, ma, da)).days
    except (ValueError, AttributeError):
        return None


# ── Índice ────────────────────────────────────────────────────────────────────

def indexar(tarefas: list[dict]) -> dict:
    """Índice por id. `tarefas` no formato bruto do snapshot (com `preds`).

    Guarda também a lista na ordem original: a hierarquia do MSP é posicional
    (as filhas vêm logo depois da mãe, com nível maior), e é assim que se acha
    a filha que manda no término de um resumo.
    """
    return {"por_id": {str(t["id"]): t for t in tarefas if t.get("id")},
            "ordem":  list(tarefas)}


def folhas(tarefas: list[dict]) -> set[str]:
    """Ids das tarefas-folha. Depende da ordem hierárquica da lista."""
    out = set()
    for i, t in enumerate(tarefas):
        prox = tarefas[i + 1] if i + 1 < len(tarefas) else None
        if prox is None or (prox.get("level") or 0) <= (t.get("level") or 0):
            out.add(str(t["id"]))
    return out


def _respeitado(pred: dict, sucessora: dict, vinculo: dict) -> bool:
    """O vínculo é coerente com as datas? (só FS tem verificação direta)

    A checagem só vale em tarefa NÃO INICIADA, onde a data ainda é plano. Depois
    que a tarefa começou a data é fato: entrar com início real antes do fim da
    predecessora é sobreposição de obra, não erro de lógica, e o vínculo continua
    valendo como trilha de causa. Medido em 13/08/26 nos 16 cronogramas: das 223
    ligações FS incoerentes, 223 tinham a sucessora já iniciada — descartar todas
    elas cegava a análise sem motivo.
    """
    if vinculo.get("tipo") != "FS":
        return True
    if (sucessora.get("pct") or 0) > 0:
        return True
    if not (pred.get("end") and sucessora.get("start")):
        return False
    return sucessora["start"] >= pred["end"]


def _descendentes(sid: str, idx: dict) -> list[dict]:
    """Tarefas sob `sid` na hierarquia — o bloco contíguo de nível maior."""
    ordem = idx.get("ordem") or []
    pos = next((i for i, t in enumerate(ordem) if str(t.get("id")) == sid), None)
    if pos is None:
        return []
    nivel = ordem[pos].get("level") or 0
    saida = []
    for t in ordem[pos + 1:]:
        if (t.get("level") or 0) <= nivel:
            break
        saida.append(t)
    return saida


def _condutora(sid: str, deltas: dict[str, dict], idx: dict) -> tuple[str, dict] | None:
    """A filha que manda no término do resumo `sid`.

    Resumo não tem variação própria — ele espelha as filhas, e por isso fica fora
    dos deltas (senão contaria duas vezes). Só que o vínculo do cronograma pode
    apontar para ele, e aí a caminhada morria ali: no Pirajuçara isso deixou 5
    dos 6 dias de atraso sem dono. Quem realmente empurra é a filha que termina
    junto com o resumo; é ela que a caminhada passa a seguir.
    """
    p = idx["por_id"].get(sid)
    if not p or not p.get("end"):
        return None
    candidatas = [(str(t["id"]), deltas[str(t["id"])])
                  for t in _descendentes(sid, idx)
                  if t.get("end") == p["end"] and deltas.get(str(t["id"]))]
    if not candidatas:
        return None
    # Entre as que terminam junto, a que mais se deslocou é a que explica o resumo.
    return max(candidatas, key=lambda c: abs(c[1].get("dfim") or 0))


# ── Causalidade ───────────────────────────────────────────────────────────────

def empurrador(tid: str, deltas: dict[str, dict], idx: dict,
               _saltos: int = 0) -> dict | None:
    """Qual predecessora empurrou esta tarefa.

    Candidata é a predecessora cujo término se deslocou no mesmo sentido e com
    magnitude parecida à do início desta tarefa, ligada por vínculo respeitado.
    Entre as compatíveis, vence a de maior deslocamento.
    """
    v = deltas.get(tid)
    if not v or not v.get("dini"):
        return None
    t = idx["por_id"].get(tid)
    if not t:
        return None

    candidatas = []
    for pr in t.get("preds") or []:
        pid = str(pr["id"])
        p  = idx["por_id"].get(pid)
        dv = deltas.get(pid)
        if p and not dv:
            # Predecessora sem delta é resumo: segue pela filha que o comanda.
            alt = _condutora(pid, deltas, idx)
            if alt:
                pid, dv = alt
                p = idx["por_id"].get(pid)
        if not p or not dv or not dv.get("dfim") or not _respeitado(p, t, pr):
            continue
        if dv["dfim"] * v["dini"] > 0 and abs(dv["dfim"] - v["dini"]) <= TOL_DIAS:
            candidatas.append((abs(dv["dfim"]), pid, p, dv))
    if not candidatas:
        return None

    candidatas.sort(reverse=True, key=lambda c: c[0])
    _, pid, p, dv = candidatas[0]

    # Marco tem duração zero: nunca gera atraso, só transmite. Apontá-lo
    # esconderia a causa, que está atrás dele.
    if p.get("marco") and _saltos < MAX_SALTOS:
        atras = empurrador(pid, deltas, idx, _saltos + 1)
        if atras:
            return atras
    return {"id": pid, "nome": p.get("name"), "recurso": p.get("resources") or "",
            "dfim": dv["dfim"], "ddur": dv.get("ddur"), "marco": bool(p.get("marco"))}


def causa_do_prazo(saldo: int | None, fim_atual: str | None,
                   deltas: dict[str, dict], idx: dict,
                   ids_folha: set[str] | None = None) -> dict:
    """Cadeia que leva ao término do projeto, e quem esticou dentro dela.

    Percorre a cadeia inteira em vez de parar no primeiro que esticou: o atraso
    costuma ser a soma de vários aumentos pequenos na mesma cadeia.

    A tarefa-resumo do projeto compartilha o término com o projeto e não pode
    ser tomada como marco final — daí `ids_folha`. E `saldo` vem calculado de
    fora, das listas normalizadas.
    """
    if not saldo:
        return {"saldo": saldo or 0, "tipo": "sem_mudanca", "cadeia": [], "geradores": []}

    finais = [t for t in idx["por_id"].values()
              if t.get("end") == fim_atual
              and (ids_folha is None or str(t["id"]) in ids_folha)]
    if not finais:
        return {"saldo": saldo, "tipo": "indeterminado", "cadeia": [], "geradores": []}

    # Preferir a que o Project marcou como crítica, se houver.
    final = next((t for t in finais if t.get("critical")), finais[0])

    cadeia: list[dict] = []
    atual, vistos = final, set()
    while atual and str(atual["id"]) not in vistos:
        tid = str(atual["id"])
        vistos.add(tid)
        v = deltas.get(tid)
        if v:
            cadeia.append({"id": tid, "nome": atual.get("name"),
                           "recurso": atual.get("resources") or "",
                           "marco": bool(atual.get("marco")),
                           "ddur": v.get("ddur"), "dini": v.get("dini"),
                           "dfim": v.get("dfim")})
        emp = empurrador(tid, deltas, idx)
        atual = idx["por_id"].get(emp["id"]) if emp else None

    # Maior aumento primeiro. No empate vence quem está mais atrás na cadeia:
    # entre duas contribuições iguais, a de montante é a origem.
    # Os mesmos dicts da cadeia, não cópias — quem consome enriquece a cadeia
    # com rótulo e datas, e os geradores precisam enxergar esse enriquecimento.
    pos = {id(c): i for i, c in enumerate(cadeia)}
    geradores = sorted([c for c in cadeia if not c["marco"] and (c["ddur"] or 0) > 0],
                       key=lambda c: (-(c["ddur"] or 0), -pos[id(c)]))
    return {"saldo": saldo,
            "tipo": "propagacao" if geradores else "indeterminado",
            "cadeia": cadeia, "geradores": geradores}
