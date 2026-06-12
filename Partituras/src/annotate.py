"""Escreve os números das posições de vara acima de cada nota e salva o PDF.

Posicionamento:
  - X: centrado na cabeça da nota (alinhamento horizontal).
  - Y: contorno relativo (grave perto da pauta, agudo mais alto) garantido por
    construção: a linha-base entre vizinhos só varia uma fração da diferença
    de altura das notas (zero quando a altura é igual), então número de nota
    mais aguda fica sempre mais alto. Obstáculos (hastes, feixes, ligaduras,
    marcas de ensaio, letras) são desviados via mapa de tinta rasterizado.
  - Tamanho: busca o MAIOR tamanho de página em que tudo cabe. Para não
    derrubar a página inteira por um gargalo local, um sistema ou um número
    específico pode ceder até 15% (regra do usuário), nunca mais que isso.
  - Verificação final: a ordem vertical de todos os pares vizinhos é checada
    contra a ordem das alturas; layout com inversão é rejeitado — nunca se
    gera PDF com contorno errado.
"""

from __future__ import annotations

import numpy as np
import pymupdf

from extract import Note, System, extract_notes
from slide_positions import position_for_midi

COLOR = (0, 0, 0)

RENDER_SCALE = 3.0   # px por pt na rasterização do mapa de tinta
INK_THRESHOLD = 170  # cinza < isto = tinta
BASE_CLEAR = 1.6     # × step: folga mínima acima da linha de cima da pauta
PITCH_SLOPE = 0.75   # × step de subida por semitom (inclinação do contorno)
BAND_MAX = 10.0      # × step: altura máx. da banda do contorno por sistema
CONTOUR_ALPHA = 0.45  # fração da diferença de altura que a base pode absorver
SAME_PITCH_STRICT_DX = 24.0  # pt: até esta distância, mesma nota = mesma altura
OBST_GAP = 1.6       # folga mínima entre o número e qualquer tinta
PAD_X = 0.3          # folga horizontal extra na caixa do número
MAX_LIFT = 60.0      # subida máxima permitida ao escapar de obstáculos
SEP_MIN = 1.5        # pt: separação vertical mínima no reparo de ordem
FONT_MAX = 18.0      # tamanho inicial da busca
FONT_MIN = 6.0       # tamanho mínimo aceitável
FONT_STEP = 0.5
CAP_RATIO = 0.72     # altura do dígito relativa ao tamanho da fonte
SHRINK_STEPS = (1.0, 0.925, 0.85)  # cedência local (sistema ou número)
SHRINK_MIN = 0.85    # piso absoluto: nenhum número fica <85% da fonte da página


_HELV = pymupdf.Font("helv")


def _digit_span(text: str, fs: float, cx: float) -> tuple[float, float, float]:
    """(x_tinta_esq, x_tinta_dir, x_caneta) do dígito centrado em cx.

    Usa o bbox de tinta real do glyph (o '1' é bem mais estreito que o
    avanço da fonte), permitindo números maiores em trechos densos.
    """
    g = ord(text)
    adv = _HELV.glyph_advance(g) * fs
    bb = _HELV.glyph_bbox(g)
    pen = cx - adv / 2
    return pen + bb.x0 * fs, pen + bb.x1 * fs, pen


def _build_ink(page: pymupdf.Page) -> np.ndarray:
    pix = page.get_pixmap(matrix=pymupdf.Matrix(RENDER_SCALE, RENDER_SCALE),
                          colorspace=pymupdf.csGRAY)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width)
    return arr < INK_THRESHOLD


