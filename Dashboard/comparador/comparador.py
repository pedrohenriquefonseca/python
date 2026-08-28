"""
comparador.py — Compara duas versões de um cronograma e explica o que mudou.

Produz a seção "O que mudou desde X?" do report semanal, que entra logo depois
do resumo e responde:

  - o término e a duração do projeto mudaram quanto?
  - quem causou o atraso (Principais Ofensores)?

Três decisões de método valem registro:

Culpa não é o mesmo que variação. Uma tarefa pode ter o término deslocado 10
dias tendo produzido apenas 2 — os outros 8 herdou da predecessora. Ofensor é
quem AUMENTOU A DURAÇÃO dentro da cadeia que chega ao término do projeto; quem
só foi deslocado por inteiro não entra.

Duração é o campo Duração do Project, não o vão entre as duas datas. Enquanto
foi o vão, bastava a tarefa escorregar para cima de um fim de semana ou de um
feriado para ela aparecer como ofensora sem ter esticado um dia — foi assim que
o 7 de setembro e o Finados de 2026 renderam ofensores inventados no 2525 e na
2ª Entrega do Jardim Coreano. O campo diz a unidade de cada tarefa por escrito
(`18d`, `11dd`), então aqui não se adivinha nem se consulta calendário.

Quando a conta não pode ser feita — base velha demais, ou tarefa que trocou de
unidade —, a seção diz isso numa ressalva. Não há segunda conta de reserva: as
duas falhas que este comparador já produziu foram degradações silenciosas, uma
caindo no vão do calendário e outra tratando duração estourada como zero.

Marcos (duração zero) ficam fora da lista: não têm duração para esticar nem
recurso a quem atribuir. Seguem visíveis para rede.py, que precisa deles como
conduíte da propagação.

Houve também uma lista de "Maiores Variações", com as tarefas que mais variaram
FORA da cadeia — variação grande sem efeito no prazo, logo com folga. Foi
retirada: respondia a uma pergunta que o report não faz e competia por atenção
com a lista que aponta o que move a entrega.

Os dois lados são o cronograma do último report (data/report_base_<pid>.json) e
o snapshot atual do PWA (data/tasks_<pid>.json). Ambos têm GUID de tarefa, então
o pareamento é por id — estável entre publicações e imune a renomeação, o que
importa porque "Análise" e "R01" se repetem dezenas de vezes no mesmo cronograma
e vêm sendo renomeadas para "Análise 1, 2, 3...".
"""
from __future__ import annotations

from datetime import date

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


def negrito(texto: str) -> str:
    """Marca de negrito do report — a mesma convenção de Report.negrito().

    Duplicada aqui de propósito: esta seção é montada por um módulo que o
    report importa, e não o contrário. Uma função de quatro caracteres não
    justifica inverter a dependência.
    """
    return f"**{texto}**" if texto else texto


def rotulo(t: dict) -> str:
    """`bisavô - avô - pai - **nome**`: a identificação inteira, numa linha só.

    Negrito só no nome, como nas demais seções do report: o caminho situa, o
    nome é o que se procura na linha.
    """
    bisavo, avo, pai = hierarquia(t)
    return " - ".join([x for x in (bisavo, avo, pai, negrito(t["nome"])) if x])


def de_snapshot(tarefas: list[dict]) -> list[dict]:
    """data/tasks_<pid>.json — o cronograma atual."""
    return _com_caminho([{
        "id":      str(t.get("id")) if t.get("id") else None,
        "nome":    t.get("name") or "",
        "recurso": t.get("resources") or "",
        "nivel":   t.get("level") or 0,
        "inicio":  t.get("start"),
        "termino": t.get("end"),
        "duracao":   t.get("duracao"),
        "duracaoUn": t.get("duracaoUn"),
        "marco":   bool(t.get("marco")),
    } for t in tarefas])


def de_base(tarefas: list[dict]) -> list[dict]:
    """data/report_base_<pid>.json — o cronograma do último report.

    Só id, datas e duração. Sem caminho hierárquico e sem marcação de folha: os
    dois são lidos apenas do cronograma ATUAL, que é quem escreve o rótulo das
    linhas e decide o que é folha. Calculá-los aqui seria percorrer a lista
    inteira para produzir campos que ninguém consulta.

    `duracaoUn` vem None nas bases gravadas antes de a duração sair do campo
    Duração do Project — é o que faz `_variacao_duracao` declarar a duração
    indisponível nesse primeiro ciclo, em vez de comparar duas escalas.
    """
    return [{
        "id":      str(t.get("id")) if t.get("id") else None,
        "inicio":  t.get("start"),
        "termino": t.get("end"),
        "duracao":   t.get("duracao"),
        "duracaoUn": t.get("duracaoUn"),
    } for t in tarefas]


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


