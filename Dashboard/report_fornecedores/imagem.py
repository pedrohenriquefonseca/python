# -*- coding: utf-8 -*-
"""O relatório de um fornecedor desenhado como imagem, para colar no Outlook.

A versão em HTML desta mensagem existia porque o corpo do e-mail é o editor do
Word. Ela morreu na prática: colado de verdade, o Word ignorou a largura das
células, espremeu a coluna dos documentos e quebrou cada código no hífen — e não
há CSS que o convença, porque ele remonta a tabela com as regras dele.

Uma imagem não tem esse problema. O Word não redesenha um PNG: ele cola o que
recebeu e, no máximo, reduz para caber na página. Em troca, o que chega ao
fornecedor deixa de ser texto — não dá para copiar um código de documento de
dentro dela —, e por isso o botão põe no clipboard a imagem E a lista em texto:
quem colar num campo sem formatação recebe a segunda.

Livre do Word, o desenho volta a ser o da tela: a grade dos meses e o fio de
hoje correm de cima a baixo sem se partir, os códigos de documento se separam
por ponto médio em vez de uma linha cada, e a largura é a que o relatório pede,
não a que o Outlook tolera.
"""
import datetime
import io
import os

from PIL import Image, ImageDraw, ImageFont

import report_fornecedores as rf

# LARGURA é fixa, e a régua fica com tudo o que as outras colunas não usarem.
#
# O tamanho importa por causa do Outlook: ele encolhe para a largura do corpo da
# mensagem qualquer imagem maior que ela, e encolher um desenho de texto é o
# mesmo que apagá-lo — a primeira versão saía com 2200 px, chegava reduzida a um
# terço e obrigava a abrir o anexo e rolar para ler. 1000 px cabe no corpo em
# janela normal.
#
# As colunas de texto têm largura constante, no mínimo que o conteúdo pede, e
# não crescem com o cronograma: é a régua que recebe a diferença. Ela é o que se
# olha primeiro, e espremê-la para dar espaço a uma lista de códigos troca o
# desenho pelo inventário.
#
# As fontes não encolhem — 11 px nos dados, 10 px nas notas, que é o piso abaixo
# do qual a suavização come a letra. O desenho é feito no dobro e reduzido no
# fim, com LANCZOS: é o supersampling que dá o acabamento nesse tamanho. O DPI
# gravado é 96, para o Word mostrar pixel por pixel em vez de esticar.
LARGURA = 700
ESCALA  = 2
DPI     = 96
MARGEM  = 16
PAD     = 13         # o respiro entre uma coluna e a seguinte

DOCS    = 240        # documentos
# VERSÃO, INÍCIO e TÉRMINO têm título e dado centralizados, e a largura de cada
# uma é o mais largo dos dois mais PAD — 6,5 px de respiro de cada lado. Nas
# datas quem manda é o título "TÉRMINO" (46 px, contra 45 da data dd/mm/aa), e
# as duas colunas ficam com os mesmos 59 px visíveis. TERMINO leva 6 px a mais
# porque o fio da régua corre dentro dela, FIO_GANTT antes do fim.
INICIO  = 59
TERMINO = 59 + 6
#
# O GANTT É SÓ MESES, TODOS DA MESMA LARGURA. A área visível — do fio que o
# separa da tabela até a margem direita da imagem — se divide em n partes iguais,
# uma por mês, e não sobra coluna vazia em ponta nenhuma. O limite esquerdo é o
# próprio fio; o direito, a margem da imagem, e ali o último mês se fecha com
# uma divisa como as outras.
#
# As datas que cada barra escreve ao lado de si disputam espaço com os meses, e
# toda barra escreve as duas: o início à esquerda, o término à direita. A que
# não couber sem passar do fio ou da margem vai para o outro lado, junto com a
# companheira, num "27/08 – 23/09" só. Sem o ano — ele está na coluna da tabela,
# e na régua só ocuparia o espaço que falta.
FIO_GANTT = 6        # o fio separador, à esquerda da coluna da régua
# A coluna da versão tem dois tamanhos, e não um por fornecedor: quase todo
# cronograma nomeia as etapas com uma letra — a, b, c — e aí quem manda é o
# título "VERSÃO" (38,5 px + PAD = 52); em alguns ela tem nome inteiro ("Projeto
# Legal de Arquitetura"), e aí a coluna abre e o que ainda não couber é cortado
# com reticências, para a entrega continuar em uma linha. O dado vai como está,
# sem prefixo "rev.".
VERSAO  = (52, 120)
ETAPA_CURTA = 4

