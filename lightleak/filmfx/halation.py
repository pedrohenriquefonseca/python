"""Halação (halation).

O fenômeno
----------
A luz atravessa as três camadas de emulsão, chega à base transparente do filme e
reflete na interface base/ar de volta para dentro da emulsão. Como a reflexão
acontece a uma distância — a espessura da base —, o retorno reaparece
*deslocado*: um halo em volta das altas-luzes, e não em cima delas.

Por que é vermelho: a camada sensível ao vermelho é a mais distante da lente,
ou seja, a que fica encostada na base. A luz que volta bate nela primeiro e com
menos atenuação, tanto da emulsão quanto do que sobrou da camada antihalo. Do
percurso de ida e volta é praticamente só o vermelho que sobrevive.

E quanto mais longe lateralmente a luz viaja dentro da base, mais material ela
atravessa — logo a cauda larga do halo é *mais* vermelha que o núcleo, que ainda
puxa laranja. O modelo reproduz isso dando uma cor própria a cada oitava da
pirâmide, em vez de tingir o halo inteiro de um vermelho só.

Duas âncoras físicas em vez de números escolhidos a olho:

* a amplitude parte da fração de luz que a base devolve, dominada por reflexão
  interna total e não por Fresnel simples — da ordem de 20%;
* o raio do halo é fração fixa do quadro, não do número de pixels, porque na
  película ele mede dezenas de micrômetros — escanear em mais dpi não aumenta o
  halo, então a pirâmide trabalha sempre na mesma escala relativa.

Ao contrário do vazamento de luz, a halação não tem nada de aleatório: é uma
resposta às altas-luzes da própria imagem. Duas fotos dão halos diferentes
porque as altas-luzes estão em lugares diferentes, não porque houve sorteio.
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

# Quanto de cada canal chega à base. O vermelho atravessa a emulsão com menos
# perda, então é ele que domina o que volta.
_PENETRATION = np.array([0.45, 0.40, 0.15], dtype=np.float32)

# Cor do halo por oitava: núcleo alaranjado, cauda vermelho-profunda.
_NEAR = np.array([1.00, 0.32, 0.13], dtype=np.float32)
_FAR = np.array([1.00, 0.05, 0.03], dtype=np.float32)

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
    """O slider é `intensity`. O resto tem default físico e fica disponível
    para a UI crescer depois."""

    intensity: float = 1.0     # 0 .. 3 — multiplica a fração de retorno
    threshold: float = 0.45    # luz linear a partir da qual há halação
    spec_boost: float = 8.0    # recupera o especular que o JPEG cortou em 1,0
    radius: float = 1.0        # multiplica o raio interno        0.3 .. 3
    falloff: float = 0.85      # peso de cada oitava mais larga
    levels: int = 5            # 5 oitavas cobrem ~0,6% a ~10% do quadro
    normalize: bool = True     # faz `intensity` valer o mesmo em fotos diferentes


def _resize(field: np.ndarray, size: tuple[int, int], filt) -> np.ndarray:
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
    """
    r = int(round(sigma))
    if r < 1:
        return a
    for _ in range(3):
        a = _box(_box(a, r, 0), r, 1)
    return a


def _source(lin: np.ndarray, p: HalationParams) -> np.ndarray:
    """Quanta luz chega à base, por pixel."""
    y = lin @ _PENETRATION
    e = np.clip((y - p.threshold) / max(1.0 - p.threshold, 1e-3), 0.0, 1.0)

    # Quadrático porque halação é fenômeno de especular: um céu claro quase não
    # halata, um ponto de luz estourado sim. E o termo de boost devolve a energia
    # do especular que o arquivo cortou em 1,0 — sem ele o halo de um ponto de
    # luz se dilui na média da pirâmide e some.
    return (e * e * (1.0 + p.spec_boost * np.power(e, 4))).astype(np.float32)


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

    # Uma oitava por nível: sigma 1, 2, 4... px de trabalho, ou seja, do raio
    # interno até dezesseis vezes ele. Cada oitava tem cor própria — quanto mais
    # longe a luz andou na base, mais vermelho sobrou dela.
    halo = np.zeros((ph, pw, 3), dtype=np.float32)
    total = 0.0
    for i in range(p.levels):
        weight = p.falloff**i
        t = i / max(p.levels - 1, 1)
        halo += weight * _gauss(small, 2.0**i)[..., None] * (_NEAR + (_FAR - _NEAR) * t)
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
        # Ancorar no pico do brilho recupera justamente isso — o halo fica com
        # força fixa em relação à sua fonte, seja ela ponto de luz ou parede. O
        # piso evita que uma foto sem alta-luz nenhuma seja amplificada até
        # inventar halação onde não há.
        peak = float(np.percentile(halo[..., 0], 99.9))
        halo *= _RETURN * p.intensity / max(peak, 0.05 * total)
    else:
        halo *= _RETURN * p.intensity / max(total, 1e-6)
    if (pw, ph) != (w, h):
        halo = np.dstack([_resize(halo[..., c], (w, h), Image.BICUBIC) for c in range(3)])
    return np.clip(halo, 0.0, None)


def apply(image_srgb: np.ndarray, p: HalationParams | None = None) -> np.ndarray:
    """Aplica a halação a uma imagem sRGB float [0,1] e devolve sRGB float."""
    p = p or HalationParams()
    lin = srgb_to_linear(image_srgb)
    return np.clip(linear_to_srgb(screen_add(lin, render_halo(image_srgb, p))), 0.0, 1.0)
