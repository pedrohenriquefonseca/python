"""Vinte presets extraídos de fotografias reais com vazamento.

Cada preset descreve a *estrutura* observada numa referência — geometria, dureza
das frentes, faixa de amplitude e tom — não valores congelados. Todo campo pode
ser um escalar ou um par `(mín, máx)` sorteado a cada 'Generate', então o preset
mantém o caráter da referência e nunca repete o mesmo quadro.

Leitura das referências, resumida:

* A banda vertical de altura inteira domina — 15 das 20. Diagonal é exceção.
* A frente é dura e rasgada (`soft` ~0,01 e `ragged` alto) num grupo, e difusa
  (`soft` ~0,15) noutro. Raramente é intermediária, por isso o sorteio livre
  escolhe entre os dois regimes em vez de interpolar.
* `amp` é o valor do platô em luz linear, onde branco = 1,0 — e é ele que decide
  a cor, sozinho. ~0,3 dá um véu quente; ~1 a 3 dá coluna âmbar com detalhe;
  acima de ~8 o platô estoura para creme chapado e sobra só a franja de fogo na
  fronteira. Não existe parâmetro de "cor do núcleo": ele cai do modelo espectral.
* `amp` e a dureza da frente andam juntas. Uma frente dura em amp 16 é um platô
  limpo; a mesma amplitude numa frente difusa lava o quadro inteiro. Por isso as
  faixas de amp abaixo variam quase uma ordem de grandeza entre os dois regimes.
* A banda fria (ciano/verde) aparece ao lado da quente em três referências. É
  luz que atinge a emulsão pela frente, não pela base.
"""
from __future__ import annotations

import numpy as np

from .lightleak import LeakParams, Recipe, draw_dye, resolve_palette

# Campos que cada primitiva assume quando o preset não diz nada.
_DEFAULTS = {
    "band": {
        "angle": 0.0, "center": 0.0, "halfwidth": 0.15,
        "soft_l": 0.06, "soft_r": 0.06, "k_l": 1.0, "k_r": 1.0,
        "ragged": 0.02, "rag_freq": 6.0,
        "striations": 0.25, "stri_freq": 24.0,
        "amp": 6.0, "dye": (0.64, 0.13, 0.23, 0.00),
    },
    "bloom": {
        "cx": 0.0, "cy": 0.5, "ra": 0.35, "rb": 0.6, "theta": 0.0,
        "k": 1.4, "lobes": 2.5, "wobble": 0.4,
        "amp": 4.0, "dye": (0.64, 0.13, 0.23, 0.00),
    },
    "wash": {
        "angle": 0.0, "reach": 0.8,
        "amp": 0.5, "dye": (0.64, 0.13, 0.23, 0.00),
    },
}

# Quais chaves cada slider escala.
_BY_INTENSITY = ("amp",)
_BY_SPREAD = ("halfwidth", "ra", "rb", "reach")
_BY_SOFTNESS = ("soft_l", "soft_r")
_BY_TEXTURE = ("ragged", "striations", "wobble")

_PI2 = float(np.pi / 2)


