"""
comparador.py — Compara duas versões de um cronograma e explica o que mudou.

Produz a seção "O que mudou entre X e Y?" do report semanal, que entra logo
depois do resumo e responde:

  - o término e a duração do projeto mudaram quanto?
  - quem causou o atraso (Principais Ofensores)?
  - o que mais variou sem afetar o prazo (Maiores Variações)?

Três decisões de método valem registro:

Culpa não é o mesmo que variação. Uma tarefa pode ter o término deslocado 10
dias tendo produzido apenas 2 — os outros 8 herdou da predecessora. Ofensor é
quem AUMENTOU A DURAÇÃO dentro da cadeia que chega ao término do projeto; quem
só foi deslocado por inteiro não entra.

As duas listas são mutuamente exclusivas, e é isso que torna o rótulo "slack
positivo" verdadeiro: Maiores Variações traz as maiores variações ENTRE AS
TAREFAS FORA da cadeia — variaram sem mover o prazo, logo tinham folga. As duas
listas costumam discordar, e a discordância é o ponto: no Vila Gilda a maior
variação do cronograma (+14 d) não é ofensora, enquanto tarefas de +8, +2 e +1
dia movem o prazo.

Marcos (duração zero) ficam fora das listas: não têm duração para esticar nem
recurso a quem atribuir. Seguem visíveis para rede.py, que precisa deles como
conduíte da propagação.

As duas versões vêm do histórico (data/history_<pid>.json) e do snapshot atual
do PWA — os dois lados têm GUID de tarefa, então o pareamento é por id.
"""
from __future__ import annotations

from datetime import date

TOPO_LISTA     = 3   # tarefas em Maiores Variações
TOPO_OFENSORES = 3   # tarefas em Principais Ofensores


# ── Normalização ──────────────────────────────────────────────────────────────

def _com_caminho(itens: list[dict]) -> list[dict]:
    """Anota o caminho hierárquico e marca as folhas. Espera ordem hierárquica.

    O caminho existe para o relatório: `Análise` e `R01` se repetem dezenas de
    vezes no mesmo cronograma e sem os ancestrais não há como distingui-las.
    """
    pilha: dict[int, str] = {}
    for it in itens:
        n = it["nivel"]
        pilha[n] = it["nome"]
        for k in [k for k in pilha if k > n]:
            del pilha[k]
        it["caminho"] = tuple(pilha[k] for k in sorted(pilha))
        it["niveis"]  = tuple(sorted(pilha))
    for i, it in enumerate(itens):
        it["folha"] = (i + 1 >= len(itens)) or (itens[i + 1]["nivel"] <= it["nivel"])
    return itens


def hierarquia(t: dict) -> tuple[str, str, str]:
    """(bisavô, avô, pai) — os três ancestrais mais próximos.

    O Report.py procura por nível fixo (1, 2 e 3); aqui a busca é relativa, o
    que dá o mesmo resultado nas tarefas de nível 4 (a maioria) e continua
    correto nas mais rasas, onde o nível fixo pegaria um ramo alheio.

    A linha de nível 0 é o próprio projeto: ancestral de tudo, não identifica
    nada, e por isso fica de fora — uma tarefa de nível 1 aparece só com o
    próprio nome.
    """
    caminho, niveis = t.get("caminho") or (), t.get("niveis") or ()
    anc = [nome for nome, nv in zip(caminho[:-1], niveis[:-1]) if nv > 0][-3:]
    while len(anc) < 3:
        anc.insert(0, "")
    return anc[0], anc[1], anc[2]


def rotulo(t: dict) -> str:
    """`bisavô - avô - pai - nome`: a identificação inteira, numa linha só."""
    bisavo, avo, pai = hierarquia(t)
    return " - ".join([x for x in (bisavo, avo, pai, t["nome"]) if x])


def responsavel(recurso: str | None) -> str:
    return "Responsável: %s" % (recurso or "não atribuído")


def de_snapshot(tarefas: list[dict]) -> list[dict]:
    """data/tasks_<pid>.json — o cronograma atual."""
    return _com_caminho([{
        "id":      str(t.get("id")) if t.get("id") else None,
        "nome":    t.get("name") or "",
        "recurso": t.get("resources") or "",
        "nivel":   t.get("level") or 0,
        "inicio":  t.get("start"),
        "termino": t.get("end"),
        "marco":   bool(t.get("marco")),
    } for t in tarefas])


def de_historico(estado: dict) -> list[dict]:
    """Estado reconstruído pelo módulo historico."""
    import historico
    return de_snapshot(historico.como_lista(estado))


# ── Datas e números ───────────────────────────────────────────────────────────

