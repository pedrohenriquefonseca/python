"""
saude.py — Análise de saúde estrutural dos cronogramas.

Mede o que faz (ou impede) a análise de causa do report semanal funcionar. Todo
KPI aqui nasceu de um defeito observado num cronograma real: o Pirajuçara perdeu
5 dos 6 dias de atraso porque a caminhada pela rede morreu numa tarefa-resumo.

O score é uma TAXA, não uma contagem: ofensores dividido pelo total de tarefas de
trabalho (as que não são resumo). Sem isso o Sede 2 (2.286 tarefas) seria sempre
pior que o Jardim Coreano (19), o que diria mais sobre o tamanho do projeto do
que sobre a qualidade dele.

Tarefa inativa do Project fica fora de tudo — da base e de todos os KPIs. Ela não
é agendada nem propaga atraso, então cobrar amarração dela é apontar defeito em
linha que o próprio Project ignora.

Lê apenas os snapshots em data/tasks_<pid>.json. Não escreve nada.

Depende de `rede` (pasta comparador/): quem importar este módulo precisa ter
comparador/ no sys.path — app.py já insere as duas pastas.
"""
from __future__ import annotations

import re

import rede

# ── Definição dos KPIs ────────────────────────────────────────────────────────
#
# limite: taxa a partir da qual o KPI zera. 0.20 = 20% das tarefas com o defeito
#         já vale nota zero.
# peso:   participação no score final (soma 100).
#
# Os pesos seguem o impacto na análise de causa: dependência em resumo trava a
# caminhada por completo, então pesa mais; tarefa fora do nível 4 é padronização,
# não quebra nada, então pesa menos. Somam 100 — os 5 pontos de duração
# fracionada saíram de `fora_nivel4`, que era o outro KPI de padronização.
#
# Os 20 pontos de `restricao` (15/09/26) saíram de todos os outros na mesma
# proporção (cada um ficou com 80% do que tinha), para a ordem entre eles não
# mudar. Com peso 10 a regra não tirava ninguém de Excelente, porque a carteira
# já estava perto de 100 no resto; com 20, nota zero nela leva a 80.
KPIS = [
    {
        "id": "dep_resumo", "peso": 24, "limite": 0.10,
        "nome": "Dependências ligadas a resumo",
        "desc": "Tarefa cuja predecessora é um resumo, ou resumo que tem predecessora.",
        "porque": "É o que trava a busca do ofensor: o resumo não tem variação própria, "
                  "então a caminhada pela rede morre nele e o atraso fica sem dono.",
        "acao": "Criar tarefa de término de etapa (duração zero) e ligar o vínculo nela.",
    },
    {
        "id": "sem_sucessora", "peso": 16, "limite": 0.25,
        "nome": "Tarefas sem sucessora",
        "desc": "Tarefa que não empurra ninguém e não termina junto com o projeto, fora uma tolerada por cronograma.",
        "porque": "Ponta solta: se ela atrasar, o atraso não chega ao término do projeto "
                  "pela rede, e o cronograma não reage.",
        "acao": "Ligar à próxima tarefa da sequência ou ao término da etapa.",
    },
    {
        "id": "sem_predecessora", "peso": 12, "limite": 0.25,
        "nome": "Tarefas sem predecessora",
        "desc": "Tarefa sem nada antes dela, fora a primeira do cronograma e uma tolerada por cronograma.",
        "porque": "Sem predecessora a tarefa é uma ilha: nada explica a data dela, e ela "
                  "não pode ser apontada como origem de nada.",
        "acao": "Ligar à tarefa que a antecede de fato.",
    },
    {
        "id": "restricao", "peso": 20, "limite": 0.05,
        "nome": "Tarefas com restrição de data",
        "desc": "Tarefa com restrição diferente de O Mais Breve Possível. Só marco com "
                "Não Iniciar Antes De é aceito.",
        "porque": "Tarefa presa a uma data não anda pela predecessora: quem a move é o "
                  "calendário. A busca do ofensor chega nela e não acha causa na rede, "
                  "e o atraso fica sem dono.",
        "acao": "Voltar a tarefa para O Mais Breve Possível e amarrar a data num marco "
                "com Não Iniciar Antes De.",
    },
    {
        "id": "sem_recurso", "peso": 8, "limite": 0.10,
        "nome": "Tarefas nível 4 sem recurso",
        "desc": "Tarefa de nível 4, fora marcos, sem nenhum recurso atribuído.",
        "porque": "A triagem do report é pelo recurso: sem ele a tarefa não é emissão "
                  "nossa nem está a cargo do cliente, fica fora das duas seções e só "
                  "aparece na nota de pendências do cronograma.",
        "acao": "Atribuir o recurso responsável pela tarefa no Project.",
    },
    {
        "id": "marco_com_duracao", "peso": 8, "limite": 0.05,
        "nome": "Marcos com duração",
        "desc": "Tarefa marcada como marco no Project mas com duração maior que zero.",
        "porque": "Marco de duração zero a análise atravessa para achar a causa atrás dele. "
                  "Com duração, ele vira elo comum e pode aparecer como ofensor no lugar "
                  "da tarefa real.",
        "acao": "Zerar a duração do marco.",
    },
    {
        "id": "duracao_fracionada", "peso": 4, "limite": 0.05,
        "nome": "Durações fracionadas",
        "desc": "Tarefa cuja duração não é um número inteiro de dias "
                "(ex.: 33,38 dias corridos).",
        "porque": "O report fala em dias inteiros, então a duração fracionada é "
                  "arredondada para caber na frase. Duas tarefas de 5,4 dias somam 11 no "
                  "Project e 10 no report, e uma edição pequena pode virar um dia inteiro "
                  "de variação que ninguém encomendou.",
        "acao": "Lançar a duração em dias inteiros no Project.",
    },
    {
        "id": "fora_nivel4", "peso": 8, "limite": 0.30,
        "nome": "Trabalho fora do nível 4",
        "desc": "Tarefa de trabalho em nível diferente de 4, fora marcos.",
        "porque": "Quebra a padronização da EAP: o trabalho deveria estar todo no mesmo "
                  "nível, e relatórios que agrupam por hierarquia ficam irregulares.",
        "acao": "Reposicionar a tarefa na estrutura ou criar os níveis que faltam.",
    },
]