def _try_layout(notes: list[Note], systems: list[System], ink: np.ndarray,
                fontsize: float,
                debug: bool = False) -> list[tuple[float, float, str, float]] | None:
    """Posiciona todos os números com esta fonte de página; None se não couber."""

    def whynot(msg: str) -> None:
        if debug:
            print(f"    [{fontsize}pt] {msg}")

    s = RENDER_SCALE
    h_px, w_px = ink.shape
    floor = SHRINK_MIN * fontsize - 1e-9

    def boxr(baseline: float, x0: int, x1: int, cap: float) -> tuple[int, int]:
        yt = max(0, int((baseline - cap - OBST_GAP) * s))
        yb = min(h_px, int((baseline + OBST_GAP * 0.5) * s) + 1)
        return yt, yb

    by_sys: dict[int, list[Note]] = {}
    for n in notes:
        by_sys.setdefault(n.system, []).append(n)

    def layout_system(si: int, sysfs: float,
                      wk: np.ndarray) -> list[tuple[float, float, str, float]] | None:
        sysm = systems[si]
        sysnotes = [n for n in sorted(by_sys[si], key=lambda n: n.x)
                    if not n.tie_cont and position_for_midi(n.midi) is not None]
        if not sysnotes:
            return []
        min_midi = min(n.midi for n in sysnotes)
        span = max(n.midi for n in sysnotes) - min_midi
        slope = PITCH_SLOPE * sysm.step
        if span > 0:
            slope = min(slope, BAND_MAX * sysm.step / span)
        sizes = [sysfs * r for r in SHRINK_STEPS if sysfs * r >= floor] or [sysfs]

        # fase 1: folga de cada coluna (menor y livre acima da pauta); se a
        # coluna não comporta o tamanho do sistema, o número cede até o piso.
        items = []   # [nota, texto, w, x0, x1, folga_y, contorno_d, fs, cap]
        for n in sysnotes:
            text = str(position_for_midi(n.midi))
            d = (n.midi - min_midi) * slope
            got = False
            for fs in sizes:
                ix0, ix1, _ = _digit_span(text, fs, n.x)
                cap = fs * CAP_RATIO
                x0 = max(0, int((ix0 - PAD_X) * s))
                x1 = min(w_px, int((ix1 + PAD_X) * s) + 1)
                y = sysm.top - BASE_CLEAR * sysm.step
                limit = y - MAX_LIFT
                while y > limit:
                    yt, yb = boxr(y, x0, x1, cap)
                    if not ink[yt:yb, x0:x1].any():
                        break
                    y -= 1.0 / s
                if y > limit:
                    items.append([n, text, ix1 - ix0, x0, x1, y, d, fs, cap])
                    got = True
                    break
            if not got:
                whynot(f"sem folga: sist{si+1} x={n.x:.0f} {n.name}")
                return None

        # fase 2: linha-base por erosão dupla — variação entre vizinhos
        # limitada a CONTOUR_ALPHA × diferença de altura (zero p/ mesma nota).
        m = len(items)
        u = [it[5] + it[6] for it in items]
        eps = [CONTOUR_ALPHA * abs(items[i + 1][6] - items[i][6])
               for i in range(m - 1)]
        ceiling = sysm.top - MAX_LIFT
        ys: list[float] = []
        exempt: dict[int, float] = {}
        for _ in range(8):
            fwd = [0.0] * m
            fwd[0] = u[0]
            for i in range(1, m):
                fwd[i] = min(u[i], fwd[i - 1] + eps[i - 1])
            bv = [0.0] * m
            bv[-1] = fwd[-1]
            for i in range(m - 2, -1, -1):
                bv[i] = min(fwd[i], bv[i + 1] + eps[i])
            ys = [bv[i] - items[i][6] for i in range(m)]
            for i, ey in exempt.items():
                ys[i] = ey
            stable = True
            for i, (n, text, w, x0, x1, clear_y, d, fs, cap) in enumerate(items):
                if i in exempt:
                    continue
                y = ys[i]
                yt, yb = boxr(y, x0, x1, cap)
                if not ink[yt:yb, x0:x1].any():
                    continue
                stable = False
                y_up = y
                while y_up >= ceiling:
                    yt, yb = boxr(y_up, x0, x1, cap)
                    if not ink[yt:yb, x0:x1].any():
                        break
                    y_up -= 1.0 / s
                if y_up >= ceiling:
                    u[i] = y_up + d
                    ys[i] = y_up
                else:
                    # subir é impossível: desce até o 1º vão livre (no pior
                    # caso, a folga da própria coluna) e leva junto a cadeia
                    # de mesma nota colada.
                    y_dn = y
                    while y_dn < clear_y:
                        yt, yb = boxr(y_dn, x0, x1, cap)
                        if not ink[yt:yb, x0:x1].any():
                            break
                        y_dn += 1.0 / s
                    y_e = min(y_dn, clear_y)
                    exempt[i] = y_e
                    ys[i] = y_e
                    for rng in (range(i - 1, -1, -1), range(i + 1, m)):
                        prev = i
                        for j in rng:
                            if abs(items[j][6] - items[i][6]) > 1e-9:
                                break
                            if abs(items[j][0].x - items[prev][0].x) > SAME_PITCH_STRICT_DX:
                                break
                            jx0, jx1 = items[j][3], items[j][4]
                            yt, yb = boxr(y_e, jx0, jx1, items[j][8])
                            if ink[yt:yb, jx0:jx1].any():
                                break
                            exempt[j] = y_e
                            ys[j] = y_e
                            prev = j
            if stable:
                break
        else:
            whynot(f"erosão não convergiu: sist{si+1}")
            return None

        def ok_at(j: int, y: float) -> bool:
            """Posição válida p/ o item j: dentro dos limites e sem tinta."""
            if y > items[j][5] + 1e-6 or y < ceiling:
                return False
            yt, yb = boxr(y, items[j][3], items[j][4], items[j][8])
            return not ink[yt:yb, items[j][3]:items[j][4]].any()

        # reparo local: depois das exceções, restaura ordem/igualdade movendo
        # números para baixo (preferência) ou para cima, dentro dos limites —
        # em vez de rejeitar a fonte da página inteira.
        for _ in range(60):
            fixed_all = True
            for i in range(m - 1):
                d1, d2 = items[i][6], items[i + 1][6]
                y1, y2 = ys[i], ys[i + 1]
                if abs(d1 - d2) < 1e-9:
                    dx = items[i + 1][0].x - items[i][0].x
                    if abs(y1 - y2) > 1e-6 and dx <= SAME_PITCH_STRICT_DX:
                        ylow, yhigh = max(y1, y2), min(y1, y2)
                        if ok_at(i, ylow) and ok_at(i + 1, ylow):
                            ys[i] = ys[i + 1] = ylow
                            fixed_all = False
                        elif ok_at(i, yhigh) and ok_at(i + 1, yhigh):
                            ys[i] = ys[i + 1] = yhigh
                            fixed_all = False
                else:
                    hi, lo = (i + 1, i) if d2 > d1 else (i, i + 1)
                    if ys[hi] < ys[lo] - 1e-6:
                        continue   # agudo acima do grave: ordem ok
                    tgt = ys[hi] + SEP_MIN     # desce o grave p/ baixo do agudo
                    if ok_at(lo, tgt):
                        ys[lo] = tgt
                        fixed_all = False
                    else:                      # ou sobe o agudo
                        tgt = ys[lo] - SEP_MIN
                        if ok_at(hi, tgt):
                            ys[hi] = tgt
                            fixed_all = False
            if fixed_all:
                break

        def order_safe(j: int, ynew: float) -> bool:
            """Mover j p/ ynew preserva ordem/igualdade com os vizinhos?"""
            for k in (j - 1, j + 1):
                if not 0 <= k < m:
                    continue
                dk, dj = items[k][6], items[j][6]
                if abs(dk - dj) < 1e-9:
                    dxjk = abs(items[k][0].x - items[j][0].x)
                    if dxjk <= SAME_PITCH_STRICT_DX and abs(ys[k] - ynew) > 1e-6:
                        return False
                elif dk > dj:
                    if not ys[k] < ynew - 1e-6:
                        return False
                else:
                    if not ynew < ys[k] - 1e-6:
                        return False
            return True

        # espalhamento: vizinhos apertados na horizontal e de alturas
        # DIFERENTES separam-se na vertical (como o escalonamento "5⁴" da
        # anotação à mão) — sempre na direção correta do contorno.
        for _ in range(40):
            moved = False
            for i in range(m - 1):
                a, b = items[i], items[i + 1]
                if abs(a[6] - b[6]) < 1e-9:
                    continue
                if a[4] <= b[3] or b[4] <= a[3]:
                    continue   # caixas sem sobreposição horizontal
                hi, lo = (i + 1, i) if b[6] > a[6] else (i, i + 1)
                need = items[lo][8] + OBST_GAP * 1.5
                if ys[lo] - ys[hi] >= need - 1e-6:
                    continue   # já separados o bastante
                tgt = ys[hi] + need          # preferência: desce o grave
                if ok_at(lo, tgt) and order_safe(lo, tgt):
                    ys[lo] = tgt
                    moved = True
                    continue
                tgt = ys[lo] - need          # senão: sobe o agudo
                if ok_at(hi, tgt) and order_safe(hi, tgt):
                    ys[hi] = tgt
                    moved = True
            if not moved:
                break

        # verificação dura: ordem estrita entre alturas distintas (sempre) e
        # igualdade exata entre mesma nota próxima. Violação => rejeita.
        for i in range(m - 1):
            d1, d2 = items[i][6], items[i + 1][6]
            y1, y2 = ys[i], ys[i + 1]
            if abs(d1 - d2) < 1e-9:
                dx = items[i + 1][0].x - items[i][0].x
                if abs(y1 - y2) > 1e-6 and dx <= SAME_PITCH_STRICT_DX:
                    whynot(f"par mesma nota desigual: sist{si+1} "
                           f"{items[i][0].name} x={items[i][0].x:.0f} "
                           f"dx={dx:.0f} dy={abs(y1-y2):.1f}")
                    return None
            else:
                if not ((y2 < y1) if d2 > d1 else (y1 < y2)):
                    whynot(f"ordem invertida: sist{si+1} "
                           f"{items[i][0].name}->{items[i+1][0].name} "
                           f"x={items[i][0].x:.0f}")
                    return None

        # carimbo: números não podem se tocar; o número específico pode ceder
        # até o piso (15%) antes de rejeitar o sistema.
        out: list[tuple[float, float, str, float]] = []
        for i, (n, text, w, x0, x1, _, d, fs, cap) in enumerate(items):
            y = ys[i]
            ok = False
            for r in SHRINK_STEPS:
                fs2 = sysfs * r
                if fs2 > fs + 1e-9 or fs2 < floor:
                    continue
                ix0, ix1, pen = _digit_span(text, fs2, n.x)
                cap2 = fs2 * CAP_RATIO
                nx0 = max(0, int((ix0 - PAD_X) * s))
                nx1 = min(w_px, int((ix1 + PAD_X) * s) + 1)
                yt, yb = boxr(y, nx0, nx1, cap2)
                if not wk[yt:yb, nx0:nx1].any():
                    out.append((pen, y, text, fs2))
                    wk[yt:yb, nx0:nx1] = True
                    ok = True
                    break
            if not ok:
                whynot(f"números se tocam: sist{si+1} x={n.x:.0f} {n.name}")
                return None
        return out

    work = ink.copy()
    placements: list[tuple[float, float, str, float]] = []
    for si in sorted(by_sys):
        done = None
        for r in SHRINK_STEPS:
            sysfs = fontsize * r
            if sysfs < floor:
                break
            wk = work.copy()
            res = layout_system(si, sysfs, wk)
            if res is not None:
                done = res
                work = wk
                break
        if done is None:
            return None
        placements.extend(done)
    return placements


def annotate(in_path: str, out_path: str) -> tuple[int, float]:
    doc = pymupdf.open(in_path)
    total = 0
    used_size = 0.0
    for page in doc:
        notes, systems = extract_notes(page)
        if not notes:
            continue
        ink = _build_ink(page)
        placements = None
        size = FONT_MAX
        while size >= FONT_MIN:
            placements = _try_layout(notes, systems, ink, size)
            if placements is not None:
                break
            size -= FONT_STEP
        if placements is None:
            raise RuntimeError("não foi possível posicionar os números nem com a fonte mínima")
        used_size = size
        for x, y, text, fs in placements:
            page.insert_text((x, y), text, fontsize=fs, color=COLOR)
        total += len(placements)
    doc.save(out_path)
    doc.close()
    return total, used_size


if __name__ == "__main__":
    import sys

    src = sys.argv[1] if len(sys.argv) > 1 else "/Users/pluto/Desktop/Folhas Secas-Limpa.pdf"
    dst = sys.argv[2] if len(sys.argv) > 2 else "/tmp/Folhas-anotada.pdf"
    n, size = annotate(src, dst)
    print(f"{n} posições escritas em {dst} (fonte {size}pt)")
