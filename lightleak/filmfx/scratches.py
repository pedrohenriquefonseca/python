"""Dano físico de fotografia velha: vincos, dobras, rasgos e perda de emulsão.

Este efeito não desenha o dano — ele **usa o dano medido em fotografias reais**.
Vinte máscaras extraídas de fotografias estragadas de verdade, uma por filtro,
em `masks/`. Quem as produz é `tools/extract_masks.py`, e o método está
documentado lá.

A escolha é deliberada e veio de uma tentativa fracassada. A primeira versão
gerava a rede de vincos por procedimento: caminhada quase reta, ramificação em
Y, tremor acumulado. A geometria estava certa no papel e o resultado era
inconfundivelmente sintético — espessura constante demais, ângulos limpos
demais, brilho uniforme demais ao longo do traço. Vinco de verdade tem
irregularidade em toda escala ao mesmo tempo, e cada tentativa de imitar isso
com mais parâmetros só empurrava o problema para outro lugar.

O que a máscara traz de graça, e que o procedimento não dava:

* o traço engrossa e afina sem periodicidade, some por um pedaço e volta;
* os vincos se encontram em vértices com ângulos que vêm da física do papel
  amassado, não de um sorteio uniforme;
* a densidade varia pelo quadro — a foto foi apertada num lugar, não em todos;
* nas quinas o dano acumula, porque é ali que a foto bate.

Composição
----------
Este é o primeiro efeito *subtrativo* do projeto. Vazamento e halação somam
exposição; dano físico mexe em quanto da luz atravessa.

* **claro.** O vinco quebra a gelatina na linha da dobra e ela solta. Sem
  emulsão sobra o papel baritado, branco-creme e mais claro que qualquer parte
  da imagem — por isso todo vinco aparece claro. É a máscara em si.
* **escuro.** A aba de papel que a dobra levanta projeta sombra, de um lado só.
  Sai da própria máscara deslocada: onde há vinco à esquerda e não aqui, há
  sombra. Simétrico daria contorno de desenho, não dobra.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import numpy as np
from PIL import Image

from .imaging import linear_to_srgb, screen_add, srgb_to_linear

MASK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "masks")

# Cor do que aparece quando a emulsão sai: papel baritado, branco-creme. Em luz
# linear, com branco = 1.
_PAPER = np.array([1.00, 0.96, 0.87], dtype=np.float32)

# Os 20 filtros, na ordem em que foram extraídos. A nota descreve o caráter da
# fotografia de origem, que é o que o filtro carrega.
PRESETS: dict[str, str] = {
    "craquele":            "rede de craquelê cobrindo o quadro inteiro",
    "craquele-fechado":    "craquelê de células pequenas, bem fechado",
    "craquele-aberto":     "craquelê de células grandes, mais respirado",
    "trinca-unica":        "uma trinca só, atravessando",
    "riscos-finos":        "riscos finos e rasos por todo o quadro",
    "riscos-finos-canto":  "os mesmos riscos, concentrados de um lado",
    "riscos-secos":        "riscos secos e curtos, alta frequência",
    "riscos-secos-denso":  "os riscos secos onde eles se acumulam",
    "riscos-cruzados":     "riscos longos se cruzando em vários ângulos",
    "riscos-cruzados-pe":  "os cruzados na metade de baixo",
    "veio-vertical":       "veios verticais de arrasto",
    "veio-vertical-forte": "veios verticais marcados, quase escovado",
    "desgaste-pesado":     "desgaste pesado, emulsão saindo em placa",
    "grao-riscado":        "grão grosso com riscos misturados",
    "borda-escura":        "dano na moldura, centro poupado",
    "poeira":              "poeira e pontos espalhados",
    "manchas":             "manchas irregulares de sujeira",
    "sujeira-rasa":        "sujeira rasa e uniforme",
    "campo-riscado":       "campo de riscos em todas as direções",
    "campo-fino":          "riscos finíssimos cobrindo tudo",
}

DAMAGE = tuple(PRESETS)

_CACHE: dict[str, np.ndarray] = {}


@dataclass
class ScratchParams:
    """Sliders. `preset` em 'auto' deixa a semente escolher entre os 20."""

    seed: int = 0
    intensity: float = 1.0     # 0 .. 2 — opacidade do dano
    zoom: float = 1.0          # 1 .. 3 — aproxima a máscara, dano maior e mais esparso
    relief: float = 0.6        # 0 .. 1 — quanto da sombra da dobra aparece
    preset: str = "auto"


def load_mask(name: str) -> np.ndarray:
    """Máscara em [0,1]. Fica em cache: são 20 arquivos pequenos e fixos."""
    if name not in _CACHE:
        path = os.path.join(MASK_DIR, f"{name}.png")
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"máscara '{name}' não encontrada em {MASK_DIR}. "
                "Gere com: python3 tools/extract_masks.py refs -o masks "
                "--manifest refs/crops.json"
            )
        _CACHE[name] = np.asarray(Image.open(path).convert("L"), np.float32) / 255.0
    return _CACHE[name]


def resolve(p: ScratchParams) -> str:
    if p.preset in PRESETS:
        return p.preset
    return DAMAGE[p.seed % len(DAMAGE)]


def _fit(mask: np.ndarray, w: int, h: int, p: ScratchParams) -> np.ndarray:
    """Encaixa a máscara no quadro cobrindo-o, com espelho e recorte da semente.

    Cobrir e recortar, nunca esticar: esticar mudaria a proporção entre
    comprimento e espessura dos vincos, que é justamente o que faz a marca
    parecer vinco e não borrão. Espelhar não estraga nada — dano não tem
    orientação canônica — e multiplica por quatro as variações de cada máscara.
    """
    rng = np.random.default_rng(p.seed)
    mh, mw = mask.shape
    z = max(p.zoom, 1.0) * max(w / mw, h / mh)
    im = Image.fromarray(mask, mode="F").resize(
        (max(w, int(mw * z)), max(h, int(mh * z))), Image.BILINEAR
    )
    if rng.random() < 0.5:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if rng.random() < 0.5:
        im = im.transpose(Image.FLIP_TOP_BOTTOM)

    x = int(rng.integers(0, max(1, im.width - w + 1)))
    y = int(rng.integers(0, max(1, im.height - h + 1)))
    return np.asarray(im.crop((x, y, x + w, y + h)), np.float32)


def apply(image_srgb: np.ndarray, p: ScratchParams | None = None) -> np.ndarray:
    """Aplica o dano a uma imagem sRGB float [0,1] e devolve sRGB float."""
    p = p or ScratchParams()
    h, w = image_srgb.shape[:2]
    m = _fit(load_mask(resolve(p)), w, h, p)

    k = max(p.intensity, 0.0)
    lin = srgb_to_linear(image_srgb)

    # Emulsão que saiu: aparece o papel, creme e não branco puro.
    #
    # O ganho é baixo de propósito. Em 2,6 quase todo pixel da máscara saturava
    # em branco e o dano inteiro saía com o mesmo brilho — o oposto de arranhão
    # real, que tem trecho forte e trecho quase invisível. Mantendo o ganho
    # perto de 1 a variação de tom que veio da fotografia de origem sobrevive.
    lin = screen_add(lin, (m[..., None] * 1.5 * k) * _PAPER)

    # Sombra da aba levantada. Sai da máscara deslocada de poucos pixels: onde
    # havia vinco logo ao lado e não aqui, o papel está erguido e faz sombra.
    if p.relief > 0:
        d = max(1, int(0.0016 * max(w, h)))
        shade = np.clip(np.roll(np.roll(m, d, 0), d, 1) - m, 0.0, 1.0)
        lin = lin * (1.0 - np.clip(shade[..., None] * 0.55 * k * p.relief, 0.0, 0.85))

    return np.clip(linear_to_srgb(lin), 0.0, 1.0)


def roll_recipe(p: ScratchParams) -> dict[str, Any]:
    """Compatível com os outros efeitos: descreve o que a semente escolheu."""
    return {"preset": resolve(p), "zoom": round(max(p.zoom, 1.0), 3)}