# Tipo de restrição como o REST do PWA devolve em `restricao`: o enum do CSOM
# somado de 1 (ver PROJETO.txt, seção 9).
RESTRICOES = {
    1: "O Mais Breve Possível",
    2: "O Mais Tarde Possível",
    3: "Deve Iniciar Em",
    4: "Deve Terminar Em",
    5: "Não Iniciar Antes De",
    6: "Não Iniciar Depois De",
    7: "Não Terminar Antes De",
    8: "Não Terminar Depois De",
}
SEM_RESTRICAO = 1           # O Mais Breve Possível
RESTRICAO_DE_MARCO = 5      # Não Iniciar Antes De — a única aceita, e só em marco

NIVEL_TRABALHO = 4          # nível em que o trabalho deve estar
TOLERANCIA_PONTA = 1        # pontas soltas perdoadas por projeto, em cada lado
FAIXAS = [                  # (nota mínima, rótulo, cor)
    (90, "Excelente", "verde"),
    (75, "Bom",       "verde"),
    (60, "Regular",   "amarelo"),
    (40, "Ruim",      "laranja"),
    (0,  "Crítico",   "vermelho"),
]


def _classificar(nota: float) -> tuple[str, str]:
    for minimo, rotulo, cor in FAIXAS:
        if nota >= minimo:
            return rotulo, cor
    return FAIXAS[-1][1], FAIXAS[-1][2]


def _nota(qtd: int, base: int, limite: float) -> float:
    """Nota 0–100 a partir da taxa de defeito. 100 sem defeito; 0 no limite."""
    if base <= 0:
        return 100.0
    taxa = qtd / base
    return round(max(0.0, min(100.0, 100.0 * (1.0 - taxa / limite))), 1)


# ── Coleta dos defeitos ───────────────────────────────────────────────────────

def _fracionada(dur_txt: str | None) -> bool:
    """`33,38dd` sim; `18d` não.

    O campo Duração do Project é número seguido de sufixo só com letras (`d` ou
    `dd` neste PWA), então qualquer separador decimal no meio da string denuncia
    a fração — sem precisar reparsear o número.
    """
    return bool(dur_txt) and ("," in dur_txt or "." in dur_txt)


def _dias_txt(n: int | None, unidade: str | None) -> str:
    """`10 dias úteis` / `1 dia corrido` — para as mensagens desta tela."""
    if n is None:
        return "—"
    singular, plural = (("útil", "úteis") if unidade == "util"
                        else ("corrido", "corridos"))
    return ("1 dia %s" % singular) if abs(n) == 1 else ("%d dias %s" % (n, plural))


