# -*- coding: utf-8 -*-
"""Report Fornecedores — as próximas entregas de cada fornecedor de projeto.

Lê o mesmo snapshot do PWA que alimenta os dashboards (data/tasks_<id>.json) e
devolve, para a tela, o que cada fornecedor tem na mão: a etapa em
desenvolvimento agora e a etapa que vem em seguida.

A triagem — quais tarefas entram e de quem é a parentela delas — mora em
`triagem.py`, ao lado. Este módulo responde pelo recorte e pelo arranjo.

  Recorte:     todo recurso do cronograma que não seja o Cliente. Marco e tarefa
               inativa não entram: uma é data e não entrega, a outra o Project
               nem agenda (`triagem.py`).
  Arranjo:     fornecedor › iniciativa › disciplina › entregas, com iniciativas e
               disciplinas na ordem do arquivo do Project.
  Agrupamento: documentos da mesma disciplina que andam na mesma revisão e nas
               mesmas datas viram uma linha só. Um pacote de projeto anda em
               bloco, e no Palhano isso reduz 149 documentos a 39 linhas — a
               diferença entre uma tela que se lê e uma lista que se rola.

O que o fornecedor recebe por e-mail é uma imagem, desenhada em `imagem.py` ao
lado. A versão em HTML que existia aqui morreu colada no Outlook: o Word remonta
a tabela com as regras dele, ignorou a largura das células e quebrou cada código
de documento no hífen. A régua — escala e conversão de data em pixel — ficou
neste módulo, para os dois desenhos lerem o cronograma da mesma maneira.
"""
import calendar
import datetime
import json
import os

import triagem

# Recurso→cor é do Cronograma de Alocação, e é de lá que este relatório lê —
# mesma pessoa e mesma cor em todo o dashboard. Só leitura: quem escreve nesse
# arquivo é a tela de alocação. O mapa de grupos não entra na conta: o recorte
# aqui é por recurso, e quem não for o Cliente tem entrega a acompanhar.
_AQUI      = os.path.dirname(os.path.abspath(__file__))
_ALOCACAO  = os.path.join(os.path.dirname(_AQUI), "cronograma_alocacao")
ARQ_CORES  = os.path.join(_ALOCACAO, "cores_fornecedores.json")

COR_PADRAO = "#64748b"          # fornecedor ainda sem cor no mapa de alocação


def _ler_json(caminho, padrao):
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return padrao


def _iso(d):
    return d.isoformat() if d else None


# ── Arranjo ───────────────────────────────────────────────────────────────────

def _linhas(itens, hoje):
    """Agrupa em linhas o que anda junto, e ordena o que está em curso primeiro.

    A chave é revisão + datas: dois documentos da mesma disciplina que começam e
    terminam no mesmo dia, na mesma revisão, são o mesmo pacote de trabalho.
    """
    grupos = {}
    for x in itens:
        chave = (x["nome"], _iso(x["inicio"]), _iso(x["termino"]), x["pct"])
        grupos.setdefault(chave, []).append(x)

    saida = []
    for (etapa, inicio, termino, pct), docs in grupos.items():
        andamento = 0 < pct < 100
        fim   = docs[0]["termino"]
        ini   = docs[0]["inicio"]
        atraso = bool(andamento and fim and fim < hoje)
        saida.append({
            "documentos": [d["pai"] or d["nome"] for d in docs],
            "etapa":      etapa,
            "inicio":     inicio,
            "termino":    termino,
            "pct":        pct,
            "estado":     "andamento" if andamento else "a_iniciar",
            "atrasada":   atraso,
            # Dias até a data que interessa em cada estado: o término de quem já
            # está trabalhando, o início de quem ainda vai começar.
            "dias":       ((fim if andamento else ini) - hoje).days
                          if (fim if andamento else ini) else None,
            "ordem":      min(d["ordem"] for d in docs),
        })
    return sorted(saida, key=lambda l: (l["estado"] != "andamento",
                                        l["inicio"] or "9999", l["ordem"]))


