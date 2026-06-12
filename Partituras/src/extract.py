"""Extração geométrica de notas de um PDF de partitura (MuseScore / SMuFL).

Em vez de OCR, lê diretamente o vetor do PDF:
  - as linhas do pentagrama (traços horizontais largos) dão a referência de altura;
  - as cabeças de nota são glyphs SMuFL (U+E0A2/3/4) com posição (x, y) exata;
  - a altura (pitch) de cada nota é a sua posição vertical contada em degraus
    diatônicos a partir da linha do Fá (clave de fá);
  - a armadura de clave e os acidentes ocasionais (♯ ♭ ♮) são lidos pelos seus
    glyphs e aplicados com a regra musical (o acidente vale do ponto em que
    aparece até a próxima barra de compasso, no mesmo grau da pauta).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import pymupdf

# Glyphs SMuFL relevantes
NOTEHEADS = {chr(0xE0A2), chr(0xE0A3), chr(0xE0A4)}  # whole, half, black
SHARP, FLAT, NATURAL = chr(0xE262), chr(0xE260), chr(0xE261)
DSHARP, DFLAT = chr(0xE263), chr(0xE264)
ACCIDENTALS = {SHARP, FLAT, NATURAL, DSHARP, DFLAT}
_ACC_DELTA = {SHARP: 1, FLAT: -1, NATURAL: 0, DSHARP: 2, DFLAT: -2}

_DIATONIC = ["C", "D", "E", "F", "G", "A", "B"]
_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
_SHARP_ORDER = ["F", "C", "G", "D", "A", "E", "B"]
_FLAT_ORDER = ["B", "E", "A", "D", "G", "C", "F"]
_ACC_SYMBOL = {1: "#", -1: "b", 0: "", 2: "x", -2: "bb"}


@dataclass
class Note:
    x: float
    y: float
    name: str         # ex.: "F#3", "Bb3", "C4"
    midi: int
    system: int
    accidental: int   # -2..+2 efetivo aplicado (após armadura/ocasional)
    tie_cont: bool = False  # continuação de ligadura: não recebe número


@dataclass
class System:
    lines: list[float]
    f_line: float
    step: float
    top: float
    bottom: float


@dataclass
class _Glyph:
    x: float
    y: float
    ch: str


def _glyphs(page: pymupdf.Page, wanted: set[str]) -> list[_Glyph]:
    """Posição de cada glyph SMuFL.

    IMPORTANTE: o `bbox` vertical reportado é a caixa do *em* da fonte (altura
    fixa), não a tinta do símbolo — usá-lo desloca a leitura de altura em ~2
    degraus. O `origin` (linha de base) cai no centro vertical correto do
    notehead/acidente. Por isso: X = centro do bbox (horizontalmente justo),
    Y = origin[1].
    """
    out = []
    for blk in page.get_text("rawdict")["blocks"]:
        if blk.get("type", 0) != 0:
            continue
        for ln in blk["lines"]:
            for sp in ln["spans"]:
                # Sem filtro por nome de fonte: os codepoints SMuFL ficam na
                # área de uso privado e só existem em fontes musicais
                # (MScore, Leland, Bravura, ...).
                for ch in sp["chars"]:
                    if ch["c"] in wanted:
                        x0, _, x1, _ = ch["bbox"]
                        out.append(_Glyph((x0 + x1) / 2, ch["origin"][1], ch["c"]))
    return out


def _staff_lines(page: pymupdf.Page) -> list[float]:
    ybins: dict[float, float] = defaultdict(float)
    page_w = page.rect.width
    for dr in page.get_drawings():
        for it in dr["items"]:
            if it[0] != "l":
                continue
            p1, p2 = it[1], it[2]
            w = abs(p2.x - p1.x)
            if abs(p1.y - p2.y) < 0.6 and 20 < w < page_w - 5:
                ybins[round((p1.y + p2.y) / 2, 1)] += w
    merged: list[list[float]] = []
    for y, w in sorted(ybins.items()):
        if merged and abs(y - merged[-1][0]) < 2:
            Y, W = merged[-1]
            merged[-1] = [(Y * W + y * w) / (W + w), W + w]
        else:
            merged.append([y, w])
    return sorted(y for y, w in merged if w > 400)


def detect_systems(page: pymupdf.Page) -> list[System]:
    strong = _staff_lines(page)
    groups: list[list[float]] = []
    cur = [strong[0]]
    for y in strong[1:]:
        if y - cur[-1] < 9:
            cur.append(y)
        else:
            groups.append(cur)
            cur = [y]
    groups.append(cur)

    def best_five(g: list[float]) -> list[float] | None:
        """5 linhas consecutivas com espaçamento mais uniforme (descarta
        linhas espúrias coladas à pauta, ex. ligaduras/voltas longas)."""
        if len(g) < 5:
            return None
        best, best_var = None, None
        for i in range(len(g) - 4):
            win = g[i:i + 5]
            sp = [win[j + 1] - win[j] for j in range(4)]
            m = sum(sp) / 4
            var = sum((x - m) ** 2 for x in sp)
            if best_var is None or var < best_var:
                best, best_var = win, var
        return best

    systems = []
    for g in groups:
        g5 = best_five(g)
        if g5 is None:
            continue
        step = (g5[1] - g5[0]) / 2
        systems.append(System(lines=g5, f_line=g5[1], step=step,
                              top=g5[0], bottom=g5[4]))
    return systems


def _barlines(page: pymupdf.Page, systems: list[System]) -> dict[int, list[float]]:
    """X das barras de compasso por sistema: verticais que vão da linha de cima
    à de baixo da pauta (distingue de hastes de nota)."""
    out: dict[int, list[float]] = {i: [] for i in range(len(systems))}
    for dr in page.get_drawings():
        for it in dr["items"]:
            if it[0] != "l":
                continue
            p1, p2 = it[1], it[2]
            if abs(p1.x - p2.x) >= 0.6:
                continue
            ytop, ybot = min(p1.y, p2.y), max(p1.y, p2.y)
            for i, s in enumerate(systems):
                if abs(ytop - s.top) < 2.5 and abs(ybot - s.bottom) < 2.5:
                    out[i].append(round((p1.x + p2.x) / 2, 1))
    for i in out:
        xs = sorted(out[i])
        dedup: list[float] = []
        for x in xs:
            if not dedup or x - dedup[-1] > 3:
                dedup.append(x)
        out[i] = dedup
    return out


def _detect_key(page: pymupdf.Page, systems: list[System]) -> tuple[int, int]:
    """(n_sustenidos, n_bemois) na armadura — contados à esquerda do 1º sistema."""
    if not systems:
        return 0, 0
    s0 = systems[0]
    sharps = [g for g in _glyphs(page, {SHARP}) if abs(g.y - s0.f_line) < 45]
    flats = [g for g in _glyphs(page, {FLAT}) if abs(g.y - s0.f_line) < 45]
    if not sharps and not flats:
        return 0, 0
    allx = [g.x for g in sharps + flats]
    left = min(allx)
    ns = sum(1 for g in sharps if g.x < left + 60)
    nf = sum(1 for g in flats if g.x < left + 60)
    # armadura é só de um tipo; mantém o predominante
    return (min(ns, 7), 0) if ns >= nf else (0, min(nf, 7))


def _tie_curves(page: pymupdf.Page) -> list[tuple[float, float, float, float]]:
    """Extremos (lx, ly, rx, ry) de cada curva desenhada (ligaduras/slurs)."""
    out = []
    for dr in page.get_drawings():
        pts = []
        has_curve = False
        for it in dr["items"]:
            if it[0] == "c":
                has_curve = True
                pts += [it[1], it[4]]   # pontos sobre a curva (extremos do segmento)
            elif it[0] == "l":
                pts += [it[1], it[2]]
        if not has_curve or not pts:
            continue
        lx = min(p.x for p in pts)
        rx = max(p.x for p in pts)
        ly = [p.y for p in pts if abs(p.x - lx) < 1.0]
        ry = [p.y for p in pts if abs(p.x - rx) < 1.0]
        out.append((lx, sum(ly) / len(ly), rx, sum(ry) / len(ry)))
    return out


def _mark_ties(notes: list[Note], systems: list[System],
               curves: list[tuple[float, float, float, float]]) -> None:
    """Marca como tie_cont as notas que continuam uma ligadura de
    prolongamento (mesma altura), inclusive através da quebra de linha."""
    by_sys: dict[int, list[Note]] = {}
    for n in notes:
        by_sys.setdefault(n.system, []).append(n)
    for si in by_sys:
        by_sys[si].sort(key=lambda n: n.x)

    def steps_of(n: Note) -> int:
        return _steps_from_y(n.y, systems[n.system])

    # 1) ligaduras dentro do sistema: curva ancorada em duas notas adjacentes
    #    da MESMA altura -> a segunda é continuação.
    for si, sysnotes in by_sys.items():
        st = systems[si].step
        for a, b in zip(sysnotes, sysnotes[1:]):
            if steps_of(a) != steps_of(b):
                continue
            gap = b.x - a.x
            if gap <= 0:
                continue
            for lx, ly, rx, ry in curves:
                if (a.x - st <= lx <= a.x + 0.6 * gap
                        and b.x - 0.6 * gap <= rx <= b.x + st
                        and abs(ly - a.y) <= 2.8 * st
                        and abs(ry - b.y) <= 2.8 * st):
                    b.tie_cont = True
                    break

    # 2) ligadura atravessando a quebra de linha: toco de curva "pendurado"
    #    terminando na 1ª nota do sistema, vindo do nada à esquerda, com a
    #    última nota do sistema anterior na mesma altura.
    for si in sorted(by_sys):
        if si == 0 or not by_sys[si] or not by_sys.get(si - 1):
            continue
        first = by_sys[si][0]
        prev_last = by_sys[si - 1][-1]
        if steps_of(first) != steps_of(prev_last):
            continue
        st = systems[si].step
        for lx, ly, rx, ry in curves:
            if (first.x - 4 * st <= rx <= first.x + st
                    and abs(ry - first.y) <= 2.8 * st
                    and lx < first.x - 1.5 * st):
                first.tie_cont = True
                break


def _steps_from_y(y: float, sysm: System) -> int:
    return round((sysm.f_line - y) / sysm.step)


def _letter_octave(steps: int) -> tuple[str, int]:
    idx = _DIATONIC.index("F") + 7 * 3 + steps   # Fá3 como âncora
    return _DIATONIC[idx % 7], idx // 7


def extract_notes(page: pymupdf.Page) -> tuple[list[Note], list[System]]:
    systems = detect_systems(page)
    if not systems:
        return [], systems
    bars = _barlines(page, systems)
    n_sharp, n_flat = _detect_key(page, systems)
    keysig: dict[str, int] = {}
    for ltr in _SHARP_ORDER[:n_sharp]:
        keysig[ltr] = 1
    for ltr in _FLAT_ORDER[:n_flat]:
        keysig[ltr] = -1

    # cabeças de nota e acidentes, por sistema
    def assign_system(g: _Glyph) -> int:
        return min(range(len(systems)), key=lambda i: abs(g.y - systems[i].f_line))

    heads_by_sys: dict[int, list[_Glyph]] = defaultdict(list)
    for g in _glyphs(page, NOTEHEADS):
        heads_by_sys[assign_system(g)].append(g)
    accs_by_sys: dict[int, list[_Glyph]] = defaultdict(list)
    for g in _glyphs(page, ACCIDENTALS):
        accs_by_sys[assign_system(g)].append(g)

    notes: list[Note] = []
    for si, sysm in enumerate(systems):
        heads = sorted(heads_by_sys[si], key=lambda g: g.x)
        accs = sorted(accs_by_sys[si], key=lambda g: g.x)
        sysbars = bars[si]

        # 1) ligar cada acidente ocasional à nota imediatamente à direita,
        #    mesmo grau de pauta, dentro de um pequeno intervalo horizontal.
        explicit: dict[int, int] = {}  # id(head) -> delta
        for a in accs:
            astep = _steps_from_y(a.y, sysm)
            best = None
            for h in heads:
                if h.x <= a.x:
                    continue
                if h.x - a.x > 16:
                    break
                if _steps_from_y(h.y, sysm) == astep:
                    best = h
                    break
            if best is not None:
                explicit[id(best)] = _ACC_DELTA[a.ch]

        # 2) propagar pela regra do compasso: acidente vale até a próxima barra.
        def measure_of(x: float) -> int:
            return sum(1 for bx in sysbars if bx < x)

        active: dict[tuple[int, int], int] = {}  # (compasso, grau) -> delta
        for h in heads:
            steps = _steps_from_y(h.y, sysm)
            # sanidade: além de ~2 oitavas da linha do Fá não é nota real
            # desta pauta (glyph mal-atribuído) — ignora.
            if not -12 <= steps <= 15:
                continue
            letter, octave = _letter_octave(steps)
            m = measure_of(h.x)
            key = (m, steps)
            if id(h) in explicit:
                delta = explicit[id(h)]
                active[key] = delta
            elif key in active:
                delta = active[key]
            else:
                delta = keysig.get(letter, 0)
            midi = _SEMITONE[letter] + delta + (octave + 1) * 12
            name = f"{letter}{_ACC_SYMBOL.get(delta, '')}{octave}"
            notes.append(Note(x=h.x, y=h.y, name=name, midi=midi,
                              system=si, accidental=delta))

    notes.sort(key=lambda n: (n.system, n.x))
    _mark_ties(notes, systems, _tie_curves(page))
    return notes, systems