def _por_extenso(dur_txt: str | None) -> str:
    """`33,38dd` → `33,38 dias corridos`.

    O `d`/`dd` é a abreviação do Project; nas telas e no report a unidade vai
    escrita. O número fica como o Project o grafou, com a vírgula e todas as
    casas: é ele que se procura na coluna Duração para corrigir a tarefa.
    """
    if not dur_txt:
        return "—"
    m = re.match(r"^\s*(-?[\d.,]+)\s*(dd?)\s*\??\s*$", dur_txt)
    if not m:
        return dur_txt          # formato inesperado: mostra como veio do servidor
    num, sufixo = m.group(1), m.group(2)
    singular, plural = (("corrido", "corridos") if sufixo == "dd"
                        else ("útil", "úteis"))
    um = num.replace(".", "").replace(",", ".") in ("1", "1.0")
    return "%s dia %s" % (num, singular) if um else "%s dias %s" % (num, plural)


def _motivo_restricao(t: dict) -> str:
    """`restrição "Não Terminar Antes De" em 21/08/2026 numa tarefa com duração`.

    O motivo diz o que está fora da regra — o tipo, ou o tipo certo na tarefa
    errada —, porque a correção é diferente: marco só troca o tipo; tarefa com
    duração perde a restrição e a data vai para um marco antes dela.
    """
    codigo = t.get("restricao")
    nome = RESTRICOES.get(codigo, "código %s" % codigo)
    data = t.get("restricaoData")
    txt = 'restrição "%s"%s' % (nome, " em %s" % _data_br(data) if data else "")
    if t.get("marco"):
        return txt + ' num marco: marco só aceita "%s"' % RESTRICOES[RESTRICAO_DE_MARCO]
    return txt + " numa tarefa com duração: a data dela vem do calendário, não da predecessora"


def _tolerar(ids: set[str], por_id: dict, campo: str, isentas: int = 0) -> set[str]:
    """Tira da conta as pontas soltas perdoadas do projeto.

    Perdoa as mais defensáveis: sem predecessora, as que começam antes de todas
    (começo de uma frente); sem sucessora, as que terminam depois de todas (fim
    de uma frente). `isentas` são as isenções estruturais, somadas à tolerância.
    """
    ordem = sorted(ids, key=lambda x: (por_id[x].get(campo) or ""),
                   reverse=(campo == "end"))
    return set(ordem[TOLERANCIA_PONTA + isentas:])