PRESETS: dict[str, dict] = {
    # 1 — noite, mastros: barra amarela estreita e incandescente + dominante magenta.
    "noturno-cruz": {
        "label": "Noturno cruz",
        "note": "Barra amarela estreita e incandescente sobre cena noturna magenta.",
        "params": {"veil": 0.12, "grain": 0.7},
        "sources": [
            {"kind": "band", "center": (0.03, 0.10), "halfwidth": (0.035, 0.06),
             "soft_l": 0.010, "soft_r": (0.010, 0.022), "k_l": 0.8, "k_r": 0.9,
             "ragged": (0.015, 0.035), "rag_freq": (5, 9), "striations": (0.15, 0.30),
             "amp": (12, 18), "dye": (0.74, 0.00, 0.26, 0.00)},
            {"kind": "wash", "angle": (2.6, 3.6), "reach": (0.9, 1.4),
             "amp": (0.10, 0.22), "dye": (0.30, 0.13, 0.57, 0.00)},
        ],
    },
    # 2 — árvores, céu teal: 40% do quadro em creme chapado, fronteira rasgada.
    "borda-rasgada": {
        "label": "Borda rasgada",
        "note": "Terço esquerdo estourado em creme, fronteira rasgada vermelha.",
        "params": {"veil": 0.06, "grain": 0.85},
        "sources": [
            {"kind": "band", "center": (-0.10, -0.02), "halfwidth": (0.34, 0.44),
             "soft_l": 0.02, "soft_r": (0.010, 0.020), "k_l": 1.0, "k_r": (0.8, 1.0),
             "ragged": (0.035, 0.060), "rag_freq": (6, 10),
             "striations": (0.18, 0.35), "stri_freq": (14, 26),
             "amp": (9, 14), "dye": (0.69, 0.07, 0.25, 0.00)},
        ],
    },
    # 3 — mãos: feixes diagonais sobrepostos, laranja sobre vermelho sobre amarelo.
    "arco-diagonal": {
        "label": "Arco diagonal",
        "note": "Feixes diagonais sobrepostos em laranja, vermelho e amarelo.",
        "params": {"veil": 0.18, "grain": 0.4},
        "sources": [
            {"kind": "band", "angle": (-0.62, -0.42), "center": (0.02, 0.10),
             "halfwidth": (0.05, 0.09), "soft_l": (0.05, 0.10), "soft_r": (0.06, 0.12),
             "ragged": (0.01, 0.03), "striations": (0.2, 0.4),
             "amp": (1.2, 2.2), "dye": (0.74, 0.00, 0.26, 0.00)},
            {"kind": "band", "angle": (-0.60, -0.40), "center": (0.13, 0.22),
             "halfwidth": (0.03, 0.07), "soft_l": (0.04, 0.09), "soft_r": (0.05, 0.10),
             "amp": (0.5, 1.1), "dye": (0.70, 0.04, 0.25, 0.00)},
            {"kind": "band", "angle": (-0.58, -0.38), "center": (0.24, 0.34),
             "halfwidth": (0.02, 0.05), "soft_l": (0.05, 0.11), "soft_r": (0.05, 0.11),
             "amp": (0.3, 0.7), "dye": (0.47, 0.11, 0.42, 0.00)},
        ],
    },
    # 4 — campo e nuvens: coluna estriada à esquerda + véu vermelho no céu.
    "coluna-e-ceu": {
        "label": "Coluna e céu",
        "note": "Coluna estriada à esquerda e véu vermelho cobrindo o céu.",
        "params": {"veil": 0.15, "grain": 0.6},
        "sources": [
            {"kind": "band", "center": (-0.06, 0.04), "halfwidth": (0.18, 0.26),
             "soft_l": 0.02, "soft_r": (0.035, 0.075), "k_r": (0.9, 1.3),
             "ragged": (0.02, 0.045), "rag_freq": (4, 8),
             "striations": (0.45, 0.70), "stri_freq": (18, 34),
             "amp": (2.5, 4.5), "dye": (0.71, 0.04, 0.25, 0.00)},
            {"kind": "wash", "angle": (-1.0, -0.4), "reach": (0.7, 1.1),
             "amp": (0.12, 0.28), "dye": (0.70, 0.04, 0.25, 0.00)},
        ],
    },
    # 5 — praia, banco: quadro inteiro âmbar com uma banda fria atravessando.
    "faixa-fria": {
        "label": "Faixa fria",
        "note": "Quadro inteiro em âmbar com uma banda ciano fria atravessando.",
        "params": {"veil": 0.12, "grain": 0.55},
        "sources": [
            {"kind": "wash", "angle": (0.0, 6.28), "reach": (1.4, 2.0),
             "amp": (0.12, 0.26), "dye": (0.71, 0.04, 0.25, 0.00)},
            {"kind": "band", "center": (0.34, 0.48), "halfwidth": (0.06, 0.11),
             "soft_l": (0.06, 0.13), "soft_r": (0.06, 0.13),
             "ragged": (0.01, 0.03), "striations": (0.15, 0.3),
             "amp": (0.30, 0.60), "dye": (0.12, 0.78, 0.10, 0.00)},
        ],
    },
    # 6 — girassóis: branco absoluto até uma linha de fogo fina e serrilhada.
    "fogo-na-borda": {
        "label": "Fogo na borda",
        "note": "Branco absoluto até uma linha de fogo fina e serrilhada.",
        "params": {"veil": 0.03, "grain": 0.35},
        "sources": [
            {"kind": "band", "center": (-0.06, 0.02), "halfwidth": (0.34, 0.44),
             "soft_l": 0.02, "soft_r": (0.004, 0.009), "k_l": 1.0, "k_r": (0.7, 0.9),
             "ragged": (0.012, 0.026), "rag_freq": (12, 20),
             "striations": (0.05, 0.15),
             "amp": (16, 24), "dye": (0.72, 0.02, 0.26, 0.00)},
        ],
    },
    # 7 — estrada: cortina de colunas verticais difusas descendo do céu.
    "cortina-estrada": {
        "label": "Cortina de estrada",
        "note": "Colunas verticais difusas descendo do céu, salmão e pálidas.",
        "params": {"veil": 0.22, "grain": 0.5},
        "sources": [
            {"kind": "band", "angle": (-0.10, 0.10), "center": (0.02, 0.14),
             "halfwidth": (0.07, 0.13), "soft_l": (0.08, 0.16), "soft_r": (0.10, 0.20),
             "striations": (0.3, 0.5), "amp": (0.6, 1.1), "dye": (0.70, 0.04, 0.25, 0.00)},
            {"kind": "band", "angle": (-0.08, 0.08), "center": (0.33, 0.47),
             "halfwidth": (0.03, 0.07), "soft_l": (0.09, 0.18), "soft_r": (0.09, 0.18),
             "amp": (0.25, 0.5), "dye": (0.46, 0.14, 0.40, 0.00)},
            {"kind": "band", "angle": (-0.08, 0.08), "center": (0.55, 0.70),
             "halfwidth": (0.02, 0.06), "soft_l": (0.08, 0.16), "soft_r": (0.08, 0.16),
             "amp": (0.15, 0.35), "dye": (0.53, 0.26, 0.21, 0.00)},
        ],
    },
    # 8 — kombi: bruma dourada difusa vindo do alto, sem fronteira visível.
    "bruma-dourada": {
        "label": "Bruma dourada",
        "note": "Bruma dourada difusa vinda do alto, sem fronteira visível.",
        "params": {"veil": 0.30, "grain": 0.3},
        "sources": [
            {"kind": "bloom", "cx": (0.15, 0.45), "cy": (-0.25, -0.02),
             "ra": (0.55, 0.95), "rb": (0.45, 0.80), "k": (1.2, 1.8),
             "wobble": (0.2, 0.5), "amp": (0.35, 0.7), "dye": (0.67, 0.09, 0.24, 0.00)},
            {"kind": "wash", "angle": (-1.9, -1.2), "reach": (1.0, 1.5),
             "amp": (0.10, 0.22), "dye": (0.67, 0.09, 0.24, 0.00)},
        ],
    },
    # 9 — árvores urbanas: coluna laranja densa e muito estriada sobre cena escura.
    "coluna-laranja": {
        "label": "Coluna laranja",
        "note": "Coluna laranja densa e muito estriada sobre cena escura.",
        "params": {"veil": 0.14, "grain": 0.6},
        "sources": [
            {"kind": "band", "angle": (-0.06, 0.06), "center": (0.22, 0.38),
             "halfwidth": (0.10, 0.17), "soft_l": (0.03, 0.07), "soft_r": (0.05, 0.11),
             "ragged": (0.015, 0.035), "rag_freq": (5, 9),
             "striations": (0.50, 0.75), "stri_freq": (22, 40),
             "amp": (1.8, 3.0), "dye": (0.72, 0.03, 0.25, 0.00)},
        ],
    },
    # 10 — rua, chapéu: inundação laranja saturada em diagonal, céu intacto.
    "inundacao-diagonal": {
        "label": "Inundação diagonal",
        "note": "Inundação laranja saturada em diagonal, com o céu preservado.",
        "params": {"veil": 0.12, "grain": 0.5},
        "sources": [
            {"kind": "band", "angle": (0.75, 1.05), "center": (0.60, 0.78),
             "halfwidth": (0.30, 0.42), "soft_l": (0.08, 0.16), "soft_r": 0.03,
             "ragged": (0.02, 0.05), "rag_freq": (3, 6),
             "striations": (0.1, 0.25),
             "amp": (0.7, 1.2), "dye": (0.74, 0.00, 0.26, 0.00)},
        ],
    },
    # 11 — três pessoas no campo: âmbar total, contraste derrubado, núcleo no alto.
    "ambar-total": {
        "label": "Âmbar total",
        "note": "Âmbar cobrindo tudo, contraste derrubado, núcleo claro no alto.",
        "params": {"veil": 0.20, "grain": 0.4},
        "sources": [
            {"kind": "wash", "angle": (-1.8, -1.35), "reach": (1.6, 2.2),
             "amp": (0.15, 0.30), "dye": (0.69, 0.06, 0.25, 0.00)},
            {"kind": "bloom", "cx": (0.35, 0.65), "cy": (-0.15, 0.10),
             "ra": (0.6, 1.0), "rb": (0.4, 0.7), "k": (1.3, 1.9),
             "wobble": (0.2, 0.45), "amp": (0.35, 0.7), "dye": (0.67, 0.09, 0.24, 0.00)},
        ],
    },
    # 12 — floresta: lateral direita queimada com franja vermelha e estrias.
    "lateral-queimada": {
        "label": "Lateral queimada",
        "note": "Lateral direita queimada, franja vermelha e estrias verticais.",
        "params": {"veil": 0.10, "grain": 0.5},
        "sources": [
            {"kind": "band", "center": (1.00, 1.10), "halfwidth": (0.24, 0.34),
             "soft_l": (0.012, 0.030), "soft_r": 0.02, "k_l": (0.8, 1.1),
             "ragged": (0.025, 0.055), "rag_freq": (7, 12),
             "striations": (0.35, 0.60), "stri_freq": (20, 38),
             "amp": (10, 16), "dye": (0.70, 0.04, 0.25, 0.00)},
        ],
    },
    # 13 — fotógrafo em silhueta: vermelho puro e saturado, fronteira horizontal.
    #      A amplitude fica baixa de propósito: acima de ~6 o vermelho vira branco.
    "vermelho-solido": {
        "label": "Vermelho sólido",
        "note": "Vermelho puro e saturado com fronteira horizontal e núcleo amarelo.",
        "params": {"veil": 0.16, "grain": 0.45},
        "sources": [
            {"kind": "band", "angle": _PI2, "center": (0.58, 0.74),
             "halfwidth": (0.34, 0.46), "soft_l": (0.06, 0.14), "soft_r": 0.05,
             "ragged": (0.02, 0.05), "rag_freq": (3, 7),
             "striations": (0.1, 0.25),
             "amp": (0.7, 1.2), "dye": (0.74, 0.00, 0.26, 0.00)},
            {"kind": "bloom", "cx": (0.35, 0.55), "cy": (0.40, 0.55),
             "ra": (0.10, 0.20), "rb": (0.08, 0.16), "k": (1.2, 1.8),
             "wobble": (0.3, 0.6), "amp": (5, 9), "dye": (0.74, 0.00, 0.26, 0.00)},
        ],
    },
    # 14 — casa entre árvores: três colunas paralelas difusas, laranja quente.
    "cortina-tripla": {
        "label": "Cortina tripla",
        "note": "Três colunas paralelas difusas em laranja quente.",
        "params": {"veil": 0.20, "grain": 0.5},
        "sources": [
            {"kind": "band", "angle": (-0.05, 0.05), "center": (0.30, 0.40),
             "halfwidth": (0.04, 0.075), "soft_l": (0.04, 0.09), "soft_r": (0.04, 0.09),
             "striations": (0.3, 0.55), "amp": (1.0, 1.8), "dye": (0.72, 0.02, 0.26, 0.00)},
            {"kind": "band", "angle": (-0.05, 0.05), "center": (0.44, 0.54),
             "halfwidth": (0.03, 0.06), "soft_l": (0.05, 0.10), "soft_r": (0.05, 0.10),
             "amp": (0.5, 1.0), "dye": (0.71, 0.04, 0.25, 0.00)},
            {"kind": "band", "angle": (-0.05, 0.05), "center": (0.57, 0.68),
             "halfwidth": (0.02, 0.05), "soft_l": (0.05, 0.11), "soft_r": (0.05, 0.11),
             "amp": (0.3, 0.7), "dye": (0.70, 0.05, 0.25, 0.00)},
        ],
    },
    # 15 — homem na ponte: coluna âmbar leitosa, quadro inteiro enevoado.
    "ambar-leitoso": {
        "label": "Âmbar leitoso",
        "note": "Coluna âmbar leitosa e larga; o quadro inteiro fica enevoado.",
        "params": {"veil": 0.50, "grain": 0.3},
        "sources": [
            {"kind": "band", "angle": (-0.06, 0.06), "center": (0.38, 0.52),
             "halfwidth": (0.18, 0.28), "soft_l": (0.12, 0.22), "soft_r": (0.12, 0.22),
             "striations": (0.2, 0.4), "stri_freq": (10, 22),
             "amp": (0.9, 1.6), "dye": (0.69, 0.07, 0.25, 0.00)},
        ],
    },
    # 16 — Flatiron: bandas amarelas difusas nas duas laterais.
    "bandas-laterais": {
        "label": "Bandas laterais",
        "note": "Bandas amarelas difusas nas duas laterais, centro limpo.",
        "params": {"veil": 0.18, "grain": 0.35},
        "sources": [
            {"kind": "band", "center": (-0.04, 0.04), "halfwidth": (0.10, 0.16),
             "soft_l": 0.03, "soft_r": (0.08, 0.16),
             "striations": (0.2, 0.4), "amp": (0.9, 1.6), "dye": (0.70, 0.05, 0.25, 0.00)},
            {"kind": "band", "center": (0.96, 1.04), "halfwidth": (0.08, 0.14),
             "soft_l": (0.08, 0.16), "soft_r": 0.03,
             "striations": (0.2, 0.4), "amp": (0.9, 1.6), "dye": (0.70, 0.05, 0.25, 0.00)},
        ],
    },
    # 17 — praia, variante forte: mesma leitura da 5, com a faixa fria dominante.
    "faixa-fria-forte": {
        "label": "Faixa fria forte",
        "note": "Como a Faixa fria, porém com a banda ciano dominando o quadro.",
        "params": {"veil": 0.22, "grain": 0.6},
        "sources": [
            {"kind": "wash", "angle": (0.0, 6.28), "reach": (1.4, 2.0),
             "amp": (0.15, 0.30), "dye": (0.72, 0.02, 0.26, 0.00)},
            {"kind": "band", "center": (0.30, 0.46), "halfwidth": (0.10, 0.17),
             "soft_l": (0.05, 0.11), "soft_r": (0.05, 0.11),
             "ragged": (0.01, 0.03), "striations": (0.2, 0.4),
             "amp": (0.6, 1.0), "dye": (0.09, 0.82, 0.09, 0.00)},
        ],
    },
    # 18 — parque com cão: borda laranja de um lado, borda esverdeada do outro.
    "duas-bordas": {
        "label": "Duas bordas",
        "note": "Borda laranja de um lado, borda esverdeada do outro, centro limpo.",
        "params": {"veil": 0.14, "grain": 0.45},
        "sources": [
            {"kind": "band", "center": (-0.05, 0.03), "halfwidth": (0.10, 0.17),
             "soft_l": 0.03, "soft_r": (0.06, 0.13),
             "ragged": (0.02, 0.04), "striations": (0.25, 0.45),
             "amp": (1.2, 2.0), "dye": (0.71, 0.04, 0.25, 0.00)},
            {"kind": "band", "center": (0.97, 1.05), "halfwidth": (0.06, 0.11),
             "soft_l": (0.07, 0.14), "soft_r": 0.03,
             "striations": (0.2, 0.4),
             "amp": (0.6, 1.1), "dye": (0.60, 0.25, 0.15, 0.00)},
        ],
    },
    # 19 — crianças no jardim: borda esquerda suave, fronteira ondulada e larga.
    "borda-suave": {
        "label": "Borda suave",
        "note": "Borda esquerda avermelhada com fronteira larga e ondulada.",
        "params": {"veil": 0.35, "grain": 0.4},
        "sources": [
            {"kind": "band", "center": (-0.08, 0.02), "halfwidth": (0.14, 0.22),
             "soft_l": 0.03, "soft_r": (0.10, 0.18), "k_r": (1.0, 1.5),
             "ragged": (0.035, 0.070), "rag_freq": (3, 6),
             "striations": (0.2, 0.4),
             "amp": (0.9, 1.5), "dye": (0.71, 0.04, 0.25, 0.00)},
        ],
    },
    # 20 — árvores em contraluz: espectro vertical — quente, escuro, frio.
    "espectro-vertical": {
        "label": "Espectro vertical",
        "note": "Banda quente numa lateral, centro intacto e banda fria na outra.",
        "params": {"veil": 0.20, "grain": 0.55},
        "sources": [
            {"kind": "band", "center": (0.04, 0.14), "halfwidth": (0.08, 0.14),
             "soft_l": (0.03, 0.07), "soft_r": (0.03, 0.08),
             "ragged": (0.015, 0.035), "striations": (0.35, 0.6),
             "amp": (1.6, 2.8), "dye": (0.72, 0.02, 0.26, 0.00)},
            {"kind": "band", "center": (0.82, 0.94), "halfwidth": (0.05, 0.10),
             "soft_l": (0.03, 0.08), "soft_r": (0.03, 0.08),
             "striations": (0.2, 0.4),
             "amp": (0.5, 0.9), "dye": (0.10, 0.81, 0.09, 0.00)},
        ],
    },
}


