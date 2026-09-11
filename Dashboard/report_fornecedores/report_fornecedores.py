# -*- coding: utf-8 -*-
"""Report Fornecedores — as próximas entregas de cada fornecedor de projeto.

Lê o mesmo snapshot do PWA que alimenta os dashboards (data/tasks_<id>.json) e
devolve, para a tela, o que cada fornecedor tem na mão: a etapa em
desenvolvimento agora e, nos documentos que ainda não começaram, a próxima etapa
dele.

A triagem — quais tarefas entram e de quem é a parentela delas — mora em
`triagem.py`, ao lado. Este módulo responde pelo recorte e pelo arranjo.

  Recorte:     só quem está em `Fornecedores` no grupos_recursos.json. Horizontes
               fica de fora, porque este relatório é sobre terceiros.
  Arranjo:     fornecedor › iniciativa › disciplina › entregas, com iniciativas e
               disciplinas na ordem do arquivo do Project.
  Agrupamento: documentos da mesma disciplina que andam na mesma revisão e nas
               mesmas datas viram uma linha só. Um pacote de projeto anda em
               bloco, e no Palhano isso reduz 149 documentos a 39 linhas — a
               diferença entre uma tela que se lê e uma lista que se rola.

Cada fornecedor sai com uma versão do próprio relatório pronta para colar no
corpo de um e-mail do Outlook (`email`), gerada aqui e não no browser: o HTML que
sobrevive ao motor do Word não é o mesmo que a tela usa, e manter os dois lados
no mesmo lugar evita que um mude sem o outro.
"""
import datetime
import html
import json
import os

import triagem

GRUPO_FORNECEDOR = "Fornecedores"

# Em boa parte dos cronogramas a própria casa é o recurso de várias tarefas, com
# o nome da empresa no lugar do nome de alguém. Ela não está no mapa de grupos —
# lá só entram pessoas — e sem esta linha apareceria como recurso por classificar
# em todo projeto.
CASA = {"horizontes"}

# Recurso→grupo e recurso→cor são do Cronograma de Alocação, e é de lá que este
# relatório os lê — mesma pessoa, mesma cor e mesmo grupo em todo o dashboard.
# Só leitura: quem escreve nesses arquivos é a tela de alocação.
_AQUI      = os.path.dirname(os.path.abspath(__file__))
_ALOCACAO  = os.path.join(os.path.dirname(_AQUI), "cronograma_alocacao")
ARQ_GRUPOS = os.path.join(_ALOCACAO, "grupos_recursos.json")
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


# ── Triagem ───────────────────────────────────────────────────────────────────

def _fornecedores_do_snapshot(itens, grupos):
    """(itens de fornecedor, recursos sem grupo definido).

    Recurso fora do mapa não entra: chutar que todo desconhecido é fornecedor
    colocaria gente da casa no relatório de terceiros. Ele volta na resposta
    para a tela poder avisar que falta classificar alguém.
    """
    sim, desconhecidos = [], set()
    for x in itens:
        recurso = x["recurso"].strip()
        if recurso.casefold() in CASA:
            continue
        grupo = grupos.get(recurso)
        if grupo is None:
            desconhecidos.add(recurso)
        elif grupo == GRUPO_FORNECEDOR:
            sim.append(x)
    return sim, sorted(desconhecidos)


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
    """(fornecedores, recursos sem grupo) — o relatório inteiro, já arranjado."""
    itens = triagem.candidatos(tarefas)
    grupos = _ler_json(ARQ_GRUPOS, {})
    itens, desconhecidos = _fornecedores_do_snapshot(itens, grupos)
    escolhidas = triagem.escolher(itens, hoje, triagem.pais_na_mao_do_cliente(tarefas))

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
    return saida, desconhecidos


# ── Versão para colar no Outlook ──────────────────────────────────────────────
# O corpo do e-mail no Outlook é o editor do Word, e colar HTML nele não é abrir
# uma página: o Word remonta tudo com as regras dele. Colado de verdade no Word,
# o desenho anterior (um <div> de título e uma tabela por iniciativa) saía
# desmontado. Daí as regras abaixo, cada uma vinda de um defeito visto:
#
#   - Uma tabela só, com a largura de cada coluna fixa. Tabelas separadas saem
#     cada uma com as colunas numa largura, e o e-mail perde o alinhamento.
#   - Fonte declarada em cada célula. O Word não leva o font-family de um <div>
#     para dentro da tabela.
#   - Nada de margem ou borda em <div>: some. Respiro é linha de altura fixa,
#     faixa é bgcolor na célula.
#   - Maiúscula escrita no texto e nada de letter-spacing ou text-transform.
#   - Um código de documento por linha. Na mesma linha o Word quebra o código
#     no hífen.
#   - Cinza nunca mais claro que #6b7280: no Outlook o #94a3b8 some.
#
# Por isso nada aqui reaproveita o CSS da tela — são duas linguagens diferentes.

_FONTE    = "font-family:'Segoe UI',Arial,sans-serif;"
_LARGURAS = (250, 62, 70, 70, 188)        # documentos, etapa, início, término, situação
_FIO      = "border-bottom:1px solid #e3e7ec;"


def _br(iso):
    if not iso:
        return "—"
    return datetime.date.fromisoformat(iso).strftime("%d/%m/%y")


