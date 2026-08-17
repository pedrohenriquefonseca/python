import pandas as pd
from datetime import datetime

#Calcula diferença em dias entre duas datas.
def calcular_dias_diferenca(data1, data2):
    if pd.isna(data1) or pd.isna(data2):
        return 0
    try:
        return (data1 - data2).days
    except:
        return 0

#Busca a hierarquia (bisavô, avô, pai) de uma linha específica.
def buscar_hierarquia(df, linha_index):
    pai = avo = bisavo = ''
    
    for i in range(linha_index - 1, -1, -1):
        if i < 0 or i >= len(df):
            continue
            
        try:
            nivel = df.at[i, 'Nível_da_estrutura_de_tópicos']
            nome = str(df.at[i, 'Nome'])
            
            if nivel == 3 and not pai:
                pai = nome
            elif nivel == 2 and not avo:
                avo = nome
            elif nivel == 1 and not bisavo:
                bisavo = nome
            
            if pai and avo and bisavo:
                break
        except (KeyError, IndexError):
            continue
    
    return bisavo, avo, pai

# O único recurso nomeado da triagem. Todo o resto é entrega nossa.
RECURSO_CLIENTE = 'Cliente'


def _selecionar_tarefas(df, do_cliente):
    """Tarefas em andamento de um dos dois lados da triagem.

    A triagem tem um critério só: o recurso Cliente. O que estiver atribuído a
    qualquer outro recurso é entrega da equipe e cai nas emissões — por
    exclusão, e não por lista. Recurso novo no cronograma entra no relatório
    sozinho, sem passar por aqui.

    Tarefa sem recurso nenhum fica fora dos dois lados: não há a quem atribuir.
    """
    try:
        recursos = df['Nomes_dos_Recursos'].fillna('').astype(str).str.strip()
        eh_cliente = recursos.str.contains(RECURSO_CLIENTE, case=False, na=False)
        lado = eh_cliente if do_cliente else (~eh_cliente & (recursos != ''))
        em_andamento = (df['Porcentagem_Concluída'] > 0) & (df['Porcentagem_Concluída'] < 1)
        return df[lado & em_andamento]
    except KeyError:
        print('Aviso: Coluna necessária não encontrada para filtrar as tarefas')
        return pd.DataFrame()


#Tarefas a cargo do cliente.
def filtrar_tarefas_cliente(df):
    return _selecionar_tarefas(df, do_cliente=True)


#Tarefas de qualquer recurso que não seja o cliente — as próximas emissões.
def filtrar_tarefas_emissoes(df):
    return _selecionar_tarefas(df, do_cliente=False)


def _serie_marco(df):
    """Quais linhas são marco, em Série booleana alinhada ao df.

    Marco não tem recurso porque não tem trabalho — é data, não entrega. Cobrar
    responsável por ele seria cobrar o cronograma por estar certo.

    O campo vem pronto do JSON do PWA (`marco`, duração zero — pwa_client.py).
    Cronograma sem a coluna não tem marco algum e a nota sai inteira.
    """
    if 'Marco' not in df.columns:
        return pd.Series(False, index=df.index)
    return df['Marco'].fillna(False).astype(bool)


def filtrar_tarefas_sem_recurso(df):
    """Tarefas de trabalho com o campo de recurso vazio — ninguém responde por
    elas, e por isso não aparecem em nenhuma das duas seções do relatório.

    Ficam de fora as duas famílias que não têm recurso por natureza, e não por
    esquecimento: tarefa-resumo (quem recebe recurso são as filhas) e marco.

    Resumo aqui é topologia, não campo do cronograma — é resumo quem tem alguém
    logo abaixo na estrutura de tópicos, o mesmo raciocínio que
    `buscar_hierarquia` usa para remontar a parentela. O campo `type` do PWA não
    serve: num cronograma real, 35 dos 40 resumos vinham marcados como 'task'.
    """
    try:
        recursos = df['Nomes_dos_Recursos'].fillna('').astype(str).str.strip()
        niveis = pd.to_numeric(df['Nível_da_estrutura_de_tópicos'], errors='coerce')
        # A última linha compara com NaN e dá False — folha, como tem de ser.
        eh_resumo = niveis.shift(-1) > niveis
        return df[(recursos == '') & ~eh_resumo & ~_serie_marco(df)]
    except KeyError:
        print('Aviso: Coluna necessária não encontrada para listar tarefas sem recurso')
        return pd.DataFrame()