def _medir(tarefas: list[dict]) -> dict:
    """Conta as tarefas com cada defeito e guarda quais são.

    A base do cálculo são as tarefas de trabalho — as que não têm filhas. Resumo
    não entra: ele espelha as filhas e seria contado duas vezes.

    Junto da contagem sai o motivo de cada tarefa apontada. É o que a tela usa
    para dizer onde está o defeito: contar 49 dependências em resumo não ajuda
    ninguém a achar as 49 no meio de 221 linhas do Project.
    """
    # Tarefa inativa do Project não é agendada, não empurra ninguém e não
    # aparece no cronograma que se executa: cobrar amarração, recurso ou nível
    # dela é apontar defeito em linha que o Project já ignora. Sai da base e de
    # todos os KPIs — inclusive como PONTA de vínculo: um link para uma inativa
    # não propaga atraso, então quem só liga nela continua sendo ponta solta.
    #
    # `ativa` entrou no snapshot depois dos demais campos. Onde ele não existe,
    # ninguém é inativa e a medição sai como sempre saiu.
    inativas = {str(t["id"]) for t in tarefas
                if t.get("id") and t.get("ativa") is False}
    ativas = [t for t in tarefas if str(t.get("id")) not in inativas]

    # `folhas` é posicional: quem decide se uma linha é resumo é o nível da
    # linha SEGUINTE. Por isso a varredura vê a lista inteira e as inativas são
    # descontadas depois — tirá-las antes faria um resumo cujas filhas são todas
    # inativas virar tarefa de trabalho.
    folhas = rede.folhas(tarefas) - inativas
    por_id = {str(t["id"]): t for t in tarefas if t.get("id")}
    # A tarefa-resumo do projeto ocupa a linha 0 do Project, não a 1. Quando ela
    # abre a lista (é o normal: o coletor a injeta como primeira), a posição no
    # cronograma é o próprio índice; sem ela a numeração começa em 1.
    base = 0 if tarefas and tarefas[0].get("level") == 0 else 1
    linha = {str(t["id"]): i + base for i, t in enumerate(tarefas) if t.get("id")}
    fim_projeto = max((t.get("end") or "") for t in ativas) if ativas else ""

    dep_resumo = set()
    motivos_resumo: dict[str, list[str]] = {}
    com_pred, com_suc = set(), set()

    for t in ativas:
        tid = str(t.get("id"))
        # Vínculo com uma inativa é vínculo que o Project não honra: não conta
        # como predecessora existente nem como sucessora de ninguém.
        preds = [pr for pr in (t.get("preds") or [])
                 if str(pr.get("id")) not in inativas]
        if preds:
            com_pred.add(tid)
            if tid not in folhas:
                dep_resumo.add(tid)          # resumo que é sucessora
                motivos_resumo.setdefault(tid, []).append(
                    "é um resumo e mesmo assim tem predecessora")
        for pr in preds:
            pid_pred = str(pr.get("id"))
            com_suc.add(pid_pred)
            if pid_pred in por_id and pid_pred not in folhas:
                dep_resumo.add(tid)          # predecessora é resumo
                motivos_resumo.setdefault(tid, []).append(
                    'predecessora é o resumo "%s" (linha %d)'
                    % (por_id[pid_pred].get("name") or "", linha[pid_pred]))

    # A primeira tarefa não precisa de predecessora; quem termina junto com o
    # projeto não precisa de sucessora. Além dessas isenções estruturais, cada
    # cronograma tem direito a TOLERANCIA_PONTA ponta solta de cada lado sem
    # perder nota: na prática todo projeto real abre uma frente a mais ("Início
    # do Contrato" de um segundo lote) e fecha uma etapa antes do fim ("Término
    # do Projeto" de uma fase). Uma dessas não é erro de amarração; da segunda
    # em diante é, e aí conta.
    sem_pred = _tolerar({x for x in folhas if x not in com_pred},
                        por_id, "start", isentas=1)   # a primeira do cronograma
    sem_suc = _tolerar({x for x in folhas if x not in com_suc
                        and (por_id[x].get("end") or "") != fim_projeto},
                       por_id, "end")

    # Marco por intenção (flag do Project) que não tem duração zero. O flag só
    # existe em snapshot coletado depois de 14/08/26 — sem ele o KPI sai de fora
    # do score em vez de mentir um 100.
    tem_flag = any("isMilestone" in t for t in tarefas)
    marco_dur = {str(t["id"]) for t in ativas
                 if t.get("isMilestone") and not t.get("marco")} if tem_flag else set()

    # Duração que não é número inteiro de dias. Depende de `duracaoTxt`, a
    # grafia do Project, que só existe em snapshot coletado depois de a duração
    # passar a sair do campo Duração: antes o número vinha dos milissegundos já
    # arredondado, e a casa decimal se perdia na própria coleta. Sem o campo o
    # KPI fica indisponível pelo mesmo motivo que o dos marcos.
    tem_dur_txt = any("duracaoTxt" in t for t in tarefas)
    dur_frac = {x for x in folhas
                if _fracionada(por_id[x].get("duracaoTxt"))} if tem_dur_txt else set()

    # Marco (duração zero) não é trabalho: marca o começo ou o fim de uma etapa,
    # e o lugar dele na EAP é o nível da etapa que ele delimita, não o nível 4.
    # Cobrar nível dele apontaria como defeito o cronograma bem montado.
    fora_nivel = {x for x in folhas
                  if (por_id[x].get("level") or 0) != NIVEL_TRABALHO
                  and not por_id[x].get("marco")}

    # Pelo mesmo motivo o marco não tem a quem atribuir: fica de fora.
    sem_recurso = {x for x in folhas
                   if (por_id[x].get("level") or 0) == NIVEL_TRABALHO
                   and not por_id[x].get("marco")
                   and not (por_id[x].get("resources") or "").strip()}

    # Restrição de data. O cronograma bem montado deixa tudo em O Mais Breve
    # Possível e prende as datas externas (contrato, OS, entrega do cliente) em
    # marcos com Não Iniciar Antes De: a data entra na rede por um ponto só, e
    # quem depende dela anda pelos vínculos. Qualquer outra combinação é tarefa
    # que o calendário move, e aí a busca do ofensor não acha causa na rede.
    #
    # Conta resumo também (a restrição nele prende as filhas do mesmo jeito);
    # a linha 0, a do projeto, não tem o campo. `restricao` só existe em
    # snapshot coletado depois de 15/09/26 — sem ele o KPI fica indisponível.
    tem_restricao = any("restricao" in t for t in tarefas)
    restricao = {
        str(t["id"]) for t in ativas
        if t.get("level") and t.get("restricao") not in (None, SEM_RESTRICAO)
        and not (t.get("restricao") == RESTRICAO_DE_MARCO and t.get("marco"))
    } if tem_restricao else set()

    caminhos = _caminhos(tarefas)
    ofensores = {
        "dep_resumo": {x: "; ".join(dict.fromkeys(motivos_resumo.get(x, [])))
                       for x in dep_resumo},
        "sem_sucessora": {
            x: "ninguém depende dela: termina em %s e o atraso morre aí"
               % _data_br(por_id[x].get("end")) for x in sem_suc},
        "sem_predecessora": {
            x: "nada antes dela na rede: começa em %s sem que ninguém a libere"
               % _data_br(por_id[x].get("start")) for x in sem_pred},
        "restricao": {x: _motivo_restricao(por_id[x]) for x in restricao},
        "sem_recurso": {
            x: 'campo Recursos vazio: fica fora das duas seções do report e cai na '
               'nota de pendências'
            for x in sem_recurso},
        "marco_com_duracao": {
            x: "marcado como marco no Project, mas com duração de %s"
               % _por_extenso(por_id[x].get("duracaoTxt")) for x in marco_dur},
        "duracao_fracionada": {
            x: "duração lançada como %s: não é um número inteiro de dias, e o "
               "report arredonda para %s"
               % (_por_extenso(por_id[x].get("duracaoTxt")),
                  _dias_txt(por_id[x].get("duracao"), por_id[x].get("duracaoUn")))
            for x in dur_frac},
        "fora_nivel4": {
            x: "é trabalho e está no nível %s, direto dentro de \"%s\""
               % (por_id[x].get("level"), caminhos[x][-1])
               if caminhos[x] else
               "é trabalho e está no nível %s, solta na raiz do cronograma"
               % por_id[x].get("level")
            for x in fora_nivel},
    }

    return {
        "base": len(folhas),
        "inativas": len(inativas),
        "tem_flag_marco": tem_flag,
        # KPI que depende de campo que o snapshot ainda não tem sai de fora do
        # score, com o motivo escrito. Ficar dentro seria anunciar um 100 que
        # não foi medido — o oposto do que esta tela existe para fazer.
        "indisponiveis": {
            k: v for k, v in {
                "marco_com_duracao":
                    None if tem_flag else
                    "O flag de marco do Project entrou no snapshot em 14/08/26. "
                    "Este KPI aparece após a próxima coleta.",
                "duracao_fracionada":
                    None if tem_dur_txt else
                    "A duração passou a vir do campo Duração do Project. Este KPI "
                    "aparece após a próxima coleta deste cronograma.",
                "restricao":
                    None if tem_restricao else
                    "O tipo de restrição entrou no snapshot em 15/09/26. Este KPI "
                    "aparece após a próxima coleta deste cronograma.",
            }.items() if v},
        "contagens": {k: len(v) for k, v in ofensores.items()},
        "ofensores": ofensores,
        "por_id": por_id,
        "linha": linha,
        "caminhos": caminhos,
    }