def _dias(a: str | None, b: str | None) -> int | None:
    """Dias corridos de `a` até `b`. Positivo = `b` é mais tarde."""
    if not a or not b:
        return None
    try:
        ya, ma, da = map(int, a.split("-")); yb, mb, db = map(int, b.split("-"))
        return (date(yb, mb, db) - date(ya, ma, da)).days
    except (ValueError, AttributeError):
        return None


def dias_txt(n: int) -> str:
    """`10 dias corridos` / `1 dia corrido` — magnitude, sem sinal."""
    n = abs(int(n))
    return f"{n} dia corrido" if n == 1 else f"{n} dias corridos"


def dias_sinal(n: int) -> str:
    """`+10 dias corridos` / `-1 dia corrido` — com sinal."""
    n = int(n)
    return f"{n:+d} dia corrido" if abs(n) == 1 else f"{n:+d} dias corridos"


def br(d: str | None) -> str:
    return "—" if not d else f"{d[8:10]}/{d[5:7]}/{d[2:4]}"


# ── Pareamento ────────────────────────────────────────────────────────────────

def parear(anterior: list[dict], atual: list[dict]) -> dict:
    """Casa as tarefas das duas versões pelo id.

    O GUID da tarefa é estável entre publicações do Project Server, e os dois
    lados vêm do PWA. Tarefa sem id só aconteceria por dado corrompido: entra
    como removida ou inserida, e a seção avisa.
    """
    indice: dict[str, list[int]] = {}
    for i, t in enumerate(atual):
        if t["id"]:
            indice.setdefault(t["id"], []).append(i)

    pares, removidas, usados = [], [], set()
    for a in anterior:
        cands = [i for i in indice.get(a["id"], []) if i not in usados] if a["id"] else []
        if cands:
            usados.add(cands[0])
            pares.append((a, atual[cands[0]]))
        else:
            removidas.append(a)
    inseridas = [t for i, t in enumerate(atual) if i not in usados]
    return {"pares": pares, "removidas": removidas, "inseridas": inseridas}


# ── Análise ───────────────────────────────────────────────────────────────────

def comparar(anterior: list[dict], atual: list[dict],
             brutos_atu: list[dict] | None = None) -> dict:
    """Compara duas versões normalizadas.

    `brutos_atu` é a lista no formato do snapshot (com `preds`): sem ela não há
    rede de dependências e, portanto, não há como apontar ofensores.
    """
    p = parear(anterior, atual)

    variacoes = []
    for a, b in p["pares"]:
        if not b["folha"]:          # resumos espelham os filhos: contariam duas vezes
            continue
        dur_a = _dias(a["inicio"], a["termino"])
        dur_b = _dias(b["inicio"], b["termino"])
        variacoes.append({
            "ant": a, "atu": b, "marco": b["marco"],
            "dfim": _dias(a["termino"], b["termino"]),
            "dini": _dias(a["inicio"],  b["inicio"]),
            "ddur": (dur_b - dur_a) if (dur_a is not None and dur_b is not None) else None,
        })

    raiz_a = anterior[0] if anterior else {}
    raiz_b = atual[0] if atual else {}
    saldo  = _dias(raiz_a.get("termino"), raiz_b.get("termino"))

    # Marcos saem das listas, mas continuam nos deltas: a rede precisa deles.
    uteis   = [v for v in variacoes if not v["marco"]]
    atrasos = sorted([v for v in uteis if (v["dfim"] or 0) > 0], key=lambda v: -v["dfim"])

    causa = None
    if brutos_atu:
        import rede
        deltas = {v["atu"]["id"]: v for v in variacoes if v["atu"]["id"]}
        causa  = rede.causa_do_prazo(saldo, raiz_b.get("termino"), deltas,
                                     rede.indexar(brutos_atu),
                                     ids_folha=rede.folhas(brutos_atu))
        # A rede trabalha com os dicts brutos, que só têm o nome solto; o
        # relatório precisa da grafia hierárquica e do término anterior.
        for g in causa["cadeia"]:
            v = deltas.get(g["id"])
            if v:
                g["rotulo"]      = rotulo(v["atu"])
                g["termino_ant"] = v["ant"].get("termino")
                g["termino"]     = v["atu"].get("termino")

    return {
        "projeto": {
            "termino_ant": raiz_a.get("termino"), "termino_atu": raiz_b.get("termino"),
            "saldo":       saldo,
            "duracao_ant": _dias(raiz_a.get("inicio"), raiz_a.get("termino")),
            "duracao_atu": _dias(raiz_b.get("inicio"), raiz_b.get("termino")),
        },
        "reconciliacao": {"removidas": p["removidas"], "inseridas": p["inseridas"]},
        "atrasos": atrasos,
        "causa":   causa,
    }