# Não há coluna de situação, nem progresso dentro da barra. A barra é o período
# da etapa, e o que se lê nela é onde ela cai em relação a hoje. Percentual de
# execução é conversa de dentro de casa: mandado ao fornecedor vira discussão
# sobre o número, e não sobre a data que ele tem de cumprir.

# As cores da tela, e as mesmas regras: uma cor por fornecedor — o fio do topo e
# as barras —, o resto em escala de cinza, e o vermelho reservado para o fio de
# hoje e o atraso.
TINTA    = "#0f172a"
TEXTO    = "#111827"
APAGADO  = "#64748b"
CLARO    = "#94a3b8"
FIO      = "#f2f5f9"
GRADE    = "#e6ebf2"
HOJE     = "#dc2626"
ROTULO   = "#ffffff"      # o texto da etiqueta de hoje, sobre o vermelho
PONTA    = "#7c8899"      # as datas nas pontas da barra
FIO_COLUNA = "#cbd5e1"    # a divisa entre a tabela e a régua
FUNDO    = "#ffffff"

BARRA    = 13          # espessura da barra de uma entrega
LINHA    = 1.45        # entrelinha


def _fonte(tamanho, peso="normal"):
    """Segoe UI, a fonte da tela, com o que houver como reserva."""
    nomes = {"normal": ("segoeui.ttf", "DejaVuSans.ttf"),
             "semi":   ("seguisb.ttf", "segoeui.ttf", "DejaVuSans.ttf"),
             "bold":   ("segoeuib.ttf", "DejaVuSans-Bold.ttf")}[peso]
    for nome in nomes:
        for base in (r"C:\Windows\Fonts", ""):
            try:
                return ImageFont.truetype(os.path.join(base, nome) if base else nome,
                                          int(tamanho * ESCALA))
            except OSError:
                continue
    return ImageFont.load_default()


# As fontes, uma vez só. São elas o piso da legibilidade — o que encolhe é o
# espaço em volta — e `_colunas` mede com a mesma fonte que vai escrever.
# 10 px é o piso: abaixo disso a suavização come a letra e a nota de rodapé
# deixa de se ler no tamanho em que a mensagem chega.
_F = {"titulo": _fonte(18, "bold"), "sub": _fonte(10.5), "cab": _fonte(10, "bold"),
      "ini": _fonte(12, "bold"), "disc": _fonte(10, "bold"), "nota": _fonte(10),
      "doc": _fonte(11), "data": _fonte(11),
      "mes": _fonte(10, "bold"), "hoje": _fonte(9, "bold"),
      "ponta": _fonte(8.5)}

# Um medidor de 1x1: a largura de um texto não depende de onde ele será escrito.
_REGUA = ImageDraw.Draw(Image.new("RGB", (1, 1)))


def _larg(txt, f):
    return _REGUA.textlength(txt, f) / ESCALA


def _cortar(txt, f, largura):
    """O texto inteiro, ou o começo dele com reticências."""
    if _larg(txt, f) <= largura:
        return txt
    corte = txt
    while corte and _larg(corte + "…", f) > largura:
        corte = corte[:-1]
    return (corte.rstrip() + "…") if corte else ""


def _resumo(itens, f, largura, sep=" · "):
    """Os códigos que couberem numa linha, e um +N pelos que sobraram.

    Uma entrega ocupa UMA linha. A lista completa de documentos, quebrada em
    tantas linhas quantas precisasse, empurrava a disciplina para seis, oito
    linhas e afastava a barra da data que ela desenha — e quem lê a mensagem
    quer ver o calendário, não conferir inventário. A lista inteira continua na
    versão em texto, que vai no mesmo clipboard.
    """
    if not itens:
        return ""
    for k in range(len(itens), 0, -1):
        texto = sep.join(itens[:k])
        if k < len(itens):
            texto += f'  +{len(itens) - k}'
        if _larg(texto, f) <= largura:
            return texto
    # Nem o primeiro código cabe: corta ele e conta o resto assim mesmo.
    sufixo = f'  +{len(itens) - 1}' if len(itens) > 1 else ""
    return _cortar(itens[0], f, largura - _larg(sufixo, f)) + sufixo