# ── Localização de cada tarefa apontada ───────────────────────────────────────

def _data_br(iso: str | None) -> str:
    return "/".join(reversed(iso.split("-"))) if iso else ""


def _caminhos(tarefas: list[dict]) -> dict[str, list[str]]:
    """Caminho na EAP de cada tarefa, sem o nome do projeto.

    A hierarquia do MSP é posicional — as filhas vêm logo depois da mãe, com
    nível maior —, então uma pilha indexada pelo nível reconstrói o caminho.
    Sem ele a lista não identifica nada: um cronograma tem dezenas de tarefas
    chamadas "Análise" e "R00", e o nome sozinho não diz qual é qual.
    """
    caminhos: dict[str, list[str]] = {}
    pilha: list[str] = []
    for t in tarefas:
        nivel = t.get("level") or 0
        pilha = pilha[:nivel]
        pilha.append(t.get("name") or "")
        caminhos[str(t.get("id"))] = list(pilha[1:-1])   # [0] é o projeto
    return caminhos


def _itens(m: dict, kpi_id: str) -> list[dict]:
    """As tarefas apontadas por um KPI, na ordem em que estão no cronograma."""
    por_id, linha, caminhos = m["por_id"], m["linha"], m["caminhos"]
    itens = []
    for tid, motivo in m["ofensores"][kpi_id].items():
        t = por_id[tid]
        itens.append({
            "linha": linha[tid],
            "nome": t.get("name") or "",
            "eap": " › ".join(caminhos.get(tid) or []) or "—",
            "nivel": t.get("level"),
            "inicio": t.get("start"),
            "fim": t.get("end"),
            "recurso": (t.get("resources") or "").strip(),
            "motivo": motivo,
        })
    return sorted(itens, key=lambda i: i["linha"])


