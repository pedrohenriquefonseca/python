"""Halação e brilho (glow) em volta das altas-luzes.

O fenômeno
----------
A luz atravessa as três camadas de emulsão, chega à base transparente do filme e
reflete na interface base/ar de volta para dentro da emulsão. Como a reflexão
acontece a uma distância — a espessura da base —, o retorno reaparece
*deslocado*: um halo em volta das altas-luzes, e não em cima delas.

Duas âncoras físicas em vez de números escolhidos a olho:

* a amplitude parte da fração de luz que a base devolve, dominada por reflexão
  interna total e não por Fresnel simples — da ordem de 20%;
* o raio do halo é fração fixa do quadro, não do número de pixels, porque na
  película ele mede dezenas de micrômetros — escanear em mais dpi não aumenta o
  halo, então a pirâmide trabalha sempre na mesma escala relativa.

Ao contrário do vazamento de luz, isto não tem nada de aleatório: é uma resposta
às altas-luzes da própria imagem. Duas fotos dão halos diferentes porque as
altas-luzes estão em lugares diferentes, não porque houve sorteio.

Halação pura é vermelha, glow carrega a cor da fonte
----------------------------------------------------
Na halação estrita a cor não depende da fonte: quem recebe a luz refletida é a
camada sensível ao vermelho, a mais próxima da base, então o retorno é vermelho
mesmo que a fonte fosse azul. Só que o brilho que se vê em volta de um neon
numa fotografia não é só isso — vem junto o espalhamento na emulsão e no vidro
da lente, que *preserva* a cor da fonte. Um tubo vermelho brilha vermelho, o
reflexo do sol na água brilha amarelo-quente.

Os dois são o mesmo transporte de luz com atenuação espectral diferente, e é
assim que estão implementados: um só efeito com o controle `redshift`.

* `redshift = 0` — o brilho tem a cromaticidade da própria fonte (glow);
* `redshift = 1` — o brilho é filtrado pela penetração das camadas e avermelha
  quanto mais longe viaja (halação de filme).

Por isso a fonte deixou de ser medida por luminância. Uma luminância ponderada é
cega justamente para a luz que mais brilha na prática: um neon vermelho saturado
tem um canal alto e dois no chão, e a média dele não chega nem perto do limiar
de uma parede branca — no modelo anterior a parede halatava mil vezes mais que o
tubo de neon, e verde e azul saturados davam exatamente zero.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

from .imaging import linear_to_srgb, screen_add, srgb_to_linear

# Fração da luz que volta para a emulsão. É daqui que sai a escala do efeito.
#
# A conta ingênua — Fresnel em incidência normal numa base de poliéster (n≈1,65)
# — dá só ~6%, e com ela o halo fica invisível. Mas ela é a conta errada: a luz
# que chega à base já foi espalhada pela emulsão e incide numa distribuição
# ampla de ângulos, e tudo além do ângulo crítico (~37°) sofre reflexão interna
# *total*. Para uma distribuição difusa a fração que escapa é 1/n² ≈ 0,37, ou
# seja, cerca de 63% volta inteira. É por isso que a halação é muito mais forte
# do que 6% faria supor. Descontando a absorção da emulsão na ida e na volta e o
# que resta da camada antihalo, sobra a ordem de 20%.
_RETURN = 0.22

# Exposição somada no pico do halo, com `normalize` ligado e `intensity = 1`.
#
# Não é 0,22, e não deveria ser: `_RETURN` é a fração da luz *original* da cena,
# e essa luz não está no arquivo — o JPEG cortou toda alta-luz em 1,0. Quando a
# normalização reancora o halo, ela está justamente reinflando a faixa dinâmica
# perdida, então o alvo tem de ser a exposição que a fonte real teria devolvido,
# uma ordem de grandeza acima. Em 0,22 o pico do brilho dava sRGB 0,48 — cinza
# médio — e o efeito sumia sobre qualquer coisa clara.
#
# O valor é o efeito cheio, calibrado a olho nas duas fotos de referência: é o
# ponto em que o halo já queima em volta da alta-luz sem lavar a sombra.
_PEAK = 1.87

# Quanto de cada canal sobrevive ao percurso até a base e de volta, relativo ao
# vermelho. O vermelho atravessa a emulsão com menos perda, então é ele que
# domina o retorno. Só entra na conta na medida de `redshift`.
_PENETRATION = np.array([1.00, 0.62, 0.30], dtype=np.float32)

# Atenuação adicional da oitava mais larga: quanto mais longe lateralmente a luz
# andou dentro da base, mais material atravessou, e menos sobrou de verde e
# azul. É daqui que sai a cauda mais vermelha que o núcleo.
_FAR = np.array([1.00, 0.22, 0.10], dtype=np.float32)

# Peso relativo da luminância, para ancorar a normalização.
_LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

# Raio interno do halo, em fração do lado maior do quadro.
#
# Halação tem raio *mínimo*: a luz volta deslocada pelo dobro da espessura da
# base, e não menos. Numa base de ~125 µm sobre um quadro de 36 mm isso dá algo
# como 0,6% da largura. Sem esse piso a pirâmide começa em 1 px, as oitavas
# minúsculas ficam com metade do peso e o resultado vira um contorno duro em
# volta da alta-luz em vez de um brilho.
_INNER_RADIUS = 0.010


@dataclass
class HalationParams:
    """Os sliders são `intensity` e `redshift`. O resto tem default físico e
    fica disponível para a UI crescer depois."""

    intensity: float = 1.0     # 0 .. 3 — multiplica a fração de retorno
    redshift: float = 1.0      # 0 .. 1 — 0 glow na cor da fonte, 1 halação vermelha
    threshold: float = 0.62    # luz linear a partir da qual há brilho
    spec_boost: float = 8.0    # recupera o especular que o JPEG cortou em 1,0
    radius: float = 1.0        # multiplica o raio interno        0.3 .. 3
    falloff: float = 0.50      # peso de cada oitava mais larga
    levels: int = 2            # ver nota sobre o pedestal em render_halo
    normalize: bool = True     # faz `intensity` valer o mesmo em fotos diferentes


def _resize(field: np.ndarray, size: tuple[int, int], filt) -> np.ndarray:
    if field.ndim == 3:
        return np.dstack([_resize(field[..., c], size, filt) for c in range(field.shape[2])])
    return np.asarray(
        Image.fromarray(field.astype(np.float32), mode="F").resize(size, filt),
        dtype=np.float32,
    )


def _box(a: np.ndarray, r: int, axis: int) -> np.ndarray:
    """Média móvel exata por soma acumulada — O(n) e sem overshoot."""
    k = 2 * r + 1
    pad = np.pad(a, [(r, r) if i == axis else (0, 0) for i in range(a.ndim)], mode="edge")
    c = np.cumsum(pad, axis=axis, dtype=np.float32)
    c = np.concatenate([np.zeros_like(np.take(c, [0], axis=axis)), c], axis=axis)
    n = a.shape[axis]
    hi = np.take(c, np.arange(k, k + n), axis=axis)
    lo = np.take(c, np.arange(0, n), axis=axis)
    return ((hi - lo) / k).astype(np.float32)


def _gauss(a: np.ndarray, sigma: float) -> np.ndarray:
    """Três box blurs aproximam bem uma gaussiana de desvio ~= o raio da caixa.

    É preciso ser gaussiana de verdade: uma pirâmide de mips reamostrada com
    bicúbica gera ringing — lóbulos negativos — quando a ampliação passa de umas
    poucas vezes, e o halo em vez de brilho vira contorno com borda escura.

    Três passagens de caixa de raio r dão desvio sqrt(r(r+1)) — daí o r a partir
    do sigma pedido, e não r = sigma, que deixava cada oitava 40% larga demais.
    """
    r = int(round((np.sqrt(1.0 + 4.0 * sigma * sigma) - 1.0) / 2.0))
    if r < 1:
        return a
    for _ in range(3):
        a = _box(_box(a, r, 0), r, 1)
    return a


def _source(lin: np.ndarray, p: HalationParams) -> np.ndarray:
    """Quanta luz chega à base, e em que cor.

    Duas medidas separadas, e é a separação que faz o modelo funcionar:

    *Quanto* vem do canal mais forte. Uma luminância ponderada é cega justamente
    para a luz que mais brilha na prática — um neon vermelho saturado tem um
    canal no teto e dois no chão, e a média dele fica abaixo do limiar de uma
    parede branca. Pelo canal mais forte, cada fonte dispara pelo canal que ela
    de fato satura.

    *Em que cor* vem da cromaticidade da fonte em luz linear. Passar o joelho em
    cada canal separadamente e só então tomar a razão não serve: o canal que
    passa raspando é esmagado pelo quadrado, e uma lâmpada âmbar saía com brilho
    vermelho puro. A razão tem de ser medida antes do joelho, na luz como ela é.
    """
    m = lin.max(axis=2, keepdims=True)
    e = np.clip((m - p.threshold) / max(1.0 - p.threshold, 1e-3), 0.0, 1.0)

    # Quadrático porque é fenômeno de especular: um céu claro quase não brilha,
    # um ponto de luz estourado sim. O boost devolve a energia do especular que o
    # arquivo cortou em 1,0 — sem ele o halo de um ponto de luz se dilui na média
    # da pirâmide e some.
    strength = e * e * (1.0 + p.spec_boost * np.power(e, 4))
    return (strength * (lin / np.maximum(m, 1e-6))).astype(np.float32)


def _tint(p: HalationParams, t: float) -> np.ndarray:
    """Multiplicador por canal da oitava `t` ∈ [0,1], do núcleo à cauda.

    Em `redshift = 0` é [1,1,1] em todas as oitavas: o brilho sai exatamente na
    cor que a fonte tinha. Subindo o controle, entra a penetração das camadas no
    núcleo e a atenuação de percurso na cauda, e o resultado converge para a
    halação de filme — cauda mais vermelha que o núcleo.
    """
    near = 1.0 + (_PENETRATION - 1.0) * p.redshift
    far = 1.0 + (_PENETRATION * _FAR - 1.0) * p.redshift
    tint = near + (far - near) * t

    # A luz que deixa de sensibilizar o verde e o azul não some do sistema: ela é
    # absorvida pela camada do vermelho, que é a que recebe o retorno da base.
    # Então o que os outros dois canais perdem vai **para o vermelho**, e não
    # redistribuído nos três — redistribuir devolvia o verde para perto de 1 e o
    # halo saía creme em vez de vermelho, justamente o oposto do efeito.
    tint[0] = 3.0 - tint[1] - tint[2]
    return tint.astype(np.float32)


def render_halo(image_srgb: np.ndarray, p: HalationParams) -> np.ndarray:
    """Halo em luz linear, no tamanho da imagem — pronto para somar."""
    h, w = image_srgb.shape[:2]
    src = _source(srgb_to_linear(image_srgb), p)

    # Resolução de trabalho em que *um* pixel vale o raio interno. É a própria
    # redução que produz o borrão do primeiro nível — por isso ela tem de ser
    # agressiva. Se a resolução de trabalho ficar perto da original, o nível 0
    # sai sem borrão nenhum e só realça a alta-luz, sem gerar brilho ao redor.
    inner = _INNER_RADIUS * max(p.radius, 1e-3)
    pw, ph = (max(16, int(round(d / (inner * max(w, h))))) for d in (w, h))
    small = _resize(src, (pw, ph), Image.BOX)   # BOX preserva a energia da fonte

    # Uma oitava por nível: sigma 1, 2, 4... px de trabalho, ou seja, o raio
    # interno, o dobro dele, e assim por diante. O borrão é feito nos três
    # canais, e não num mapa escalar depois tingido: só assim a cor viaja junto
    # com a luz e duas fontes de cores diferentes no mesmo quadro dão brilhos
    # diferentes.
    #
    # Poucas oitavas, e de propósito. Uma oitava larga espalhada sobre 10% do
    # quadro não vira brilho, vira pedestal: ela sobe o quadro inteiro alguns
    # pontos e o que se vê é véu, não halo. Pior ainda porque a normalização
    # ancora no pico — quando o pedestal domina, o pico é o próprio pedestal e
    # tudo é escalado por ele. Com duas oitavas o brilho fica onde a luz está, e
    # a sombra continua sombra.
    halo = np.zeros((ph, pw, 3), dtype=np.float32)
    total = 0.0
    for i in range(p.levels):
        weight = p.falloff**i
        t = i / max(p.levels - 1, 1)
        blurred = np.dstack([_gauss(small[..., c], 2.0**i) for c in range(3)])
        halo += weight * blurred * _tint(p, t)
        total += weight

    if p.normalize:
        # Normaliza pelo pico do *brilho já borrado*, não pela fonte.
        #
        # O borrão conserva energia, então um ponto de luz se espalha e some,
        # enquanto uma área clara grande atravessa quase intacta — medido, o pico
        # variava mais de 100x entre fotos. Conservar energia só estaria certo se
        # a gente soubesse o brilho real da cena, e não sabe: o JPEG cortou toda
        # alta-luz em 1,0. Um poste de neon que era mil vezes o entorno chega aqui
        # valendo o mesmo que um muro branco.
        #
        # A âncora é a luminância do halo, não o canal vermelho: com o brilho
        # herdando a cor da fonte, medir só o vermelho daria escalas diferentes
        # para um letreiro verde e um âmbar de mesmo brilho. O piso evita que uma
        # foto sem alta-luz nenhuma seja amplificada até inventar brilho onde não
        # há.
        peak = float(np.percentile(halo @ _LUMA, 99.9))
        halo *= _PEAK * p.intensity / max(peak, 0.05 * total)
    else:
        halo *= _RETURN * p.intensity / max(total, 1e-6)
    if (pw, ph) != (w, h):
        halo = _resize(halo, (w, h), Image.BICUBIC)
    return np.clip(halo, 0.0, None)


def apply(image_srgb: np.ndarray, p: HalationParams | None = None) -> np.ndarray:
    """Aplica o efeito a uma imagem sRGB float [0,1] e devolve sRGB float."""
    p = p or HalationParams()
    lin = srgb_to_linear(image_srgb)
    return np.clip(linear_to_srgb(screen_add(lin, render_halo(image_srgb, p))), 0.0, 1.0)
