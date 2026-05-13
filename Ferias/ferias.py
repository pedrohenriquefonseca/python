"""
Lógica de Anotação de Férias.

Regras:
  - Cada funcionário ganha 30 dias corridos por período aquisitivo (ano trabalhado).
  - O período aquisitivo começa na data de admissão e se renova a cada 12 meses.
  - Os dias são debitados sempre do período mais antigo com saldo disponível (FIFO).
  - Dias = (fim - início).days + 1  (ambas as datas inclusivas, corridos).
"""
import json
import os
import uuid
from datetime import date, timedelta

DB_PATH: str = ''   # definido pelo app.py após importação


# ── helpers internos ─────────────────────────────────────────────────────────

def _add_years(d: date, n: int) -> date:
    """Soma n anos a uma data tratando 29/fev em anos não-bissextos."""
    try:
        return d.replace(year=d.year + n)
    except ValueError:
        return d.replace(year=d.year + n, day=28)


def _load() -> dict:
    if os.path.exists(DB_PATH):
        with open(DB_PATH, encoding='utf-8') as f:
            return json.load(f)
    return {'funcionarios': {}}


def _save(db: dict) -> None:
    with open(DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


# ── cálculo de períodos aquisitivos ──────────────────────────────────────────

def periodos_concedidos(admissao_str: str, hoje=None) -> list:
    """
    Retorna os períodos aquisitivos já concluídos até hoje.
    Um período é concluído quando o funcionário completa mais um ano na empresa.
    """
    admissao = date.fromisoformat(admissao_str)
    if hoje is None:
        hoje = date.today()

    periodos = []
    for n in range(1, 61):          # suporte a até 60 anos de empresa
        inicio       = _add_years(admissao, n - 1)
        fim          = _add_years(admissao, n) - timedelta(days=1)
        concedido_em = fim + timedelta(days=1)   # = _add_years(admissao, n)

        if concedido_em > hoje:
            break

        periodos.append({
            'ano':          n,
            'label':        f'Ano {n}  ({inicio.isoformat()} → {fim.isoformat()})',
            'inicio':       inicio.isoformat(),
            'fim':          fim.isoformat(),
            'dias_totais':  30,
        })

    return periodos


def proximo_periodo(admissao_str: str, hoje=None) -> dict:
    """Retorna dados do próximo período aquisitivo ainda não concluído."""
    admissao = date.fromisoformat(admissao_str)
    if hoje is None:
        hoje = date.today()

    n = len(periodos_concedidos(admissao_str, hoje)) + 1
    inicio       = _add_years(admissao, n - 1)
    fim          = _add_years(admissao, n) - timedelta(days=1)
    concedido_em = fim + timedelta(days=1)

    return {
        'ano':          n,
        'label':        f'Ano {n}  ({inicio.isoformat()} → {fim.isoformat()})',
        'concedido_em': concedido_em.isoformat(),
    }


# ── saldo por período ────────────────────────────────────────────────────────

def calcular_saldo(func: dict) -> list:
    """Retorna saldo de férias por período, do mais antigo ao mais novo."""
    periodos = periodos_concedidos(func['admissao'])
    usados   = {p['ano']: 0 for p in periodos}

    for ft in func.get('ferias_tiradas', []):
        for deb in ft.get('debitos', []):
            if deb['periodo_ano'] in usados:
                usados[deb['periodo_ano']] += deb['dias']

    return [
        {
            **p,
            'dias_usados':     usados[p['ano']],
            'dias_restantes':  30 - usados[p['ano']],
        }
        for p in periodos
    ]


# ── API pública ───────────────────────────────────────────────────────────────

def listar_funcionarios() -> list:
    return sorted(_load()['funcionarios'].keys())


def consultar_funcionario(nome: str) -> dict:
    db   = _load()
    func = db['funcionarios'].get(nome.strip())

    if not func:
        return {'novo': True}

    saldo   = calcular_saldo(func)
    proximo = proximo_periodo(func['admissao'])

    total_restante = sum(p['dias_restantes'] for p in saldo)

    return {
        'novo':           False,
        'admissao':       func['admissao'],
        'ferias_tiradas': func.get('ferias_tiradas', []),
        'saldo':          saldo,
        'proximo':        proximo,
        'total_restante': total_restante,
    }


def registrar_ferias(nome: str, inicio_str: str, fim_str: str,
                     admissao_str=None) -> dict:
    db   = _load()
    nome = nome.strip()

    # Cria funcionário novo se necessário
    if nome not in db['funcionarios']:
        if not admissao_str:
            return {
                'erro':     'funcionario_novo',
                'mensagem': f"Funcionário '{nome}' não encontrado. Informe a data de admissão.",
            }
        db['funcionarios'][nome] = {'admissao': admissao_str, 'ferias_tiradas': []}

    func   = db['funcionarios'][nome]
    inicio = date.fromisoformat(inicio_str)
    fim    = date.fromisoformat(fim_str)

    if fim < inicio:
        return {'erro': 'data_invalida', 'mensagem': 'A data de fim deve ser posterior à de início.'}

    dias_solicitados = (fim - inicio).days + 1   # corridos, inclusivo

    # Calcula dias disponíveis por período
    periodos = periodos_concedidos(func['admissao'])
    if not periodos:
        proximo = proximo_periodo(func['admissao'])
        return {
            'erro':     'sem_saldo',
            'mensagem': (f"Nenhum período aquisitivo concluído ainda. "
                         f"O primeiro período de 30 dias será concedido em {proximo['concedido_em']}."),
        }

    usados = {p['ano']: 0 for p in periodos}
    for ft in func.get('ferias_tiradas', []):
        for deb in ft.get('debitos', []):
            if deb['periodo_ano'] in usados:
                usados[deb['periodo_ano']] += deb['dias']

    total_disponivel = sum(30 - usados[p['ano']] for p in periodos)

    if dias_solicitados > total_disponivel:
        return {
            'erro':     'saldo_insuficiente',
            'mensagem': (f'Saldo insuficiente. '
                         f'Solicitados: {dias_solicitados} dias. '
                         f'Disponível: {total_disponivel} dias.'),
        }

    # Verifica sobreposição com férias já registradas
    for ft in func.get('ferias_tiradas', []):
        ex_ini = date.fromisoformat(ft['inicio'])
        ex_fim = date.fromisoformat(ft['fim'])
        if not (fim < ex_ini or inicio > ex_fim):
            return {
                'erro':     'sobreposicao',
                'mensagem': (f"Conflito com férias já registradas "
                             f"de {ft['inicio']} a {ft['fim']}."),
            }

    # Debita dos períodos mais antigos primeiro (FIFO)
    debitos, restante = [], dias_solicitados
    for p in sorted(periodos, key=lambda x: x['ano']):
        disp = 30 - usados[p['ano']]
        if disp <= 0:
            continue
        usar = min(disp, restante)
        debitos.append({'periodo_ano': p['ano'], 'dias': usar})
        restante -= usar
        if restante == 0:
            break

    entry = {
        'id':            uuid.uuid4().hex[:8],
        'inicio':        inicio_str,
        'fim':           fim_str,
        'dias':          dias_solicitados,
        'debitos':       debitos,
        'registrado_em': date.today().isoformat(),
    }

    func.setdefault('ferias_tiradas', []).append(entry)
    _save(db)

    return {
        'sucesso': True,
        'entry':   entry,
        'saldo':   calcular_saldo(func),
        'ferias_tiradas': func['ferias_tiradas'],
    }


def cancelar_ferias(nome: str, entry_id: str) -> dict:
    db   = _load()
    nome = nome.strip()
    func = db['funcionarios'].get(nome)

    if not func:
        return {'erro': 'Funcionário não encontrado.'}

    antes = len(func.get('ferias_tiradas', []))
    func['ferias_tiradas'] = [
        ft for ft in func.get('ferias_tiradas', [])
        if ft.get('id') != entry_id
    ]

    if len(func['ferias_tiradas']) == antes:
        return {'erro': 'Registro não encontrado.'}

    _save(db)
    return {
        'sucesso':        True,
        'saldo':          calcular_saldo(func),
        'ferias_tiradas': func['ferias_tiradas'],
    }
