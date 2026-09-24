# -*- coding: utf-8 -*-
"""Quem tem o quê na mão, lido da estrutura de tópicos do cronograma.

A triagem corre dentro de cada tarefa pai — o documento, com suas etapas em fila
(a, Análise 01, 0, b...). De cada documento sai o ponto em que a fila está: o que
está em andamento agora e a etapa que vem em seguida. Documento parado em análise
do Cliente continua no relatório: a etapa seguinte já tem data no cronograma, e é
ela que o fornecedor precisa ver chegando.

Fora de tudo, em qualquer projeto: tarefa do Cliente, tarefa inativa e marco. A
primeira não é nossa; a segunda o Project nem agenda; a terceira não tem duração.

Este módulo só decide *quais* tarefas entram e de quem é a parentela delas. Quem
recorta por fornecedor, agrupa e escreve é o report_fornecedores.
"""
import datetime

RECURSO_CLIENTE = "cliente"          # mesma triagem do report semanal


def _inativa(t):
    """Tarefa desativada no Project.

    O Project não agenda inativa, não deixa ela empurrar ninguém e não a executa:
    é escopo que existe no arquivo e não existe no trabalho. Cobrar um fornecedor
    por ela é cobrar por algo que foi tirado do projeto de propósito. Some do
    relatório inteiro, como já some da Análise de Saúde.

    O campo entrou no snapshot depois dos demais. Onde ele não existe, ninguém é
    inativa e a triagem sai como sempre saiu — daí o `is False`, e não `not`.
    """
    return t.get("ativa") is False


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
    recurso é a folha, e é dela que o relatório fala. Todo o resto entra — o
    relatório não pergunta a que grupo o recurso pertence, só se ele não é o
    Cliente.

    Marco também não entra. Duração zero não é trabalho na mão de ninguém — é a
    data em que alguma coisa se fecha —, e um relatório de entregas que anuncia
    "Término da Iniciativa" como próxima tarefa do fornecedor está cobrando dele
    o calendário, não o desenho. Marco costuma vir sem recurso e cair fora
    sozinho, mas nos cronogramas em que a própria casa assina esses pontos ele
    tem recurso e precisa desta linha.

    Inativa também não entra, pelo motivo de `_inativa`.

    A varredura vê a lista inteira, e não só o que passa: a parentela é
    posicional — o ancestral é a linha anterior mais próxima naquele nível —, e
    pular linhas aqui remontaria a hierarquia errada.
    """
    saida = []
    for i, t in enumerate(tarefas):
        r = (t.get("resources") or "").strip()
        if not r or RECURSO_CLIENTE in r.lower() or t.get("marco") or _inativa(t):
            continue
        anc = hierarquia(tarefas, i)
        saida.append({
            "recurso": r, "nome": str(t.get("name", "")),
            "bisavo": _nome(tarefas, anc[1]), "avo": _nome(tarefas, anc[2]),
            "pai": _nome(tarefas, anc[3]),
            "inicio": _data(t.get("start")), "termino": _data(t.get("end")),
            "pct": t.get("pct") or 0, "ordem": i,
            "pai_idx": _indice_pai(tarefas, i),
        })
    return saida


def _mais_proximas(abertas, referencia):
    """As tarefas que começam mais perto de uma data — todas as que empatam.

    "Mais perto" vale nas duas direções: etapa que devia ter começado semana
    passada é tão a próxima quanto a que começa amanhã, e escolher só para a
    frente esconderia justamente a que está atrasada. Datas iguais entram juntas
    porque um pacote de projeto anda em bloco — a mesma pessoa toca vários
    documentos ao mesmo tempo, e separar um do outro seria arbitrário.
    """
    if not abertas:
        return []
    dia = min(abertas, key=lambda x: (abs((x["inicio"] - referencia).days),
                                      x["inicio"]))["inicio"]
    return [x for x in abertas if x["inicio"] == dia]


def escolher(itens, hoje):
    """As tarefas do relatório, decididas documento a documento.

    Cada documento mostra o ponto em que sua fila está:

      - com trabalho em andamento, vão todas as etapas em andamento — um pacote
        anda em bloco — mais a etapa seguinte, a que começa mais perto de quando
        esse trabalho termina. O fornecedor vê o que tem na mão e o que vem
        atrás, sem precisar abrir o cronograma;
      - sem nada em andamento, vai só a etapa seguinte: a que começa mais perto
        de hoje.

    Com mais de uma etapa em andamento no mesmo documento, a referência é o
    término mais distante entre elas: a fila só segue depois que a última fecha.
    """
    por_pai = {}
    for x in itens:
        por_pai.setdefault(x["pai_idx"], []).append(x)

    escolhidas = []
    for grupo in por_pai.values():
        andamento = [x for x in grupo if 0 < x["pct"] < 100]
        abertas = [x for x in grupo if x["pct"] == 0 and x["inicio"]]

        if andamento:
            escolhidas += andamento
            fins = [x["termino"] for x in andamento if x["termino"]]
            escolhidas += _mais_proximas(abertas, max(fins) if fins else hoje)
        else:
            escolhidas += _mais_proximas(abertas, hoje)

    return sorted(escolhidas, key=lambda x: (x["inicio"] or datetime.date.max,
                                             x["termino"] or datetime.date.max,
                                             x["ordem"]))
