# -*- coding: utf-8 -*-
"""Quem tem o quê na mão, lido da estrutura de tópicos do cronograma.

A triagem corre dentro de cada tarefa pai — o documento, com suas etapas em fila
(a, Análise 01, 0, b...). De cada documento sai o ponto em que a fila está: as
etapas nossas em desenvolvimento e, nos documentos que ainda não começaram, a
próxima etapa nossa. Documento parado em análise do Cliente não aparece: a bola
não é nossa, e anunciar a etapa seguinte cobraria alguém por trabalho travado.

Este módulo só decide *quais* tarefas entram e de quem é a parentela delas. Quem
recorta por fornecedor, agrupa e escreve é o report_fornecedores.
"""
import datetime

RECURSO_CLIENTE = "cliente"          # mesma triagem do report semanal


# ── Leitura da estrutura de tópicos ───────────────────────────────────────────

def _nivel(t):
    n = t.get("level")
    return t.get("outlineLevel") if n is None else n


def hierarquia(tarefas, i):
    """{1: linha do bisavô, 2: linha do avô, 3: linha do pai} — None onde não há.

    Mesma leitura de Report.buscar_hierarquia: a estrutura de tópicos é a
    parentela, e o ancestral de cada nível é a linha anterior mais próxima
    naquele nível. Devolve a linha, não o nome, porque o relatório precisa das
    duas coisas: o nome para escrever e o número da linha para ordenar os grupos
    como estão no Project.
    """
    meu = _nivel(tarefas[i])
    idx = {n: None for n in (1, 2, 3) if n < meu}
    for j in range(i - 1, -1, -1):
        n = _nivel(tarefas[j])
        if n in idx and idx[n] is None:
            idx[n] = j
            if all(v is not None for v in idx.values()):
                break
    return {n: idx.get(n) for n in (1, 2, 3)}


def _indice_pai(tarefas, i):
    """Linha do pai imediato: a anterior mais próxima um nível acima.

    É o documento (nível 3) para as etapas de revisão (nível 4), mas serve em
    qualquer profundidade. Sem pai — projeto e primeiro nível — a própria linha
    responde por si.
    """
    alvo = _nivel(tarefas[i]) - 1
    if alvo < 0:
        return i
    for j in range(i - 1, -1, -1):
        if _nivel(tarefas[j]) == alvo:
            return j
    return i


def _nome(tarefas, j):
    return "" if j is None else str(tarefas[j].get("name", ""))


def _data(v):
    try:
        return datetime.date.fromisoformat(str(v)[:10])
    except (ValueError, TypeError):
        return None


# ── Triagem ───────────────────────────────────────────────────────────────────

def candidatos(tarefas):
    """Linhas com recurso próprio (nem Cliente, nem vazio), com a parentela.

    Recurso vazio já elimina as tarefas-resumo e a linha do projeto: quem recebe
    recurso é a folha, e é dela que o relatório fala.
    """
    saida = []
    for i, t in enumerate(tarefas):
        r = (t.get("resources") or "").strip()
        if not r or RECURSO_CLIENTE in r.lower():
            continue
        anc = hierarquia(tarefas, i)
        saida.append({
            "recurso": r, "nome": str(t.get("name", "")),
            "bisavo": _nome(tarefas, anc[1]), "avo": _nome(tarefas, anc[2]),
            "pai": _nome(tarefas, anc[3]),
            "inicio": _data(t.get("start")), "termino": _data(t.get("end")),
            "pct": t.get("pct") or 0, "marco": bool(t.get("marco")), "ordem": i,
            "pai_idx": _indice_pai(tarefas, i),
        })
    return saida


def pais_na_mao_do_cliente(tarefas):
    """Documentos com uma etapa do Cliente em curso.

    Enquanto a análise está com ele, a bola não é nossa: anunciar a etapa
    seguinte como próxima tarefa da equipe cobraria alguém por trabalho que ainda
    não pode começar. O documento inteiro sai do relatório.
    """
    travados = set()
    for i, t in enumerate(tarefas):
        r = (t.get("resources") or "").lower()
        if RECURSO_CLIENTE in r and 0 < (t.get("pct") or 0) < 100:
            travados.add(_indice_pai(tarefas, i))
    return travados


def escolher(itens, hoje, travados=frozenset()):
    """As tarefas do relatório, decididas documento a documento.

    Em desenvolvimento manda porque é o que está na mão agora, e vão todas: um
    pacote de projeto anda em bloco, com a mesma pessoa tocando vários documentos
    ao mesmo tempo. Sem nenhuma em andamento no documento, vale a próxima etapa
    nossa — "mais perto de hoje" nas duas direções, que etapa atrasada é tão a
    próxima quanto a que começa amanhã — e datas empatadas entram juntas.

    Etapa do Cliente não é candidata; se estiver em curso, tranca o documento
    (`travados`) e ele sai inteiro.
    """
    por_pai = {}
    for x in itens:
        if x["pai_idx"] in travados:
            continue
        por_pai.setdefault(x["pai_idx"], []).append(x)

    escolhidas = []
    for grupo in por_pai.values():
        andamento = [x for x in grupo if 0 < x["pct"] < 100]
        if andamento:
            escolhidas += andamento
            continue
        abertas = [x for x in grupo if x["pct"] == 0 and x["inicio"]]
        if not abertas:
            continue
        dia = min(abertas, key=lambda x: (abs((x["inicio"] - hoje).days),
                                          x["inicio"]))["inicio"]
        escolhidas += [x for x in abertas if x["inicio"] == dia]

    return sorted(escolhidas, key=lambda x: (x["inicio"] or datetime.date.max,
                                             x["termino"] or datetime.date.max,
                                             x["ordem"]))
