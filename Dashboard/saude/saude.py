"""
saude.py — Análise de saúde estrutural dos cronogramas.

Mede o que faz (ou impede) a análise de causa do report semanal funcionar. Todo
KPI aqui nasceu de um defeito observado num cronograma real: o Pirajuçara perdeu
5 dos 6 dias de atraso porque a caminhada pela rede morreu numa tarefa-resumo.

O score é uma TAXA, não uma contagem: ofensores dividido pelo total de tarefas de
trabalho (as que não são resumo). Sem isso o Sede 2 (2.286 tarefas) seria sempre
pior que o Jardim Coreano (19), o que diria mais sobre o tamanho do projeto do
que sobre a qualidade dele.

Lê apenas os snapshots em data/tasks_<pid>.json. Não escreve nada.

Depende de `rede` (pasta comparador/): quem importar este módulo precisa ter
comparador/ no sys.path — app.py já insere as duas pastas.
"""
from __future__ import annotations

import rede

# ── Definição dos KPIs ────────────────────────────────────────────────────────
#
# limite: taxa a partir da qual o KPI zera. 0.20 = 20% das tarefas com o defeito
#         já vale nota zero.
# peso:   participação no score final (soma 100).
#
# Os pesos seguem o impacto na análise de causa: dependência em resumo trava a
# caminhada por completo, então pesa mais; tarefa fora do nível 4 é padronização,
# não quebra nada, então pesa menos.
KPIS = [
    {
        "id": "dep_resumo", "peso": 30, "limite": 0.10,
        "nome": "Dependências ligadas a resumo",
        "desc": "Tarefa cuja predecessora é um resumo, ou resumo que tem predecessora.",
        "porque": "É o que trava a busca do ofensor: o resumo não tem variação própria, "
                  "então a caminhada pela rede morre nele e o atraso fica sem dono.",
        "acao": "Criar tarefa de término de etapa (duração zero) e ligar o vínculo nela.",
    },
    {
        "id": "sem_sucessora", "peso": 20, "limite": 0.25,
        "nome": "Tarefas sem sucessora",
        "desc": "Tarefa que não empurra ninguém e não termina junto com o projeto.",
        "porque": "Ponta solta: se ela atrasar, o atraso não chega ao término do projeto "
                  "pela rede, e o cronograma não reage.",
        "acao": "Ligar à próxima tarefa da sequência ou ao término da etapa.",
    },
    {
        "id": "sem_predecessora", "peso": 15, "limite": 0.25,
        "nome": "Tarefas sem predecessora",
        "desc": "Tarefa sem nada antes dela, fora a primeira do cronograma.",
        "porque": "Sem predecessora a tarefa é uma ilha: nada explica a data dela, e ela "
                  "não pode ser apontada como origem de nada.",
        "acao": "Ligar à tarefa que a antecede de fato.",
    },
    {
        "id": "sem_recurso", "peso": 10, "limite": 0.10,
        "nome": "Tarefas nível 4 sem recurso",
        "desc": "Tarefa de nível 4, fora marcos, sem nenhum recurso atribuído.",
        "porque": "O report nomeia o responsável de cada ofensor. Sem recurso a linha sai "
                  "com \"Responsável: não atribuído\" — aponta o problema e não aponta "
                  "para quem cobrar.",
        "acao": "Atribuir o recurso responsável pela tarefa no Project.",
    },
    {
        "id": "marco_com_duracao", "peso": 10, "limite": 0.05,
        "nome": "Marcos com duração",
        "desc": "Tarefa marcada como marco no Project mas com duração maior que zero.",
        "porque": "Marco de duração zero a análise atravessa para achar a causa atrás dele. "
                  "Com duração, ele vira elo comum e pode aparecer como ofensor no lugar "
                  "da tarefa real.",
        "acao": "Zerar a duração do marco.",
    },
    {
        "id": "fora_nivel4", "peso": 15, "limite": 0.30,
        "nome": "Trabalho fora do nível 4",
        "desc": "Tarefa de trabalho em nível diferente de 4.",
        "porque": "Quebra a padronização da EAP: o trabalho deveria estar todo no mesmo "
                  "nível, e relatórios que agrupam por hierarquia ficam irregulares.",
        "acao": "Reposicionar a tarefa na estrutura ou criar os níveis que faltam.",
    },
]

NIVEL_TRABALHO = 4          # nível em que o trabalho deve estar
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

