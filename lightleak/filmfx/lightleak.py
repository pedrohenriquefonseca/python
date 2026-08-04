"""Vazamento de luz (light leak) generativo.

Modelo físico
-------------
A composição acontece em luz linear: no filme a luz parasita não "mistura" com a
imagem, ela *soma exposição* no negativo (`L = L_imagem + L_vaz`). Isso reproduz
de graça três assinaturas do efeito real — preto levantado, contraste local
derrubado e estouro para branco no núcleo.

A cor não é RGB fixo: é o corante do filme. Um vazamento tem a cor de *quais
camadas* a luz sensibilizou, então amarelo/ciano/magenta — as três camadas — são
a parametrização natural, com o branco como quarto polo (as três por igual, só
luminosidade). Cada polo dá um expoente por canal, e o canal fraco recebe
expoente alto: ele some na franja e só volta no núcleo, que por isso satura em
branco. A rampa corante → branco cai daí sozinha, sem gradiente pintado à mão, e
só aparece se a queda for estreita — que é o caso das frentes rasgadas reais.

Por que quase todo leak é uma coluna vertical
---------------------------------------------
O caso clássico não é a tampa traseira: é o feltro da boca do cartucho. A luz
entra ali e caminha *entre as camadas enroladas* do filme, velando uma faixa que
atravessa a largura da fita — o que num quadro deitado aparece como uma banda
vertical de altura inteira. Ela para numa frente irregular, onde as camadas se
encostam: daí a borda rasgada, dura, tipo papel queimado, e não um degradê suave.

Primitivas:
    band   coluna com duas frentes independentes, platô estourado e estrias
    bloom  brilho difuso ancorado numa borda ou canto (fresta larga, luz oblíqua)
    wash   véu direcional amplo — luz difusa de início/fim de rolo
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field as dc_field

import numpy as np

from . import noise
from .imaging import (
    linear_to_srgb,
    resize_field,
    screen_add,
    srgb_to_linear,
)

KINDS = ("band", "bloom", "wash")

# As frentes rasgadas são de alta frequência: reamostrar de longe as amaciaria
# justamente onde está o caráter do efeito.
_PROC_LONG_SIDE = 2400


@dataclass
class LeakParams:
    """Controles expostos ao usuário (viram sliders na UI)."""

    intensity: float = 1.0    # amplitude global                     0 .. 2
    palette: str = "auto"     # corante: ver PALETTES; 'permutar' cicla as oito
    chroma: float = 1.0       # 0 = vazamento branco · 1 = corante cheio
    spread: float = 1.0       # largura das bandas / alcance          0.3 .. 2
    softness: float = 1.0     # maciez das frentes                    0.3 .. 2
    complexity: float = 1.0   # quantidade de fontes (sorteio livre)  0 .. 2
    texture: float = 1.0      # raggedness das frentes + estrias      0 .. 2
    veil: float = 0.22        # névoa global de flare interno         0 .. 1
    grain: float = 0.5        # granulado dentro do vazamento         0 .. 1
    seed: int = 0


@dataclass
class Recipe:
    """Resultado de um 'Generate': a receita completa e reproduzível."""

    seed: int
    preset: str = "random"
    palette: str = "auto"
    sources: list[dict] = dc_field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- utilidades


def _smoothstep(edge0: float, edge1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - edge0) / max(edge1 - edge0, 1e-6), 0.0, 1.0)
    return (t * t * (3.0 - 2.0 * t)).astype(np.float32)


def _blur(field: np.ndarray, factor: int) -> np.ndarray:
    """Borrão barato: reduz e amplia de volta com bicúbica."""
    h, w = field.shape
    sw, sh = max(2, w // factor), max(2, h // factor)
    return resize_field(resize_field(field, (sw, sh)), (w, h))


def _proc_size(w: int, h: int) -> tuple[int, int]:
    scale = _PROC_LONG_SIDE / max(w, h)
    if scale >= 1.0:
        return w, h
    return max(8, int(round(w * scale))), max(8, int(round(h * scale)))


def _coords(w: int, h: int) -> tuple[np.ndarray, np.ndarray, float]:
    """X e Y normalizados em [0,1]. As bandas são autoradas em fração do quadro,
    não em unidades isotrópicas — é assim que se lê uma referência."""
    aspect = w / h
    x = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]
    y = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    return np.repeat(x, h, axis=0), np.repeat(y, w, axis=1), aspect


# ------------------------------------------------------------------ primitivas


def _field_band(src: dict, X, Y, aspect) -> np.ndarray:
    rng = np.random.default_rng(src["noise_seed"])
    ca, sa = np.cos(src["angle"]), np.sin(src["angle"])
    v = X * ca + Y * sa   # através da banda
    u = -X * sa + Y * ca  # ao longo dela

    # Cada frente tem ruído próprio: as duas bordas de um leak real não são
    # espelhadas nem correlacionadas — uma pode ser dura e a outra difusa.
    z = np.zeros_like(u)
    rag = src["ragged"]
    fl = noise.fbm(rng, u, z, octaves=6, freq_u=src["rag_freq"], freq_v=0.0, gain=0.62)
    fr = noise.fbm(rng, u, z, octaves=6, freq_u=src["rag_freq"] * 1.37, freq_v=0.0, gain=0.62)
    left = src["center"] - src["halfwidth"] + rag * (fl - 0.5) * 2.0
    right = src["center"] + src["halfwidth"] + rag * (fr - 0.5) * 2.0

    # Fora de cada frente cai com dureza própria; entre elas o campo vale 1 — é o
    # platô estourado, sem detalhe, que ocupa boa parte do quadro nas referências.
    dl = np.maximum(left - v, 0.0) / max(src["soft_l"], 1e-5)
    dr = np.maximum(v - right, 0.0) / max(src["soft_r"], 1e-5)
    f = np.exp(-np.power(np.clip(dl, 0, 20), src["k_l"])) * np.exp(
        -np.power(np.clip(dr, 0, 20), src["k_r"])
    )

    # Estrias: variam através da banda e persistem ao longo dela — são o rastro do
    # filme enrolado, por isso correm sempre paralelas à coluna.
    if src.get("striations", 0) > 0:
        st = noise.fbm(rng, v, u, octaves=4, freq_u=src["stri_freq"], freq_v=0.7, gain=0.55)
        f = f * (1.0 - src["striations"] * 0.55 * (1.0 - st))

    return np.clip(f, 0.0, 1.0)


def _field_bloom(src: dict, X, Y, aspect) -> np.ndarray:
    rng = np.random.default_rng(src["noise_seed"])
    dx = (X - src["cx"]) * aspect
    dy = Y - src["cy"]
    ct, st = np.cos(src["theta"]), np.sin(src["theta"])
    a = (dx * ct + dy * st) / max(src["ra"], 1e-4)
    b = (-dx * st + dy * ct) / max(src["rb"], 1e-4)
    r = np.sqrt(a * a + b * b)

    ang = np.arctan2(b, a) / (2 * np.pi) + 0.5
    lobe = noise.fbm(rng, ang, r * 0.35, octaves=3, freq_u=src["lobes"], freq_v=1.0)
    r = r * (1.0 + src["wobble"] * (lobe - 0.5))
    return np.clip(np.exp(-np.power(np.clip(r, 0, 12), src["k"])), 0.0, 1.0)


def _field_wash(src: dict, X, Y, aspect) -> np.ndarray:
    ca, sa = np.cos(src["angle"]), np.sin(src["angle"])
    proj = (X - 0.5) * ca + (Y - 0.5) * sa
    return _smoothstep(float(np.max(proj)), -0.5 * src["reach"], proj)


_FIELDS = {"band": _field_band, "bloom": _field_bloom, "wash": _field_wash}


# ------------------------------------------------------------------- cor


# Os três polos são as três camadas de corante do filme. A cor de um vazamento é
# literalmente quais camadas a luz sensibilizou, então amarelo/ciano/magenta é a
# parametrização natural — mais fiel que uma escala quente↔fria.
#
# Cada polo tem ganho e expoente por canal. O expoente é o que faz a rampa: o
# canal fraco recebe expoente alto, some na franja e só volta no núcleo quente,
# que por isso satura em branco. p perto de 1 nos canais fortes é deliberado —
# abaixo disso o canal decai devagar demais e transborda para fora da banda.
# Branco é o quarto polo: ganho e expoente neutros, isto é, só luminosidade — a
# luz sensibilizou as três camadas por igual e não sobra dominante nenhuma.
DYES = ("amarelo", "ciano", "magenta", "branco")

_DYE_GAIN = {
    "amarelo": np.array([1.00, 0.86, 0.10], dtype=np.float32),
    "ciano":   np.array([0.14, 0.82, 1.00], dtype=np.float32),
    "magenta": np.array([1.00, 0.12, 0.78], dtype=np.float32),
    "branco":  np.array([1.00, 1.00, 1.00], dtype=np.float32),
}
_DYE_EXP = {
    "amarelo": np.array([0.95, 1.15, 3.60], dtype=np.float32),
    "ciano":   np.array([3.50, 1.25, 0.95], dtype=np.float32),
    "magenta": np.array([0.95, 3.60, 1.30], dtype=np.float32),
    "branco":  np.array([1.00, 1.00, 1.00], dtype=np.float32),
}

# As sete combinações não-vazias dos três corantes, mais o branco puro.
PALETTES: dict[str, tuple[str, ...]] = {
    "branco": ("branco",),
    "amarelo": ("amarelo",),
    "ciano": ("ciano",),
    "magenta": ("magenta",),
    "amarelo-ciano": ("amarelo", "ciano"),
    "amarelo-magenta": ("amarelo", "magenta"),
    "ciano-magenta": ("ciano", "magenta"),
    "tricromia": ("amarelo", "ciano", "magenta"),
}
_CYCLE = tuple(PALETTES)


def resolve_palette(name: str, seed: int) -> str:
    """'auto'/'permutar' percorre as oito combinações em ordem pela semente, de
    modo que apertar Generate repetidamente passa por todas sem sortear repetido."""
    if name in ("auto", "permutar"):
        return _CYCLE[seed % len(_CYCLE)]
    return name


def draw_dye(rng: np.random.Generator, palette: str, mix: float = 0.45) -> tuple:
    """Pesos de corante para uma fonte, dentro da paleta escolhida."""
    poles = PALETTES[palette]
    idx = [DYES.index(d) for d in poles]
    w = np.zeros(len(DYES), dtype=np.float32)
    if len(idx) > 1 and rng.random() < mix:
        w[idx] = rng.dirichlet(np.full(len(idx), 1.1)).astype(np.float32)
    else:
        w[int(rng.choice(idx))] = 1.0

    # Corante absolutamente puro não existe no filme: as outras camadas sempre
    # respondem um pouco. Sem essa contaminação o resultado vira chapa de cor.
    # O branco é a exceção — contaminar seria justamente introduzir a dominante
    # que ele não deve ter.
    if poles != ("branco",):
        w[:3] = 0.94 * w[:3] + 0.06 * rng.random(3).astype(np.float32)
    return tuple(float(x) for x in w / w.sum())


def dye_response(dye, chroma: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
    w = np.asarray(dye, dtype=np.float32)
    w = w / max(float(w.sum()), 1e-6)
    g = sum(w[i] * _DYE_GAIN[d] for i, d in enumerate(DYES))
    p = sum(w[i] * _DYE_EXP[d] for i, d in enumerate(DYES))
    # chroma=0 devolve um vazamento branco neutro; 1 é o corante cheio.
    c = float(np.clip(chroma, 0.0, 2.0))
    g = 1.0 + (g - 1.0) * c
    p = 1.0 + (p - 1.0) * c
    return np.clip(g, 0.02, None).astype(np.float32), np.clip(p, 0.3, 9.0).astype(np.float32)


def _colorize(f: np.ndarray, src: dict) -> np.ndarray:
    g, p = dye_response(src["dye"], src.get("chroma", 1.0))
    fc = np.clip(f, 0.0, 1.0)[..., None]
    return (src["amp"] * g * np.power(fc, p)).astype(np.float32)


# ------------------------------------------------------------- sorteio livre


def _band_source(rng, p: LeakParams, side: str, lvl: float, palette: str) -> dict:
    """Banda ancorada numa lateral: de longe o caso mais comum nas referências."""
    # Parametrizada pelo *alcance da frente* — onde a luz para dentro do quadro —
    # e não pela meia-largura: a outra ponta fica fora do enquadramento, então a
    # meia-largura sozinha não diz quanto do quadro o vazamento come.
    reach = float(rng.uniform(0.10, 0.42) * p.spread)
    back = float(rng.uniform(-0.30, -0.10))
    center, hw = (back + reach) / 2, (reach - back) / 2
    if side == "right":
        center = 1.0 - center

    # Frente queimada ou difusa — raramente algo entre as duas nas referências.
    # A amplitude tem de acompanhar: uma frente dura em amp 16 é um platô limpo
    # com franja de fogo; a mesma amplitude numa frente difusa lava o quadro todo.
    hard = rng.random() < 0.45
    soft = (0.004, 0.02) if hard else (0.05, 0.20)
    amp = (6.0, 16.0) if hard else (0.4, 1.1)
    return {
        "kind": "band",
        "angle": float(rng.normal(0.0, 0.09)),
        "center": center,
        "halfwidth": hw,
        "soft_l": float(rng.uniform(*soft) * p.softness),
        "soft_r": float(rng.uniform(*soft) * p.softness),
        "k_l": float(rng.uniform(0.7, 1.6)),
        "k_r": float(rng.uniform(0.7, 1.6)),
        "ragged": float(rng.uniform(0.01, 0.07) * p.texture),
        "rag_freq": float(rng.uniform(3.0, 11.0)),
        "striations": float(rng.uniform(0.1, 0.6) * p.texture),
        "stri_freq": float(rng.uniform(12.0, 40.0)),
        "amp": float(rng.uniform(*amp) * p.intensity * lvl),
        "dye": draw_dye(rng, palette),
        "chroma": float(p.chroma),
        "noise_seed": int(rng.integers(0, 2**31 - 1)),
    }


def roll_recipe(params: LeakParams) -> Recipe:
    """Sorteia uma receita nova. Mesma semente + mesmos params = mesmo resultado."""
    rng = np.random.default_rng(params.seed)
    palette = resolve_palette(params.palette, params.seed)
    side = "left" if rng.random() < 0.5 else "right"
    sources = [_band_source(rng, params, side, 1.0, palette)]

    for _ in range(int(np.clip(round(params.complexity * rng.uniform(0.0, 2.2)), 0, 3))):
        lvl = float(rng.uniform(0.15, 0.45))
        dye = draw_dye(rng, palette)
        seed = int(rng.integers(0, 2**31 - 1))
        r = rng.random()
        if r < 0.45:
            other = side if rng.random() < 0.6 else ("right" if side == "left" else "left")
            sources.append(_band_source(rng, params, other, lvl, palette))
        elif r < 0.75:
            sources.append({
                "kind": "wash",
                "angle": float(rng.uniform(0, 2 * np.pi)),
                "reach": float(rng.uniform(0.4, 1.2) * params.spread),
                "amp": float(rng.uniform(0.05, 0.20) * params.intensity),
                "dye": dye, "chroma": float(params.chroma), "noise_seed": seed,
            })
        else:
            sources.append({
                "kind": "bloom",
                "cx": float(0.0 if side == "left" else 1.0) + float(rng.normal(0, 0.12)),
                "cy": float(rng.random()),
                "ra": float(rng.uniform(0.15, 0.6) * params.spread),
                "rb": float(rng.uniform(0.20, 0.9) * params.spread),
                "theta": float(rng.uniform(0, np.pi)),
                "k": float(rng.uniform(1.0, 2.2)),
                "lobes": float(rng.uniform(1.5, 4.0)),
                "wobble": float(rng.uniform(0.2, 0.7) * params.texture),
                "amp": float(rng.uniform(0.3, 0.9) * params.intensity),
                "dye": dye, "chroma": float(params.chroma), "noise_seed": seed,
            })
    return Recipe(seed=params.seed, preset="random", palette=palette, sources=sources)


# ---------------------------------------------------------------- renderização


def render_leak(recipe: Recipe, params: LeakParams, size: tuple[int, int]) -> np.ndarray:
    """Mapa RGB do vazamento em luz linear, no tamanho (largura, altura) pedido."""
    w, h = size
    pw, ph = _proc_size(w, h)
    X, Y, aspect = _coords(pw, ph)

    leak = np.zeros((ph, pw, 3), dtype=np.float32)
    peak = np.zeros((ph, pw), dtype=np.float32)
    for src in recipe.sources:
        f = _FIELDS[src["kind"]](src, X, Y, aspect)
        leak += _colorize(f, src)
        peak = np.maximum(peak, f)

    # Flare interno: parte da luz é espalhada pelo vidro e vela o quadro inteiro.
    if params.veil > 0:
        # O flare interno é a mesma luz espalhada pelo vidro: herda o corante
        # médio das fontes em vez de ter um tom próprio.
        mean_dye = np.mean([np.asarray(s["dye"], dtype=np.float32) for s in recipe.sources], axis=0)
        leak += _colorize(
            _blur(peak, 8),
            {"dye": mean_dye, "chroma": params.chroma,
             "amp": params.veil * 0.06 * params.intensity},
        )

    if w != pw or h != ph:
        leak = np.dstack([resize_field(leak[..., c], (w, h)) for c in range(3)])

    # Grão: o vazamento é revelado no mesmo filme, logo carrega o mesmo granulado.
    if params.grain > 0:
        g = noise.grain(np.random.default_rng(params.seed ^ 0x5EED), (h, w), sigma=1.0)
        leak *= 1.0 + params.grain * 0.14 * g[..., None]

    return np.clip(leak, 0.0, None)


def apply(image_srgb: np.ndarray, params: LeakParams, recipe: Recipe | None = None) -> np.ndarray:
    """Aplica o vazamento a uma imagem sRGB float [0,1] e devolve sRGB float."""
    if recipe is None:
        recipe = roll_recipe(params)
    h, w = image_srgb.shape[:2]
    out = screen_add(srgb_to_linear(image_srgb), render_leak(recipe, params, (w, h)))
    return np.clip(linear_to_srgb(out), 0.0, 1.0)