# Teto de linhas da nota. Existe cronograma nosso com 196 tarefas sem recurso —
# listadas uma a uma, a nota fica maior que o relatório inteiro. O total não se
# perde: vai na linha de excedente.
LIMITE_SEM_RECURSO = 15


def montar_nota_sem_recurso(tarefas_df, df_principal, hoje):
    """Nota de rodapé com as tarefas órfãs de recurso.

    Some do relatório quando não há nenhuma: nota de pendência sem pendência é
    ruído semanal. As demais seções sempre aparecem porque descrevem o projeto;
    esta só existe quando há algo a corrigir no cronograma.
    """
    if tarefas_df.empty:
        return ''

    nota = montar_secao_markdown(
        '📝 TAREFAS SEM RECURSO ATRIBUÍDO:',
        tarefas_df.head(LIMITE_SEM_RECURSO), df_principal, hoje, 'sem_recurso'
    )
    excedente = len(tarefas_df) - LIMITE_SEM_RECURSO
    if excedente == 1:
        nota += '- ... e outra tarefa sem recurso atribuído\n'
    elif excedente > 1:
        nota += f'- ... e outras {excedente} tarefas sem recurso atribuído\n'
    return nota


def _caminho_tarefa(avo, pai, nome):
    """'avô - pai - Nome', pulando os níveis que não existem.

    Tarefa pendurada direto no projeto não tem avô nem pai, e o caminho fixo em
    três partes saía como '-  -  - Nome'. Isso só aparece agora porque a nota de
    tarefas sem recurso alcança níveis rasos, que as outras seções não pegavam.
    """
    return ' - '.join(parte for parte in (avo, pai, nome) if parte)


def montar_secao_markdown(titulo, tarefas_df, df_principal, hoje, tipo_secao):
    #Monta uma seção em Markdown com as tarefas especificadas.
    secao_md = f'\n{titulo}'
    if tarefas_df.empty:
        # O \n é daqui, não do título: no caminho com tarefas quem quebra a linha
        # é o cabeçalho do grupo, que também separa um grupo do outro.
        secao_md += '\n- Não existem tarefas que cumpram os critérios desta seção\n'
        return secao_md

    grupos = {}
    for idx, row in tarefas_df.iterrows():
        bisavo, avo, pai = buscar_hierarquia(df_principal, idx)
        chave = bisavo if bisavo else 'Sem categoria'
        caminho = _caminho_tarefa(avo, pai, row['Nome'])

        # A nota de tarefas sem recurso usa a mesma linha das emissões: o
        # caminho da tarefa e a data em que ela está programada.
        if tipo_secao in ('emissoes', 'sem_recurso'):
            linha = f'{caminho}: Programado para {row.get("Término", "N/A")}'
        else:
            dias_analise = '?'
            if pd.notna(row.get('Início_DT')):
                try:
                    dias_analise = (hoje - row['Início_DT']).days
                except:
                    dias_analise = '?'
            linha = f'{caminho}: A cargo do cliente desde {row.get("Início", "N/A")} ({dias_analise} dias)'

        grupos.setdefault(chave, []).append(linha)

    for bisavo, tarefas in grupos.items():
        if bisavo:
            secao_md += f'\n{bisavo}:\n'
        for tarefa in tarefas:
            secao_md += f'- {tarefa}\n'

    return secao_md

#Valida se as colunas necessárias existem no DataFrame.
def validar_colunas_necessarias(df):
    colunas_obrigatorias = [
        'Nível_da_estrutura_de_tópicos', 'Nome', 'Nomes_dos_Recursos',
        'Porcentagem_Concluída'
    ]
    
    colunas_faltantes = []
    for coluna in colunas_obrigatorias:
        if coluna not in df.columns:
            colunas_faltantes.append(coluna)
    
    if colunas_faltantes:
        raise ValueError(f"Snapshot do PWA incompatível. Campos ausentes: {', '.join(colunas_faltantes)}")
    
    return df

def _bloco_resumo(AA, CC, DD, EE):
    """Linhas do bloco 📌 RESUMO, sem o cabeçalho.

    Quatro linhas pareadas: linha de base e tendência, primeiro para a conclusão
    e depois para a duração. Quem lê compara os dois números lado a lado — o
    desvio e o percentual não vêm escritos.

      AA término atual              CC término da linha de base
      DD duração da linha de base   EE duração atual
    """
    dur_atual = EE + 1          # +1 como sempre foi: o dia de início conta
    return [
        f'- Conclusão do Projeto - Linha de Base: {CC}.',
        f'- Conclusão do Projeto - Tendência: {AA}.',
        f'- Duração do Projeto - Linha de Base: {DD} dias corridos.',
        f'- Duração do Projeto - Tendência: {dur_atual} dias corridos.',
    ]


