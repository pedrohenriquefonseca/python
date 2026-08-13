"""Moldura de filme: o quadro deixa de ser retângulo solto e vira janela numa tira.

Como o dano físico, e ao contrário do vazamento e da halação, este efeito **não é
modelo** — é moldura medida. A razão é a mesma nos dois casos, mas aqui ela é
ainda mais direta: a geometria do 135 é norma publicada (ISO 1007) e desenhá-la
por parâmetro dá exatamente o que se espera de um desenho — furo idêntico ao
furo vizinho, rebate de espessura constante, letreiro alinhado ao pixel. O que
denuncia moldura sintética não é a forma estar errada, é ela estar *certa demais*.

O que a máscara traz de graça:

* o rebate tem densidade desigual, porque é base de filme escaneada e não preto;
* o letreiro está gasto, cortado pela borda do quadro e às vezes ilegível;
* o furo tem canto vivido e franja de flare do scanner em volta;
* a fronteira entre imagem e rebate não é reta — a janela da câmera tem rebarba.

Composição
----------
Alfa reta, em luz linear. Moldura não soma exposição como o vazamento nem
subtrai transmissão como o dano: ela **ocupa** o pixel. Um pixel meio coberto
pela beirada da tira recebe a média das duas radiâncias, e média de radiância se
faz em linear — em sRGB a beirada sairia escura demais.

As máscaras são PNG RGBA em `borders/`, e `borders/frames.json` diz onde fica a
janela de cada uma. Quem as produz é `tools/extract_borders.py`.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image

from .imaging import linear_to_srgb, srgb_to_linear

BORDER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "borders")

_CACHE: dict[str, tuple[np.ndarray, np.ndarray]] = {}
_FRAMES: dict[str, Any] | None = None


def frames() -> dict[str, Any]:
    """Índice das máscaras: nota, tamanho e retângulos de janela."""
    global _FRAMES
    if _FRAMES is None:
        path = os.path.join(BORDER_DIR, "frames.json")
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"{path} não encontrado. Gere as máscaras com: "
                "python3 tools/extract_borders.py refs -o borders "
                "--manifest refs/borders.json"
            )
        with open(path, encoding="utf-8") as f:
            _FRAMES = json.load(f)
    return _FRAMES


def names() -> tuple[str, ...]:
    return tuple(frames())


@dataclass
class BorderParams:
    """Sliders. `preset` em 'auto' deixa a semente escolher entre as máscaras."""

    seed: int = 0
    preset: str = "auto"
    fit: str = "expandir"   # 'expandir' cresce a tela; 'caber' não passa do tamanho da entrada
    window: int = -1        # qual janela nas tiras de vários quadros; -1 = todas
    opacity: float = 1.0    # 0 .. 1 — só para prévia; 1 é a moldura cheia
    max_growth: float = 4.0  # teto de crescimento da saída, em vezes a área da entrada


def load(name: str) -> tuple[np.ndarray, np.ndarray]:
    """(RGB linear, alfa) da máscara, em cache."""
    if name not in _CACHE:
        path = os.path.join(BORDER_DIR, f"{name}.png")
        if not os.path.exists(path):
            raise FileNotFoundError(f"máscara de moldura '{name}' não encontrada em {BORDER_DIR}")
        a = np.asarray(Image.open(path).convert("RGBA"), np.float32) / 255.0
        _CACHE[name] = (srgb_to_linear(a[..., :3]), a[..., 3])
    return _CACHE[name]


def resolve(p: BorderParams) -> str:
    n = names()
    if p.preset in n:
        return p.preset
    return n[p.seed % len(n)]


def _windows(name: str, p: BorderParams) -> list[tuple[float, float, float, float]]:
    """Retângulos normalizados onde a foto entra.

    Numa tira de quatro quadros a foto vai em **todos**, não num só. Preencher um
    e deixar três buracos pretos não é tira de filme, é tira de filme com defeito
    — o olho lê os vazios como erro antes de ler a moldura. Repetido, o conjunto
    lê como prova de contato, que é o que uma tira é. `window` fixa um quadro só
    para quem quiser esse enquadramento.
    """
    wins = frames()[name]["windows"]
    if not wins:
        raise ValueError(f"máscara '{name}' não tem janela registrada")
    if 0 <= p.window < len(wins):
        return [tuple(wins[p.window])]
    return [tuple(w) for w in wins]


def _main_window(name: str, p: BorderParams) -> tuple[float, float, float, float]:
    """A janela que dá a escala da moldura: a maior."""
    return max(_windows(name, p), key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))


def _cover(img: np.ndarray, w: int, h: int) -> np.ndarray:
    """Encaixa a foto na janela cobrindo-a, cortando o excesso e centrando.

    Cobrir e cortar, nunca esticar: a janela tem a proporção do formato de filme
    e a foto tem a da câmera de quem usa. Esticar para casar as duas deformaria
    o assunto, que é o único elemento aqui que ninguém aceita ver deformado.
    """
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih)
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).resize(
        (max(w, int(round(iw * s))), max(h, int(round(ih * s)))), Image.LANCZOS)
    x = (im.width - w) // 2
    y = (im.height - h) // 2
    return np.asarray(im.crop((x, y, x + w, y + h)), np.float32) / 255.0


def apply(image_srgb: np.ndarray, p: BorderParams | None = None) -> np.ndarray:
    """Põe a foto dentro da moldura. Devolve sRGB float — e, em 'expandir', num
    tamanho diferente do da entrada: é o único efeito do projeto que faz isso."""
    p = p or BorderParams()
    name = resolve(p)
    rgb, alpha = load(name)
    mh, mw = alpha.shape
    x0, y0, x1, y1 = _main_window(name, p)

    ih, iw = image_srgb.shape[:2]
    if p.fit == "caber":
        # A moldura inteira encolhe até caber no tamanho da entrada, e a saída
        # nunca passa dele. Não é *igual* à entrada: a moldura tem a proporção do
        # formato de filme, e forçar as duas a bater esticaria uma das duas.
        scale = min(iw / mw, ih / mh)
    else:
        # A janela passa a valer o tamanho da foto, então a foto não é reduzida
        # e a tela é que cresce. Numa foto de 12 MP a moldura sai em 20 MP.
        scale = max(iw / ((x1 - x0) * mw), ih / ((y1 - y0) * mh))

        # Com teto, e ele existe por causa das tiras. Numa tira de quatro
        # quadros, dar resolução cheia a cada janela multiplica a área por seis:
        # uma foto de 16 MP saía com 198 MP e estourava o limite do decodificador
        # antes de terminar. O teto é em área e não em lado porque é a área que
        # explode — e ele não encosta em moldura de quadro único, que cresce
        # menos de duas vezes.
        grow = (mw * scale * mh * scale) / max(iw * ih, 1)
        if grow > p.max_growth > 0:
            scale *= float(np.sqrt(p.max_growth / grow))

    tw, th = max(2, round(mw * scale)), max(2, round(mh * scale))
    m = Image.fromarray((np.concatenate([rgb, alpha[..., None]], axis=2) * 255)
                        .astype(np.uint8), "RGBA").resize((tw, th), Image.LANCZOS)
    m = np.asarray(m, np.float32) / 255.0
    b_lin, b_a = m[..., :3], m[..., 3] * float(np.clip(p.opacity, 0.0, 1.0))

    # A foto entra nas janelas, em luz linear como todo o resto do projeto.
    out = np.zeros((th, tw, 3), np.float32)
    for a0, b0, a1, b1 in _windows(name, p):
        wx0, wy0 = int(round(a0 * tw)), int(round(b0 * th))
        wx1, wy1 = int(round(a1 * tw)), int(round(b1 * th))
        out[wy0:wy1, wx0:wx1] = srgb_to_linear(_cover(image_srgb, wx1 - wx0, wy1 - wy0))

    out = out * (1.0 - b_a[..., None]) + b_lin * b_a[..., None]
    return np.clip(linear_to_srgb(out), 0.0, 1.0)


def roll_recipe(p: BorderParams) -> dict[str, Any]:
    """Compatível com os outros efeitos: descreve o que a semente escolheu."""
    name = resolve(p)
    return {"preset": name, "fit": p.fit,
            "janelas": [[round(v, 4) for v in w] for w in _windows(name, p)]}