def _td(conteudo, estilo="", largura=None, colspan=None, fundo=None):
    attrs = "".join(f' {k}="{v}"' for k, v in
                    (("width", largura), ("colspan", colspan), ("bgcolor", fundo)) if v)
    return f'<td valign="top"{attrs} style="{_FONTE}{estilo}">{conteudo}</td>'


def _faixa(conteudo, estilo="", fundo=None):
    """Linha que ocupa a tabela inteira: título, iniciativa, disciplina, rodapé."""
    return f"<tr>{_td(conteudo, estilo, colspan=len(_LARGURAS), fundo=fundo)}</tr>"


def _respiro(px):
    return (f'<tr><td colspan="{len(_LARGURAS)}" height="{px}" '
            f'style="font-size:1px;line-height:1px;">&nbsp;</td></tr>')


def email(forn, nome_projeto, hoje):
    """HTML de uma mensagem pronta para o corpo de um e-mail do Outlook."""
    E = html.escape
    a_iniciar = forn["documentos"] - forn["andamento"]
    P = [f'<table cellpadding="0" cellspacing="0" border="0" width="{sum(_LARGURAS)}" '
         f'style="border-collapse:collapse;">',
         _faixa(f'Próximas entregas &mdash; {E(forn["nome"])}',
                "font-size:15pt;font-weight:bold;color:#111827;"),
         _faixa(f'{E(str(nome_projeto))} &nbsp;&middot;&nbsp; posição do cronograma '
                f'em {hoje:%d/%m/%Y}', "font-size:9pt;color:#4b5563;"),
         _faixa(f'<b>{forn["documentos"]}</b> documentos &nbsp;&middot;&nbsp; '
                f'<b>{forn["andamento"]}</b> em andamento &nbsp;&middot;&nbsp; '
                f'<b>{a_iniciar}</b> a iniciar',
                "font-size:9pt;color:#111827;padding-top:2pt;"),
         _respiro(12)]

    cab = ("font-size:7.5pt;font-weight:bold;color:#4b5563;padding:0 6pt 3pt 6pt;"
           "border-bottom:1.5px solid #111827;")
    P.append("<tr>" + "".join(_td(t, cab, w) for t, w in zip(
        ("DOCUMENTOS", "ETAPA", "INÍCIO", "TÉRMINO", "SITUAÇÃO"), _LARGURAS)) + "</tr>")

    celula = "font-size:9pt;color:#111827;padding:4pt 6pt;" + _FIO
    apagada = celula + "color:#4b5563;"
    for ini in forn["iniciativas"]:
        P.append(_respiro(10))
        P.append(_faixa(E(ini["nome"]), "font-size:10pt;font-weight:bold;color:#111827;"
                        "padding:4pt 6pt;", fundo="#e8ecf1"))
        for disc in ini["disciplinas"]:
            # Disciplina com o nome da iniciativa só repetiria a faixa logo acima.
            if disc["nome"].strip().casefold() != ini["nome"].strip().casefold():
                P.append(_faixa(E(disc["nome"]), "font-size:8pt;font-weight:bold;"
                                "color:#374151;padding:8pt 6pt 0 6pt;"))
            for l in disc["linhas"]:
                if l["estado"] == "andamento":
                    sit = (f'<b>Em andamento</b> <span style="color:#6b7280;">'
                           f'&middot; {l["pct"]}%</span>')
                    if l["atrasada"]:
                        sit += (f'<br><span style="color:#b91c1c;font-weight:bold;">'
                                f'{-l["dias"]} d em atraso</span>')
                else:
                    sit = '<span style="color:#4b5563;">A iniciar</span>'
                P.append("<tr>"
                         + _td("<br>".join(E(d) for d in l["documentos"]), celula,
                               _LARGURAS[0])
                         + _td(f'rev. {E(l["etapa"])}', apagada, _LARGURAS[1])
                         + _td(_br(l["inicio"]), apagada, _LARGURAS[2])
                         + _td(f'<b>{_br(l["termino"])}</b>', celula, _LARGURAS[3])
                         + _td(sit, celula, _LARGURAS[4])
                         + "</tr>")

    P.append(_respiro(10))
    P.append(_faixa("Lista extraída do cronograma publicado no Project Online. Para cada "
                    "documento consta a etapa em desenvolvimento e, quando nenhuma está "
                    "em curso, a próxima etapa prevista. Documentos em análise do cliente "
                    "não entram nesta lista.", "font-size:8pt;color:#6b7280;"))
    P.append("</table>")
    return "".join(P)


# ── Porta de entrada ──────────────────────────────────────────────────────────

def analisar(tarefas, nome_projeto, hoje=None):
    """O relatório inteiro em JSON, pronto para a tela desenhar."""
    if not tarefas:
        raise ValueError("Projeto sem tarefas disponíveis no snapshot do PWA.")
    hoje = hoje or datetime.date.today()

    fornecedores, desconhecidos = arvore(tarefas, hoje)
    for f in fornecedores:
        f["email"] = email(f, nome_projeto, hoje)

    todas = [l for f in fornecedores for i in f["iniciativas"]
             for d in i["disciplinas"] for l in d["linhas"]]
    documentos = sum(len(l["documentos"]) for l in todas)
    andamento  = sum(len(l["documentos"]) for l in todas if l["estado"] == "andamento")

    return {
        "projeto": nome_projeto,
        "hoje":    hoje.isoformat(),
        "desconhecidos": desconhecidos,
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