def arvore(tarefas, hoje):
    """O relatório inteiro, já arranjado: um nó por fornecedor."""
    escolhidas = triagem.escolher(triagem.candidatos(tarefas), hoje)

    cores = _ler_json(ARQ_CORES, {})

    por_forn = {}
    for x in escolhidas:
        (por_forn.setdefault(x["recurso"], {})
                 .setdefault(x["bisavo"] or "—", {})
                 .setdefault(x["avo"] or "—", []).append(x))

    saida = []
    for forn, inis_cru in por_forn.items():
        inis = []
        for ini, discs_cru in inis_cru.items():
            discs = []
            for disc, xs in discs_cru.items():
                linhas = _linhas(xs, hoje)
                discs.append({
                    "nome":       disc,
                    "documentos": sum(len(l["documentos"]) for l in linhas),
                    "linhas":     linhas,
                    "ordem":      min(x["ordem"] for x in xs),
                })
            discs.sort(key=lambda d: d["ordem"])     # ordem do arquivo do Project
            inis.append({
                "nome":        ini,
                "disciplinas": discs,
                "documentos":  sum(d["documentos"] for d in discs),
                "ordem":       min(d["ordem"] for d in discs),
            })
        inis.sort(key=lambda i: i["ordem"])

        todas = [l for i in inis for d in i["disciplinas"] for l in d["linhas"]]
        saida.append({
            "nome":        forn,
            "cor":         cores.get(forn, COR_PADRAO),
            "iniciativas": inis,
            "documentos":  sum(len(l["documentos"]) for l in todas),
            "disciplinas": len({d["nome"] for i in inis for d in i["disciplinas"]}),
            "andamento":   sum(len(l["documentos"]) for l in todas
                               if l["estado"] == "andamento"),
            "atrasados":   sum(len(l["documentos"]) for l in todas if l["atrasada"]),
            "proxima":     min((l["inicio"] for l in todas if l["inicio"]), default=None),
            "linhas":      len(todas),
        })

    # Quem tem trabalho em andamento primeiro; depois quem larga antes. É a ordem
    # em que o PMO precisa olhar: o que já está rodando, e o que vem em seguida.
    saida.sort(key=lambda f: (-f["andamento"], f["proxima"] or "9999", f["nome"]))
    return saida


# ── A régua do gantt ──────────────────────────────────────────────────────────
# A escala e a conversão de data em pixel vivem aqui porque são de quem lê o
# cronograma, não de quem desenha: a tela as reescreve em JavaScript e o
# `imagem.py` as importa daqui. Mudar a régua num lugar só é o que impede os dois
# desenhos de divergirem.

_MESES = ("jan", "fev", "mar", "abr", "mai", "jun",
          "jul", "ago", "set", "out", "nov", "dez")


def _br(iso):
    if not iso:
        return "—"
    return datetime.date.fromisoformat(iso).strftime("%d/%m/%y")


def entregas(forn):
    """Todas as linhas de um fornecedor, sem a hierarquia."""
    return [l for i in forn["iniciativas"] for d in i["disciplinas"]
            for l in d["linhas"]]


def escala(forn):
    """Os meses que as entregas deste fornecedor ocupam — a régua dele.

    Uma régua por fornecedor, cobrindo só os meses em que ele tem entrega. O que
    se lê nela é o paralelismo entre as tarefas dele, e uma escala comum a todos
    espremeria cada relatório no tamanho do pior caso.
    """
    linhas = entregas(forn)
    inicios = [l["inicio"] for l in linhas if l["inicio"]]
    fins    = [l["termino"] for l in linhas if l["termino"]]
    if not inicios or not fins:
        return None
    a = datetime.date.fromisoformat(min(inicios))
    b = datetime.date.fromisoformat(max(fins))
    n = (b.year - a.year) * 12 + (b.month - a.month) + 1
    t = a.month - 1 + n - 1
    uy, um = a.year + t // 12, t % 12 + 1
    return {"ano": a.year, "mes": a.month, "n": n,
            "de":  datetime.date(a.year, a.month, 1),
            "ate": datetime.date(uy, um, calendar.monthrange(uy, um)[1])}