def _sample(rng: np.random.Generator, value):
    # Só um par é intervalo. Tuplas maiores são valores literais — `dye` tem
    # quatro componentes e não deve ser sorteada componente a componente.
    if isinstance(value, tuple) and len(value) == 2:
        return float(rng.uniform(value[0], value[1]))
    return value


def preset_params(name: str, base: LeakParams | None = None) -> LeakParams:
    """Params do preset — os defaults dos sliders para aquela referência."""
    p = LeakParams(**vars(base)) if base else LeakParams()
    for k, v in PRESETS[name]["params"].items():
        setattr(p, k, v)
    return p


def preset_recipe(name: str, params: LeakParams) -> Recipe:
    """Sorteia uma variação do preset. Os sliders escalam a estrutura observada;
    a semente decide onde, dentro das faixas da referência, cada valor cai."""
    spec = PRESETS[name]
    rng = np.random.default_rng(params.seed)
    # 'auto' preserva as cores da referência; qualquer paleta explícita as
    # substitui, o que permite ver a mesma geometria em ciano, magenta ou branco.
    palette = None if params.palette == "auto" else resolve_palette(params.palette, params.seed)

    sources = []
    for raw in spec["sources"]:
        src = dict(_DEFAULTS[raw["kind"]])
        src["kind"] = raw["kind"]
        src.update({k: _sample(rng, v) for k, v in raw.items() if k != "kind"})

        for key in _BY_INTENSITY:
            if key in src:
                src[key] *= params.intensity
        for key in _BY_SPREAD:
            if key in src:
                src[key] *= params.spread
        for key in _BY_SOFTNESS:
            if key in src:
                src[key] *= params.softness
        for key in _BY_TEXTURE:
            if key in src:
                src[key] *= params.texture

        if palette:
            src["dye"] = draw_dye(rng, palette)
        else:
            # Jitter leve no corante da referência: duas fontes do mesmo preset
            # nunca saem com exatamente a mesma cor, como num rolo real.
            w = np.clip(np.asarray(src["dye"], dtype=np.float32)
                        * (1.0 + rng.normal(0, 0.10, len(src["dye"]))), 0, None)
            src["dye"] = tuple(float(x) for x in w / max(w.sum(), 1e-6))
        src["chroma"] = float(params.chroma)
        src["noise_seed"] = int(rng.integers(0, 2**31 - 1))
        sources.append(src)

    return Recipe(
        seed=params.seed, preset=name, palette=palette or "auto", sources=sources
    )