# ── Seção do report semanal ───────────────────────────────────────────────────

def secao_semanal(r: dict, data_ant: str, data_atu: str) -> str:
    """Bloco pronto para entrar no report semanal, logo depois do resumo."""
    pj    = r["projeto"]
    causa = r.get("causa")
    saldo = pj["saldo"] or 0
    L: list[str] = [f"## O que mudou entre {data_ant} e {data_atu}?", ""]

    if saldo > 0:
        efeito = "gerando um atraso de %s em relação à semana anterior" % dias_txt(saldo)
    elif saldo < 0:
        efeito = "gerando um adiantamento de %s em relação à semana anterior" % dias_txt(saldo)
    else:
        efeito = "sem alteração de prazo em relação à semana anterior"
    L.append("- A Previsão de Conclusão mudou de %s para %s, %s."
             % (br(pj["termino_ant"]), br(pj["termino_atu"]), efeito))

    d_ant, d_atu = pj["duracao_ant"], pj["duracao_atu"]
    if d_ant is None or d_atu is None:
        L.append("- A Duração total do projeto não pôde ser comparada.")
    else:
        delta = d_atu - d_ant
        if delta > 0:
            efeito = "gerando um aumento de %s na duração total do projeto" % dias_txt(delta)
        elif delta < 0:
            efeito = "gerando uma redução de %s na duração total do projeto" % dias_txt(delta)
        else:
            efeito = "sem alteração na duração total do projeto"
        L.append("- A Duração total do projeto mudou de %s para %s, %s."
                 % (dias_txt(d_ant), dias_txt(d_atu), efeito))

    # ── Ofensores ────────────────────────────────────────────────────────────
    ger = (causa or {}).get("geradores") or []
    L += ["", "**Principais Ofensores (Tarefas de Caminho Crítico)**", ""]
    if ger:
        for g in ger[:TOPO_OFENSORES]:
            # O número é o AUMENTO DE DURAÇÃO, não a variação do término: parte
            # do deslocamento é herdada, e só o que a tarefa acrescentou de
            # duração é responsabilidade dela.
            L.append("- %s: Aumento de duração de %s (%s, término %s → %s)"
                     % (g.get("rotulo") or g["nome"], dias_sinal(g["ddur"]),
                        responsavel(g["recurso"]), br(g.get("termino_ant")),
                        br(g.get("termino"))))
    elif causa is None:
        L.append("- Sem a rede de dependências não é possível apontar os ofensores.")
    elif saldo:
        L.append("- Nenhuma tarefa aumentou de duração na cadeia que leva ao término: "
                 "o desvio veio de replanejamento, não de atraso de tarefa.")
    else:
        L.append("- Não existem tarefas que cumpram os critérios desta seção")

    # ── Maiores variações, fora da cadeia ────────────────────────────────────
    na_cadeia = {c["id"] for c in (causa or {}).get("cadeia") or []}
    fora = [v for v in r["atrasos"] if v["atu"]["id"] not in na_cadeia]
    L += ["", "**Maiores Variações (Tarefas com slack positivo)**", ""]
    if not fora:
        L.append("- Não existem tarefas que cumpram os critérios desta seção")
    else:
        for v in fora[:TOPO_LISTA]:
            t = v["atu"]
            L.append("- %s: Variação de %s (%s, %s → %s)"
                     % (rotulo(t), dias_sinal(v["dfim"]), responsavel(t["recurso"]),
                        br(v["ant"]["termino"]), br(t["termino"])))

    rec = r["reconciliacao"]
    if rec["removidas"] or rec["inseridas"]:
        L += ["", "> Atenção: %d tarefa(s) removida(s) e %d inserida(s) entre as duas "
              "versões não entram na comparação."
              % (len(rec["removidas"]), len(rec["inseridas"]))]
    return "\n".join(L)


# ── Construtor de alto nível ──────────────────────────────────────────────────

def secao_desde_versao(pid: str, data_ant: str, tarefas_atuais: list[dict],
                       data_atu: str) -> tuple[str, dict] | None:
    """Seção comparando a versão vigente em `data_ant` com o snapshot atual.

    Devolve (markdown, versão usada) ou None quando aquela data está fora da
    janela de versões retidas — responder com a versão mais antiga disponível
    seria apresentar um cronograma que não é o daquele dia.
    """
    import historico
    v = historico.versao_em(pid, data_ant)
    if not v:
        return None
    estado = historico.reconstruir(pid, v["versao"])
    if not estado:
        return None
    r = comparar(de_historico(estado), de_snapshot(tarefas_atuais),
                 brutos_atu=tarefas_atuais)
    return secao_semanal(r, br(v["versao"][:10]), data_atu), v