def _dur_projeto(inicio: str | None, termino: str | None) -> int | None:
    """Duração do projeto em dias corridos, contando o dia de início.

    O vão entre as duas datas mais um: um projeto que começa e termina no mesmo
    dia dura um dia, não zero. É a mesma conta do bloco RESUMO
    (Report._bloco_resumo) — as duas seções do report falam da mesma duração e
    precisam dar o mesmo número. Sem o +1 aqui, esta seção anunciava um total
    um dia menor que o do resumo, logo acima dela.
    """
    d = _dias(inicio, termino)
    return None if d is None else d + 1


def dias_txt(n: int, unidade: str = "corrido") -> str:
    """`10 dias corridos` / `1 dia útil` — magnitude, sem sinal.

    A unidade não é enfeite: o cronograma mistura tarefas lançadas em dias
    úteis e em dias corridos, e a linha do ofensor precisa dizer em qual delas
    o número está. As linhas do projeto ficam em dias corridos, que é o que a
    distância entre duas datas mede.
    """
    n = abs(int(n))
    if unidade == "util":
        return f"{n} dia útil" if n == 1 else f"{n} dias úteis"
    return f"{n} dia corrido" if n == 1 else f"{n} dias corridos"


def br(d: str | None) -> str:
    return "—" if not d else f"{d[8:10]}/{d[5:7]}/{d[2:4]}"


# ── Duração ───────────────────────────────────────────────────────────────────
# O Project agenda cada tarefa numa de duas unidades, e as duas convivem no
# mesmo cronograma: nos 13 projetos do PWA são 4341 folhas em dias úteis e 1453
# em dias corridos (as `Análise`). Nenhuma medida única serve para as duas.
# Contar o vão do calendário fazia de ofensor quem só escorregou para cima de um
# fim de semana ou de um feriado; contar dia útil faria o inverso com as
# `Análise`, que existem justamente para consumir dias corridos e encolheriam
# ou cresceriam conforme o feriado caísse dentro ou fora da janela.
#
# Quem responde é a unidade da PRÓPRIA tarefa, e ela vem escrita do campo
# Duração do Project: `18d` é dia útil, `11dd` é dia corrido. O pwa_client já
# entrega isso partido em `duracao` (o número, na unidade dela) e `duracaoUn`.
# Aqui não se adivinha unidade nem se consulta calendário: subtrai-se.