def _montar_relatorio_md(df, nome_projeto, secao_comparativo=None):
    """Montagem do relatório: recebe um DataFrame já com as colunas canônicas e
    as colunas de data no formato de exibição '%d/%m/%y', e devolve
    (conteudo_md, nome_arquivo)."""
    df = validar_colunas_necessarias(df)
    col_datas = ['Início', 'Término', 'Início_da_Linha_de_Base', 'Término_da_linha_de_base']
    for col in col_datas:
        if col in df.columns:
            df[col + '_DT'] = pd.to_datetime(df[col], format='%d/%m/%y', errors='coerce')
    hoje = datetime.now()
    nivel0_linhas = df[df['Nível_da_estrutura_de_tópicos'] == 0]
    nivel0 = nivel0_linhas.iloc[0] if not nivel0_linhas.empty else df.iloc[0]
    AA = nivel0.get('Término', 'N/A')
    CC = nivel0.get('Término_da_linha_de_base', 'N/A')
    DD = calcular_dias_diferenca(nivel0.get('Término_da_linha_de_base_DT'), nivel0.get('Início_da_Linha_de_Base_DT'))
    EE = calcular_dias_diferenca(nivel0.get('Término_DT'), nivel0.get('Início_DT'))
    filtro_emissoes = filtrar_tarefas_emissoes(df)
    filtro_cliente = filtrar_tarefas_cliente(df)
    partes = [
        f'REPORT SEMANAL {nome_projeto.upper()} - {hoje.strftime("%d/%m/%y")}\n',
        '📌 RESUMO:\n',
        *[f'{linha}\n' for linha in _bloco_resumo(AA, CC, DD, EE)],
        # Bloco "O que mudou entre X e Y?", logo depois do resumo. Sem ele o
        # relatório sai exatamente como antes.
        (f'\n{secao_comparativo}\n' if secao_comparativo else ''),
        montar_secao_markdown('📅 PRÓXIMAS EMISSÕES DE PROJETO:', filtro_emissoes, df, hoje, 'emissoes'),
        montar_secao_markdown('🔎 TAREFAS A CARGO DO CLIENTE:', filtro_cliente, df, hoje, 'analise'),
        montar_nota_sem_recurso(filtrar_tarefas_sem_recurso(df), df, hoje),
    ]
    conteudo_md = ''.join(partes)
    nome_arquivo = f'Relatório Semanal - {nome_projeto}.md'
    return conteudo_md, nome_arquivo


def _iso_para_br(valor):
    """Converte data ISO 'YYYY-MM-DD' (formato do JSON do PWA) para '%d/%m/%y'."""
    if not valor:
        return None
    try:
        return datetime.strptime(str(valor)[:10], '%Y-%m-%d').strftime('%d/%m/%y')
    except (ValueError, TypeError):
        return None


def gerar_relatorio_web_json(tarefas, nome_projeto, secao_comparativo=None):
    """Gera o relatório semanal a partir da lista de tarefas do JSON do PWA
    (mesmo formato de data/tasks_<id>.json usado pelos dashboards) — única porta
    de entrada do módulo. Retorna (conteudo_md, nome_arquivo).

    As chaves do JSON são traduzidas aqui para o vocabulário de colunas que o
    relatório usa, herdado das planilhas exportadas do Project."""
    linhas = []
    for t in tarefas:
        nivel = t.get('level')
        if nivel is None:
            nivel = t.get('outlineLevel')
        pct = t.get('pct') or 0
        linhas.append({
            'Nível_da_estrutura_de_tópicos': nivel,
            'Nome': t.get('name', ''),
            'Nomes_dos_Recursos': t.get('resources') or '',
            # Duração zero. Só a nota de tarefas sem recurso lê este campo.
            'Marco': bool(t.get('marco')),
            # O JSON guarda % concluída em escala 0–100; o relatório espera 0–1.
            'Porcentagem_Concluída': (pct / 100.0),
            'Início': _iso_para_br(t.get('start')),
            'Término': _iso_para_br(t.get('end')),
            'Início_da_Linha_de_Base': _iso_para_br(t.get('blStart')),
            'Término_da_linha_de_base': _iso_para_br(t.get('blEnd')),
        })
    df = pd.DataFrame(linhas)
    if df.empty:
        raise ValueError('Projeto sem tarefas disponíveis no snapshot do PWA.')
    return _montar_relatorio_md(df, nome_projeto, secao_comparativo)