def _medir(tarefas: list[dict]) -> dict:
    """Conta as tarefas com cada defeito.

    A base do cálculo são as tarefas de trabalho — as que não têm filhas. Resumo
    não entra: ele espelha as filhas e seria contado duas vezes.
    """
    folhas = rede.folhas(tarefas)
    por_id = {str(t["id"]): t for t in tarefas if t.get("id")}
    fim_projeto = max((t.get("end") or "") for t in tarefas) if tarefas else ""

    dep_resumo = set()
    com_pred, com_suc = set(), set()

    for t in tarefas:
        tid = str(t.get("id"))
        preds = t.get("preds") or []
        if preds:
            com_pred.add(tid)
            if tid not in folhas:
                dep_resumo.add(tid)          # resumo que é sucessora
        for pr in preds:
            pid_pred = str(pr.get("id"))
            com_suc.add(pid_pred)
            if pid_pred in por_id and pid_pred not in folhas:
                dep_resumo.add(tid)          # predecessora é resumo

    # A primeira tarefa não precisa de predecessora; quem termina junto com o
    # projeto não precisa de sucessora.
    sem_pred = {x for x in folhas if x not in com_pred}
    if sem_pred:
        primeira = min(sem_pred, key=lambda x: (por_id[x].get("start") or "9999"))
        sem_pred.discard(primeira)
    sem_suc = {x for x in folhas
               if x not in com_suc and (por_id[x].get("end") or "") != fim_projeto}

    # Marco por intenção (flag do Project) que não tem duração zero. O flag só
    # existe em snapshot coletado depois de 14/08/26 — sem ele o KPI sai de fora
    # do score em vez de mentir um 100.
    tem_flag = any("isMilestone" in t for t in tarefas)
    marco_dur = {str(t["id"]) for t in tarefas
                 if t.get("isMilestone") and not t.get("marco")} if tem_flag else set()

    fora_nivel = {x for x in folhas
                  if (por_id[x].get("level") or 0) != NIVEL_TRABALHO}

    # Marco não executa trabalho, então não tem a quem atribuir: fica de fora.
    sem_recurso = {x for x in folhas
                   if (por_id[x].get("level") or 0) == NIVEL_TRABALHO
                   and not por_id[x].get("marco")
                   and not (por_id[x].get("resources") or "").strip()}

    return {
        "base": len(folhas),
        "tem_flag_marco": tem_flag,
        "contagens": {
            "dep_resumo":        len(dep_resumo),
            "sem_sucessora":     len(sem_suc),
            "sem_predecessora":  len(sem_pred),
            "sem_recurso":       len(sem_recurso),
            "marco_com_duracao": len(marco_dur),
            "fora_nivel4":       len(fora_nivel),
        },
    }


# ── API do módulo ─────────────────────────────────────────────────────────────

def analisar(tarefas: list[dict], nome: str = "", pid: str = "") -> dict:
    """Análise completa de um cronograma: KPIs, notas e score total."""
    m = _medir(tarefas)
    base = m["base"]

    kpis = []
    soma_pesos = soma_notas = 0.0
    for k in KPIS:
        indisponivel = (k["id"] == "marco_com_duracao" and not m["tem_flag_marco"])
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
            "motivo_indisponivel": ("O flag de marco do Project entrou no snapshot em "
                                    "14/08/26. Este KPI aparece após a próxima coleta.")
                                   if indisponivel else None,
        })

    score = round(soma_notas / soma_pesos, 1) if soma_pesos else 0.0
    faixa, cor = _classificar(score)
    total_defeitos = sum(m["contagens"][k["id"]] for k in KPIS
                         if not (k["id"] == "marco_com_duracao" and not m["tem_flag_marco"]))

    return {
        "id": pid, "nome": nome,
        "score": score, "faixa": faixa, "cor": cor,
        "tarefas": len(tarefas), "folhas": base,
        "total_defeitos": total_defeitos,
        "kpis": kpis,
    }


def resumo(tarefas: list[dict], nome: str = "", pid: str = "") -> dict:
    """Score e notas por indicador — para o painel com todos os projetos.

    As notas de cada KPI vêm junto porque o painel monta com elas o mapa de
    calor e o radar que compara os melhores com os piores; sem isso seria uma
    chamada por projeto só para desenhar a comparação.
    """
    a = analisar(tarefas, nome, pid)
    notas = [{"id": k["id"], "nome": k["nome"], "nota": k["nota"],
              "qtd": k["qtd"], "taxa": k["taxa"]} for k in a["kpis"]]
    avaliados = [k for k in notas if k["nota"] is not None]
    return {"id": a["id"], "nome": a["nome"], "score": a["score"],
            "faixa": a["faixa"], "cor": a["cor"], "folhas": a["folhas"],
            "total_defeitos": a["total_defeitos"],
            "notas": notas,
            "limpos": sum(1 for k in avaliados if k["qtd"] == 0),
            "piores": sorted(avaliados, key=lambda k: k["nota"])[:2],
            "melhores": sorted(avaliados, key=lambda k: -k["nota"])[:2]}