def _variacao_duracao(a: dict, b: dict) -> tuple[int | None, str | None, str | None]:
    """Quanto a duração da tarefa mudou, em que unidade dizer isso, e o que
    impediu a conta quando ela não pôde ser feita.

    Os dois lados já estão na unidade de leitura da tarefa, o que também é o que
    permite à lista de ofensores ordenar junto dia útil e dia corrido.

    Duas situações não têm resposta, e nenhuma delas vira outra conta:

    - `duracaoUn` ausente de um dos lados. É base gravada antes de a duração
      passar a sair do campo Duração: o número que está lá conta unidades de 8h,
      em que um dia corrido vale 3, e subtrair um do outro daria um número
      plausível e errado. Voltar ao vão do calendário também não serve — era ele
      o falso positivo que tirou a duração do calendário em primeiro lugar.

    - A tarefa trocou de espécie entre os dois reports (`18d` virou `18dd`).
      A duração mudou de verdade, mas a diferença dos números é zero. É raro e é
      dito por escrito, não escondido num número.
    """
    ua, ub = a.get("duracaoUn"), b.get("duracaoUn")
    da, db = a.get("duracao"),   b.get("duracao")
    if not ua or not ub or da is None or db is None:
        return None, None, "sem_campo"
    if ua != ub:
        return None, None, "mudou_unidade"
    return db - da, ub, None


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
    sem_duracao = {"sem_campo": 0, "mudou_unidade": 0}
    for a, b in p["pares"]:
        if not b["folha"]:          # resumos espelham os filhos: contariam duas vezes
            continue
        ddur, unidade, motivo = _variacao_duracao(a, b)
        # Marco não tem duração para esticar: entra na rede como conduíte, mas
        # não conta como duração que ficou por comparar.
        if motivo and not b["marco"]:
            sem_duracao[motivo] += 1
        variacoes.append({
            "ant": a, "atu": b, "marco": b["marco"],
            "dfim": _dias(a["termino"], b["termino"]),
            "dini": _dias(a["inicio"],  b["inicio"]),
            "ddur": ddur, "unidade": unidade,
        })

    raiz_a = anterior[0] if anterior else {}
    raiz_b = atual[0] if atual else {}
    saldo  = _dias(raiz_a.get("termino"), raiz_b.get("termino"))

    causa = None
    if brutos_atu:
        import rede
        # Marcos entram nos deltas mesmo ficando fora da lista final: a rede
        # precisa deles como conduíte da propagação.
        deltas = {v["atu"]["id"]: v for v in variacoes if v["atu"]["id"]}
        causa  = rede.causa_do_prazo(saldo, raiz_b.get("termino"), deltas,
                                     rede.indexar(brutos_atu),
                                     ids_folha=rede.folhas(brutos_atu))
        # A rede trabalha com os dicts brutos, que só têm o nome solto; o
        # relatório precisa da grafia hierárquica.
        for g in causa["cadeia"]:
            v = deltas.get(g["id"])
            if v:
                g["rotulo"] = rotulo(v["atu"])

    return {
        "projeto": {
            "termino_ant": raiz_a.get("termino"), "termino_atu": raiz_b.get("termino"),
            "saldo":       saldo,
            "duracao_ant": _dur_projeto(raiz_a.get("inicio"), raiz_a.get("termino")),
            "duracao_atu": _dur_projeto(raiz_b.get("inicio"), raiz_b.get("termino")),
        },
        "reconciliacao": {"removidas": p["removidas"], "inseridas": p["inseridas"]},
        "causa":   causa,
        # Quantas tarefas ficaram sem comparação de duração, e por quê. A lista
        # de ofensores só admite quem aumentou de duração, então essas somem
        # dela — e sumir calado é como o report passou duas semanas afirmando
        # coisas que não tinha como saber.
        "sem_duracao": sem_duracao,
        "pares_folha": len(variacoes),
    }


# ── Seção do report semanal ───────────────────────────────────────────────────