def posicao(esc, d, w, fim_do_dia=False):
    """Em que pixel de uma régua de `w` px a data cai.

    Todo mês tem a mesma largura: a diferença entre 28 e 31 dias não muda a
    leitura e deixa as divisas caírem em contas redondas. Uma ponta de término
    anda até o fim do dia — etapa que fecha no dia 31 fecha no fim do mês, e não
    um dia antes dele.
    """
    dia = d.day if fim_do_dia else d.day - 1
    i = ((d.year - esc["ano"]) * 12 + (d.month - esc["mes"])
         + dia / calendar.monthrange(d.year, d.month)[1])
    return int(round(min(max(i / esc["n"], 0.0), 1.0) * w))


# ── A lista em texto puro ───────────────────────────────────────
# Vai no clipboard junto com a imagem: quem colar num campo sem formatação
# recebe esta, e não um retangulo vazio.

def texto(forn, nome_projeto, hoje):
    """A mesma lista em texto puro, para quem colar num campo sem formatação."""
    L = [f'Próximas entregas — {forn["nome"]}',
         f'{nome_projeto} · posição do cronograma em {hoje:%d/%m/%Y}',
         f'{forn["documentos"]} documentos · {forn["andamento"]} em andamento · '
         f'{forn["documentos"] - forn["andamento"]} a iniciar', ""]
    for ini in forn["iniciativas"]:
        L += [ini["nome"].upper(), ""]
        for disc in ini["disciplinas"]:
            if disc["nome"].strip().casefold() != ini["nome"].strip().casefold():
                L.append(f'  {disc["nome"]} ({disc["documentos"]} documentos)')
            for l in disc["linhas"]:
                sit = (f'em andamento, {l["pct"]}%' if l["estado"] == "andamento"
                       else "a iniciar")
                if l["atrasada"]:
                    sit += f', {-l["dias"]} d em atraso'
                L.append(f'    rev. {l["etapa"]} · {_br(l["inicio"])} a '
                         f'{_br(l["termino"])} · {sit}')
                L.append(f'      {" · ".join(l["documentos"])}')
            L.append("")
    return "\n".join(L)


# ── Porta de entrada ──────────────────────────────────────────────────────────

def analisar(tarefas, nome_projeto, hoje=None):
    """O relatório inteiro em JSON, pronto para a tela desenhar."""
    if not tarefas:
        raise ValueError("Projeto sem tarefas disponíveis no snapshot do PWA.")
    hoje = hoje or datetime.date.today()

    fornecedores = arvore(tarefas, hoje)
    # A lista em texto acompanha o JSON: é leve, e é ela que vai para o
    # clipboard junto com a imagem, para quem colar num campo sem formatação.
    for f in fornecedores:
        f["texto"] = texto(f, nome_projeto, hoje)

    todas = [l for f in fornecedores for i in f["iniciativas"]
             for d in i["disciplinas"] for l in d["linhas"]]
    documentos = sum(len(l["documentos"]) for l in todas)
    andamento  = sum(len(l["documentos"]) for l in todas if l["estado"] == "andamento")

    return {
        "projeto": nome_projeto,
        "hoje":    hoje.isoformat(),
        "fornecedores":  fornecedores,
        "kpis": {
            "fornecedores": len(fornecedores),
            "disciplinas":  len({d["nome"] for f in fornecedores
                                 for i in f["iniciativas"] for d in i["disciplinas"]}),
            "documentos":   documentos,
            "linhas":       len(todas),
            "andamento":    andamento,
            "aIniciar":     documentos - andamento,
            "fornecedoresAndamento": sum(1 for f in fornecedores if f["andamento"]),
            # Vence em até 7 dias: só conta o que já está em curso — o que ainda
            # não começou não tem entrega para vencer.
            "vence7":       sum(len(l["documentos"]) for l in todas
                                if l["estado"] == "andamento"
                                and l["dias"] is not None and 0 <= l["dias"] <= 7),
            "atrasados":    sum(len(l["documentos"]) for l in todas if l["atrasada"]),
            "proximaLargada": min((l["inicio"] for l in todas
                                   if l["estado"] != "andamento" and l["inicio"]),
                                  default=None),
        },
    }