# ── API do módulo ─────────────────────────────────────────────────────────────

def analisar(tarefas: list[dict], nome: str = "", pid: str = "",
             detalhar: bool = True) -> dict:
    """Análise completa de um cronograma: KPIs, notas e score total.

    `detalhar` traz junto a lista das tarefas apontadas por cada KPI. O painel
    geral analisa a carteira inteira só para desenhar o mapa de calor e não usa
    essas listas — nele sai `False` para não montar milhares de linhas à toa.
    """
    m = _medir(tarefas)
    base = m["base"]

    kpis = []
    soma_pesos = soma_notas = 0.0
    for k in KPIS:
        indisponivel = k["id"] in m["indisponiveis"]
        qtd = m["contagens"][k["id"]]
        nota = None if indisponivel else _nota(qtd, base, k["limite"])
        if not indisponivel:
            soma_pesos += k["peso"]
            soma_notas += nota * k["peso"]
        rotulo, cor = _classificar(nota if nota is not None else 0)
        kpis.append({
            "id": k["id"], "nome": k["nome"], "desc": k["desc"],
            "porque": k["porque"], "acao": k["acao"], "peso": k["peso"],
            "qtd": qtd, "base": base,
            "taxa": round(100.0 * qtd / base, 1) if base else 0.0,
            "nota": nota,
            "faixa": None if indisponivel else rotulo,
            "cor": None if indisponivel else cor,
            "indisponivel": indisponivel,
            "motivo_indisponivel": m["indisponiveis"].get(k["id"]),
            "itens": _itens(m, k["id"]) if detalhar and not indisponivel else [],
        })

    score = round(soma_notas / soma_pesos, 1) if soma_pesos else 0.0
    faixa, cor = _classificar(score)
    total_defeitos = sum(m["contagens"][k["id"]] for k in KPIS
                         if k["id"] not in m["indisponiveis"])

    return {
        "id": pid, "nome": nome,
        "score": score, "faixa": faixa, "cor": cor,
        "tarefas": len(tarefas), "folhas": base,
        # Quantas linhas ficaram fora por estarem inativas no Project. A tela
        # diz o número: score que ignora parte do cronograma calado é score que
        # o leitor não tem como conferir contra o que vê no Project.
        "inativas": m["inativas"],
        "total_defeitos": total_defeitos,
        "kpis": kpis,
    }


def resumo(tarefas: list[dict], nome: str = "", pid: str = "") -> dict:
    """Score e notas por indicador — para o painel com todos os projetos.

    As notas de cada KPI vêm junto porque o painel monta com elas o mapa de
    calor e o radar que compara os melhores com os piores; sem isso seria uma
    chamada por projeto só para desenhar a comparação.
    """
    a = analisar(tarefas, nome, pid, detalhar=False)
    notas = [{"id": k["id"], "nome": k["nome"], "nota": k["nota"],
              "qtd": k["qtd"], "taxa": k["taxa"]} for k in a["kpis"]]
    avaliados = [k for k in notas if k["nota"] is not None]
    return {"id": a["id"], "nome": a["nome"], "score": a["score"],
            "faixa": a["faixa"], "cor": a["cor"], "folhas": a["folhas"],
            "inativas": a["inativas"],
            "total_defeitos": a["total_defeitos"],
            "notas": notas,
            "limpos": sum(1 for k in avaliados if k["qtd"] == 0),
            "piores": sorted(avaliados, key=lambda k: k["nota"])[:2],
            "melhores": sorted(avaliados, key=lambda k: -k["nota"])[:2]}