def secao_semanal(r: dict, data_ant: str) -> str:
    """Bloco pronto para entrar no report semanal, logo depois do resumo.

    `data_ant` é a data do cronograma com que se compara — o do último report.
    Ela vai no título porque o período não é fixo: se o report anterior saiu há
    dois dias, a seção cobre dois dias, e quem lê precisa saber disso sem ter de
    perguntar. Pela mesma razão nenhuma frase do corpo diz "semana": o número
    seria verdadeiro e o período, falso.
    """
    pj    = r["projeto"]
    causa = r.get("causa")
    saldo = pj["saldo"] or 0
    # Cabeçalhos no mesmo padrão das demais seções do report: emoji + caixa alta
    # + a marca de negrito. Fora dela, nenhuma sintaxe de markdown: o report é
    # lido como texto puro, e "##" apareceria cru do outro lado.
    L: list[str] = [negrito(f"🤔 O QUE MUDOU DESDE O ÚLTIMO REPORT({data_ant})")]

    # Sem movimento não se anuncia "mudou de X para X": a frase pede ao leitor
    # que compare duas datas iguais para concluir o que a linha já podia dizer.
    if saldo > 0:
        # "aumento", e não "atraso": a linha relata o deslocamento da data, e
        # quem julga se aquilo é atraso é quem lê o report com o contrato na
        # mão. O par com "redução" também deixa as duas metades simétricas.
        L.append("- A Previsão de Conclusão mudou de %s para %s, aumento de %s."
                 % (br(pj["termino_ant"]), br(pj["termino_atu"]), dias_txt(saldo)))
    elif saldo < 0:
        L.append("- A Previsão de Conclusão mudou de %s para %s, redução de %s."
                 % (br(pj["termino_ant"]), br(pj["termino_atu"]), dias_txt(saldo)))
    else:
        L.append("- A Previsão de Conclusão do projeto não sofreu alteração.")

    d_ant, d_atu = pj["duracao_ant"], pj["duracao_atu"]
    if d_ant is None or d_atu is None:
        L.append("- A Duração total do projeto não pôde ser comparada.")
    elif d_atu == d_ant:
        L.append("- A Duração total do projeto não sofreu alteração.")
    else:
        # Sem o "gerando um aumento de N dias corridos na duração total do
        # projeto": o número era a subtração dos dois que a própria linha acaba
        # de dar, e o complemento repetia o sujeito da frase. A linha da
        # Previsão de Conclusão mantém o dela porque lá o desvio é a distância
        # entre duas DATAS — ninguém conta isso de cabeça.
        L.append("- A Duração total do projeto mudou de %s para %s."
                 % (dias_txt(d_ant), dias_txt(d_atu)))

    # ── Ofensores ────────────────────────────────────────────────────────────
    # A seção só existe para explicar um desvio de prazo. Sem desvio ela vira um
    # cabeçalho vermelho seguido de "não existem tarefas" — alarme sem conteúdo.
    if saldo:
        ger = (causa or {}).get("geradores") or []
        sd = r.get("sem_duracao") or {}
        n_sem, n_troca = sd.get("sem_campo") or 0, sd.get("mudou_unidade") or 0
        L += ["", negrito("🚨PRINCIPAIS OFENSORES")]
        if ger:
            for g in ger[:TOPO_OFENSORES]:
                # O número é o AUMENTO DE DURAÇÃO, não a variação do término: parte
                # do deslocamento é herdada, e só o que a tarefa acrescentou de
                # duração é responsabilidade dela. E é a variação do campo Duração
                # do Project, na unidade em que a tarefa foi lançada — daí a linha
                # dizer "úteis" numa tarefa e "corridos" na outra.
                #
                # A linha é o nome e o número, e nada mais. Responsável e término
                # vinham entre parênteses e roubavam a leitura do que a seção tem
                # a dizer; quem precisa deles tem o cronograma e as outras seções
                # do report.
                # Sem o "+" na frente: a lista só admite quem aumentou de duração
                # (rede.causa_do_prazo filtra ddur > 0), então o sinal não
                # distingue uma linha da outra — e a palavra "Aumento" já está
                # escrita ali do lado.
                L.append("- %s: Aumento na duração de %s."
                         % (g.get("rotulo") or g["nome"],
                            dias_txt(g["ddur"], g.get("unidade") or "corrido")))
        elif causa is None:
            L.append("- Sem a rede de dependências não é possível apontar os ofensores.")
        elif n_sem or n_troca:
            # "Veio de replanejamento" é uma conclusão, e ela se apoia em ter
            # comparado a duração de todas as tarefas da cadeia. Com alguma
            # delas fora da conta, a conclusão não está disponível — o que há é
            # a ausência de ofensor entre as que deu para medir.
            L.append("- Nenhuma das tarefas comparadas aumentou de duração na cadeia que "
                     "leva ao término, mas nem todas puderam ser comparadas — veja a "
                     "ressalva abaixo.")
        else:
            L.append("- Nenhuma tarefa aumentou de duração na cadeia que leva ao término: "
                     "o desvio veio de replanejamento, não de atraso de tarefa.")

        # O que ficou fora da conta é dito, não omitido: a lista acima só enxerga
        # quem teve a duração comparada, e quem não teve sairia dela sem deixar
        # rastro. Uma linha a mais é mais barata que um ofensor que não aparece.
        if n_sem:
            L.append("- Ressalva: %d tarefa(s) ficaram fora da comparação de duração "
                     "porque o report anterior é mais antigo que o campo Duração do "
                     "Project. Some sozinho no próximo report salvo no histórico."
                     % n_sem)
        if n_troca:
            L.append("- Ressalva: %d tarefa(s) trocaram de dias úteis para dias corridos "
                     "(ou o contrário) entre os dois reports. A duração delas mudou, mas "
                     "as duas unidades não se subtraem — confira no Project."
                     % n_troca)

    return "\n".join(L)


# ── Construtor de alto nível ──────────────────────────────────────────────────

def secao_desde_base(base: dict, tarefas_atuais: list[dict]) -> str:
    """Seção comparando o cronograma do último report com o de agora.

    `base` é o que report_base.carregar() devolve.
    """
    import report_base
    r = comparar(de_base(base["tarefas"]), de_snapshot(tarefas_atuais),
                 brutos_atu=tarefas_atuais)
    return secao_semanal(r, br(report_base.data(base)[:10]))