def _dm(iso):
    """09/10: a data da ponta da barra, sem o ano."""
    return datetime.date.fromisoformat(iso).strftime("%d/%m")


class _Tela:
    """Um bloco de desenho que sabe a régua do gantt e a escala do papel."""

    def __init__(self, dr, esc, x_regua, w_regua):
        self.dr, self.esc = dr, esc
        self.x, self.w = x_regua, w_regua

    def texto(self, x, y, txt, f, cor):
        self.dr.text((x * ESCALA, y * ESCALA), txt, font=f, fill=cor)

    def caixa(self, x, y, w, h, cor):
        if w <= 0 or h <= 0:
            return
        self.dr.rectangle([round(x * ESCALA), round(y * ESCALA),
                           round((x + w) * ESCALA) - 1, round((y + h) * ESCALA) - 1],
                          fill=cor)

    def px(self, d, fim_do_dia=False):
        """O pixel da régua onde a data cai — a mesma conta da versão em HTML."""
        return self.x + rf.posicao(self.esc, d, self.w, fim_do_dia)


def _etiqueta_hoje(img, x, y):
    """"Hoje" em pé, branco sobre vermelho, no alto do fio.

    Em pé porque deitada ela cobriria dois meses da régua; no alto porque é de
    cima que se começa a ler a tabela, e ali ela não tapa barra nenhuma. O texto
    é desenhado deitado numa tira e a tira é girada: PIL não escreve na vertical.
    """
    f = _F["hoje"]
    # A caixa sai da métrica real do texto, e não do corpo da fonte: com 7,5 px
    # a sobra de um pixel é a diferença entre caber e cortar o rabo do "j".
    e, n, d, sul = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), "Hoje", f)
    px, py = 4 * ESCALA, 3 * ESCALA               # respiro dentro da etiqueta
    tira = Image.new("RGB", (d - e + 2 * px, sul - n + 2 * py), HOJE)
    ImageDraw.Draw(tira).text((px - e, py - n), "Hoje", font=f, fill=ROTULO)
    tira = tira.rotate(270, expand=True)          # lê de cima para baixo
    img.paste(tira, (round(x * ESCALA) - tira.width // 2, round(y * ESCALA)))


def _colunas(forn):
    """(x de cada coluna, largura de cada uma, se a etapa leva o prefixo "rev.").

    As quatro colunas de texto são constantes; a régua leva o que sobrar dos
    1000 px. A única coisa que varia é a coluna da versão, que tem dois tamanhos
    conforme o cronograma nomeie as etapas por letra ou por extenso.
    """
    etapas = [str(l["etapa"]) for l in rf.entregas(forn)]
    curta  = not any(len(e) > ETAPA_CURTA for e in etapas)
    versao = VERSAO[0] if curta else VERSAO[1]

    larguras = [DOCS, versao, INICIO, TERMINO,
                LARGURA - 2 * MARGEM - DOCS - versao - INICIO - TERMINO]
    xs, x = [], MARGEM
    for w in larguras:
        xs.append(x)
        x += w
    return xs, larguras, curta


def desenhar(forn, nome_projeto, hoje):
    """O relatório de um fornecedor como PNG, pronto para o clipboard."""
    esc = rf.escala(forn)
    xs, ws, curta = _colunas(forn)
    cor = forn["cor"] if str(forn["cor"]).startswith("#") else rf.COR_PADRAO

    f_titulo, f_sub, f_cab = _F["titulo"], _F["sub"], _F["cab"]
    f_ini, f_disc, f_nota  = _F["ini"], _F["disc"], _F["nota"]
    f_doc, f_data          = _F["doc"], _F["data"]
    f_mes                  = _F["mes"]

    alt_doc = f_doc.size / ESCALA * LINHA

    # ── medir ────────────────────────────────────────────────────────────────
    # Uma passada só para saber a altura da imagem: cada linha guarda o que vai
    # escrever e quanto isso ocupa, e o desenho depois só percorre a lista.
    corpo = []
    for ini in forn["iniciativas"]:
        corpo.append(("iniciativa", ini["nome"], 30))
        for disc in ini["disciplinas"]:
            if disc["nome"].strip().casefold() != ini["nome"].strip().casefold():
                corpo.append(("disciplina", (disc["nome"], disc["documentos"]), 23))
            for l in disc["linhas"]:
                docs  = _resumo(l["documentos"], f_doc, ws[0] - PAD)
                etapa = _cortar(str(l["etapa"]), f_data, ws[1] - PAD)
                corpo.append(("entrega", (l, docs, etapa),
                              round(7 + alt_doc + 6)))

    y_cab = 4 + 11 + 25 + 17 + 17 + 12         # fio, título, subtítulo, resumo
    y_tabela = y_cab + 23
    altura_corpo = sum(h for _, _, h in corpo)
    total = y_tabela + altura_corpo + MARGEM

    img = Image.new("RGB", (LARGURA * ESCALA, round(total) * ESCALA), FUNDO)
    dr  = ImageDraw.Draw(img)
    # A área que se vê como gantt começa no fio e termina na margem da imagem,
    # e é ela inteira que os meses dividem.
    esquerda = xs[-1] - FIO_GANTT
    t   = _Tela(dr, esc, esquerda, ws[-1] + FIO_GANTT)

    # ── cabeçalho da mensagem ────────────────────────────────────────────────
    t.caixa(0, 0, LARGURA, 4, cor)             # a cor do fornecedor abre, como na tela
    y = 4 + 11
    t.texto(MARGEM, y, f'Próximas entregas — {forn["nome"]}', f_titulo, TINTA)
    y += 25
    t.texto(MARGEM, y, f'{nome_projeto}  ·  posição do cronograma em '
                       f'{hoje:%d/%m/%Y}', f_sub, APAGADO)
    y += 17
    a_iniciar = forn["documentos"] - forn["andamento"]
    resumo = (f'{forn["documentos"]} documentos  ·  {forn["andamento"]} em '
              f'andamento  ·  {a_iniciar} a iniciar')
    t.texto(MARGEM, y, resumo, f_sub, TEXTO)

    # ── a régua, desenhada de uma vez ────────────────────────────────────────
    # Aqui está o ganho sobre o HTML: a grade dos meses e o fio de hoje são duas
    # linhas contínuas do cabeçalho ao rodapé da tabela, e não um pedaço por
    # linha que precisava casar com a altura do texto ao lado para não se partir.
    fim_tabela = y_tabela + altura_corpo
    # O fio que separa a tabela da régua: daqui para a direita é desenho, e não
    # mais texto, e a divisa faz a leitura mudar de chave.
    t.caixa(xs[-1] - FIO_GANTT, y_cab, 1, fim_tabela - y_cab, FIO_COLUNA)
    if esc:
        # Só as divisas internas: o fio que separa o gantt da tabela fecha a
        # régua à esquerda e a margem da imagem a fecha à direita.
        # A última fecha o último mês, junto da margem.
        for k in range(1, esc["n"]):
            t.caixa(t.x + round(k * t.w / esc["n"]), y_cab, 1,
                    fim_tabela - y_cab, GRADE)
        t.caixa(t.x + t.w - 1, y_cab, 1, fim_tabela - y_cab, GRADE)
        passo = max(1, int(-(-34 * esc["n"] // t.w)))
        for i in range(0, esc["n"], passo):
            a = t.x + round(i * t.w / esc["n"])
            b = t.x + round(min(i + passo, esc["n"]) * t.w / esc["n"])
            m = esc["mes"] - 1 + i
            rot = f'{rf._MESES[m % 12]}/{str(esc["ano"] + m // 12)[2:]}'
            t.texto(a + (b - a - _larg(rot, f_mes)) / 2, y_cab + 3, rot, f_mes, APAGADO)

    # ── cabeçalho das colunas ────────────────────────────────────────────────
    # O fim da coluna TÉRMINO é o fio da régua, e não o começo da régua.
    fins = (None, xs[2], xs[3], esquerda)

    def centro(i, txt, f):
        return xs[i] + (fins[i] - xs[i] - _larg(txt, f)) / 2

    t.texto(xs[0], y_cab + 4, "DOCUMENTOS", f_cab, APAGADO)
    for i, nome in ((1, "VERSÃO"), (2, "INÍCIO"), (3, "TÉRMINO")):
        t.texto(centro(i, nome, f_cab), y_cab + 4, nome, f_cab, APAGADO)
    t.caixa(MARGEM, y_tabela - 2, LARGURA - 2 * MARGEM, 1.5, TINTA)

    # ── o corpo ──────────────────────────────────────────────────────────────
    y = y_tabela
    rotulos = []        # as datas das barras, escritas depois do fio de hoje
    for tipo, dado, h in corpo:
        if tipo == "iniciativa":
            t.texto(xs[0], y + 9, dado, f_ini, TINTA)
            t.caixa(MARGEM, y + h - 1, xs[-1] - MARGEM - 10, 1, TINTA)
        elif tipo == "disciplina":
            nome, n = dado
            t.texto(xs[0], y + 6, nome, f_disc, "#334155")
            t.texto(xs[0] + _larg(nome, f_disc) + 9, y + 7,
                    f'{n} documento{"s" if n > 1 else ""}', f_nota, CLARO)
        else:
            l, docs, etapa = dado
            t.texto(xs[0], y + 6, docs, f_doc, "#334155")
            d_ini, d_fim = rf._br(l["inicio"]), rf._br(l["termino"])
            t.texto(centro(1, etapa, f_data), y + 6, etapa, f_data, APAGADO)
            t.texto(centro(2, d_ini, f_data), y + 6, d_ini, f_data, APAGADO)
            t.texto(centro(3, d_fim, f_data), y + 6, d_fim, f_data, TEXTO)
            # A barra fica na altura da primeira linha de texto, ao lado das
            # datas que ela desenha.
            if esc and l["inicio"] and l["termino"]:
                a = t.px(datetime.date.fromisoformat(l["inicio"]))
                b = max(t.px(datetime.date.fromisoformat(l["termino"]), True), a + 3)
                yb = y + 6 + (alt_doc - BARRA) / 2
                t.caixa(a, yb, b - a, BARRA, cor)
                # As datas encostadas nas pontas, como na tela: a barra deixa de
                # depender da régua lá em cima para dizer quando começa e acaba.
                # A ponta sem espaço junta as duas datas do lado que tem.
                fp  = _F["ponta"]
                ini = _dm(l["inicio"])
                fim = _dm(l["termino"])
                par = f"{ini} – {fim}"
                ty  = yb + (BARRA - fp.size / ESCALA) / 2 - 1
                xi  = a - 5 - _larg(ini, fp)
                cabe_fim = b + 5 + _larg(fim, fp) <= t.x + t.w - 3
                if xi >= esquerda + 2 and cabe_fim:
                    rotulos += [(xi, ty, ini), (b + 5, ty, fim)]
                elif cabe_fim:
                    rotulos.append((b + 5, ty, par))
                else:
                    # Barra que cobre a régua inteira: o par vai por cima dela,
                    # mas não invade a tabela.
                    rotulos.append((max(a - 5 - _larg(par, fp), esquerda + 2), ty, par))
            t.caixa(MARGEM, y + h - 1, LARGURA - 2 * MARGEM, 1, FIO)
        y += h

    # O fio de hoje por cima de tudo, inclusive das barras — é contra ele que se
    # lê se a barra está para trás ou para a frente.
    # Começa abaixo dos nomes dos meses: subindo até eles, o fio riscaria o
    # rótulo em que por acaso caísse.
    if esc and esc["de"] <= hoje <= esc["ate"]:
        x = t.px(hoje)
        t.caixa(x - 1, y_tabela, 2, fim_tabela - y_tabela, HOJE)
        _etiqueta_hoje(img, x, y_tabela)

    # As datas das barras por cima do fio de hoje, cada uma num respiro branco:
    # com o fio por cima, a data em que ele caísse sairia riscada ao meio.
    fp = _F["ponta"]
    for x, y, txt in rotulos:
        t.caixa(x - 1, y + 1, _larg(txt, fp) + 2, fp.size / ESCALA + 1, FUNDO)
        t.texto(x, y, txt, fp, PONTA)

    # Paleta de 128 cores. O desenho tem meia dúzia de cores e o resto é a
    # suavização das letras; indexado, o arquivo cai a 40% do tamanho sem
    # diferença que se veja lado a lado — e é um anexo de e-mail que vai no
    # caminho.
    saida = io.BytesIO()
    img = img.resize((LARGURA, round(total)), Image.LANCZOS)
    img.quantize(colors=128, method=Image.MEDIANCUT).save(
        saida, "PNG", dpi=(DPI, DPI), optimize=True)
    return saida.getvalue()
