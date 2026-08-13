"""Extrai máscaras de moldura de filme das referências.

Uma máscara de borda não é um mapa escalar como as de dano. A moldura tem cor
própria — rebate preto, furo branco, letreiro laranja — e tem um buraco no meio
por onde a foto aparece. Então a saída é **PNG RGBA**: RGB é a cor da moldura, A
é a cobertura, e a janela interna fica com A = 0. Compor é uma linha, e funciona
sobre qualquer foto.

O que torna a extração não-trivial é que **cor não basta para decidir cobertura**.
A perfuração é branca e o fundo fora da tira também é branco: separados por cor,
os furos ficariam transparentes e a foto apareceria através deles. O que
distingue os dois não é o tom, é a topologia — o furo está *dentro* da tira e o
fundo está fora. Por isso a extração é feita por componentes conexos:

1. `tinta` = distância até a cor de fundo, contínua, que já traz o antialiasing
   e as bordas rasgadas de graça;
2. limiar baixo, e o componente de fundo é o que **encosta na moldura da
   imagem** — todo o resto é a tira;
3. a silhueta é a tira com os buracos tapados;
4. os buracos se separam por área: os grandes são **janela de imagem** (a foto
   entra ali, A = 0), os pequenos são **perfuração** (A = 1, brancos e opacos).

Daí sai também a segunda coisa que o efeito precisa saber, e que nenhuma máscara
escalar carregaria: onde a janela fica. Vai num `frames.json` ao lado das
máscaras, em coordenadas normalizadas.

Dois modos de reamostragem, porque as referências são de duas naturezas:

* `sharp` — arte chapada (tira vetorial). A forma é geométrica, então a alfa é
  ampliada e **relimiarizada**: a borda volta nítida no tamanho grande em vez de
  virar degradê. É o que permite uma máscara de 3000 px sair de um thumbnail.
* `photo` — scan de filme de verdade. Aí a irregularidade *é* o conteúdo e
  relimiarizar a destruiria; vai Lanczos puro.

    python3 tools/extract_borders.py refs -o borders --manifest refs/borders.json
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any

import numpy as np
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None


# ------------------------------------------------------------ componentes conexos


def _label(b: np.ndarray) -> tuple[np.ndarray, int]:
    """Rotula componentes 4-conexos de um binário. Duas passagens sobre runs.

    Feito à mão porque o projeto inteiro se sustenta em numpy e Pillow, e trazer
    scipy só para isto não se paga. Trabalhar por *run* — trecho contíguo de uma
    linha — em vez de por pixel deixa a união-busca com poucos milhares de nós
    mesmo numa imagem grande.
    """
    h, w = b.shape
    labels = np.zeros((h, w), np.int32)
    parent: list[int] = [0]

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, c: int) -> None:
        ra, rc = find(a), find(c)
        if ra != rc:
            parent[max(ra, rc)] = min(ra, rc)

    prev: list[tuple[int, int, int]] = []
    for y in range(h):
        row = b[y]
        if not row.any():
            prev = []
            continue
        d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
        starts = np.flatnonzero(d == 1)
        ends = np.flatnonzero(d == -1)

        cur: list[tuple[int, int, int]] = []
        for s, e in zip(starts, ends):
            lab = 0
            for ps, pe, pl in prev:
                if ps < e and s < pe:          # sobreposição na linha anterior
                    lab = pl if lab == 0 else lab
                    union(lab, pl)
            if lab == 0:
                lab = len(parent)
                parent.append(lab)
            labels[y, s:e] = lab
            cur.append((s, e, lab))
        prev = cur

    # Achata a união-busca e compacta os rótulos para 1..n.
    roots = np.array([find(i) for i in range(len(parent))], np.int32)
    uniq = np.unique(roots[1:]) if len(parent) > 1 else np.array([], np.int32)
    remap = np.zeros(len(parent), np.int32)
    for i, r in enumerate(uniq, start=1):
        remap[roots == r] = i
    remap[0] = 0
    return remap[labels], len(uniq)


def _touches_border(mask: np.ndarray) -> bool:
    return bool(mask[0].any() or mask[-1].any() or mask[:, 0].any() or mask[:, -1].any())


# ------------------------------------------------------------------- fundo e tinta


def _background(rgb: np.ndarray, alpha: np.ndarray | None, kind: str,
                bg_rgb: np.ndarray, tol: float) -> np.ndarray:
    """Quanto cada pixel se parece com o fundo, em [0,1] — 1 é fundo puro.

    Dois testes bastam para as referências:

    * `alpha` — o arquivo já traz transparência (webp/png). É o caso limpo.
    * `plain` — arte recortada sobre cor chapada. Nem sempre branca: em várias
      referências a janela é o creme do papel, e medir distância até o branco
      puro faria o creme contar como moldura.

    Fica de fora, deliberadamente, o xadrez cinza que os bancos usam para
    *desenhar* transparência num JPEG. Houve um teste para ele — nível, lisura e
    saturação — e ele não sobrevive à compressão: no arquivo de 339 px os dois
    níveis do xadrez viram um contínuo de 0,75 a 0,96, encostam no creme do papel
    envelhecido, e o que separava os dois deixa de separar. Referência assim se
    resolve recortando no quadro da moldura e dando a janela à mão, que é o que
    `copia-papel` faz. Um teste que só funciona no caso fácil não vale o código.
    """
    if kind == "alpha" and alpha is not None:
        return 1.0 - alpha

    # Distância pelo canal que mais se afasta, não pela média: laranja saturado
    # tem luminância alta e passaria por fundo claro se medido por média.
    d = np.abs(rgb - bg_rgb).max(axis=2)
    return np.clip(1.0 - d / max(tol, 1e-3), 0.0, 1.0)


def _despeckle(rgb: np.ndarray, r: int) -> np.ndarray:
    """Tira marca d'água fina de arte chapada, por abertura e fechamento.

    A marca do banco é traço claro e fino por cima do rebate escuro. Uma abertura
    com elemento maior que o traço e menor que o letreiro apaga o traço e devolve
    o preto; o fechamento seguinte cuida do trecho da marca que cai sobre furo
    branco. Só serve para arte chapada — numa textura fotográfica isto comeria
    justamente o detalhe que dá valor à referência.
    """
    if r < 1:
        return rgb
    k = 2 * r + 1
    im = Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))
    im = im.filter(ImageFilter.MinFilter(k)).filter(ImageFilter.MaxFilter(k))
    im = im.filter(ImageFilter.MaxFilter(k)).filter(ImageFilter.MinFilter(k))
    return np.asarray(im, np.float32) / 255.0


# ------------------------------------------------------------------------ extração


def extract(path: str, crop=None, bg: str = "plain", mode: str = "sharp",
            width: int = 3000, window_min: float = 0.03, ink: float = 0.35,
            despeckle: int = 0, bg_rgb=(1.0, 1.0, 1.0), tol: float = 0.10,
            window=None, rect_window: bool = True,
            window_grow: int = 2) -> tuple[Image.Image, list]:
    """Devolve (máscara RGBA, janelas) de uma referência de moldura.

    `window` recorta a janela por retângulo dado em vez de por topologia. É o que
    permite usar scan de filme *com foto dentro* — ali a janela não é fundo, é
    paisagem, e nenhum teste de cor a encontraria. As referências assim são as
    melhores que existem, porque a moldura é filme de verdade e não desenho.

    `rect_window` preenche a janela até o retângulo em vez de usar a forma exata
    do buraco. Sem isso, duas coisas passam: a marca d'água escrita *dentro* da
    janela sobra como ilha opaca no meio da foto, e uma mancha na referência come
    um pedaço da janela. Só fica desligado quando a janela é redonda de verdade,
    caso do canto arredondado de cópia e de slide montado.
    """
    im = Image.open(path)
    src_alpha = None
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        src_alpha = np.asarray(im.split()[-1], np.float32) / 255.0
    im = im.convert("RGB")

    if crop:
        x0, y0, x1, y1 = crop
        box = (int(x0 * im.width), int(y0 * im.height),
               int(x1 * im.width), int(y1 * im.height))
        if src_alpha is not None:
            src_alpha = src_alpha[box[1]:box[3], box[0]:box[2]]
        im = im.crop(box)

    rgb = np.asarray(im, np.float32) / 255.0
    if despeckle:
        rgb = _despeckle(rgb, despeckle)

    b = np.asarray(bg_rgb, np.float32)
    back = _background(rgb, src_alpha, bg, b, tol)
    tinta = 1.0 - back

    # 1. Quem é fundo de verdade: o componente que encosta na moldura da imagem.
    #    O resto que parecia fundo — o branco dentro de uma perfuração — não é.
    solid = tinta > ink
    lab, n = _label(~solid)
    outside = np.zeros_like(solid)
    for i in range(1, n + 1):
        c = lab == i
        if _touches_border(c):
            outside |= c

    silhouette = ~outside

    # Só a moldura, e nada mais que esteja solto no quadro. Nas referências de
    # banco a marca d'água é escrita *fora* da moldura, no papel branco: sem este
    # filtro ela conta como tinta, entra na máscara e ainda estica o recorte até
    # englobá-la, deixando a moldura pequena num canto.
    slab, sn = _label(silhouette)
    if sn > 1:
        areas = np.bincount(slab.ravel(), minlength=sn + 1)
        areas[0] = 0
        silhouette = slab == int(areas.argmax())

    # 2. Buracos: o que é fundo mas está cercado pela tira. Os grandes são janela
    #    de imagem; os pequenos são perfuração e continuam opacos.
    windows: list[tuple[int, int, int, int]] = []
    win_mask = np.zeros_like(silhouette)
    gh, gw = rgb.shape[:2]

    def _grow(r: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        """Alarga a janela alguns pixels antes de recortá-la.

        A fronteira do quadro na arte de origem é antialiasada, e a franja clara
        dela fica *fora* do buraco detectado — o limiar a classificou como tinta.
        Recortando no retângulo exato, essa franja sobrevive opaca e aparece na
        aplicação como uma linha branca fina contornando cada quadro. Numa tira
        ampliada oito vezes a linha fica grossa e é a primeira coisa que se vê.
        """
        g = max(window_grow, 0)
        return (max(r[0] - g, 0), max(r[1] - g, 0), min(r[2] + g, gw), min(r[3] + g, gh))

    if window:
        # Janela dada: a referência tem foto dentro, então aqui não há buraco
        # nenhum a achar — o quadro inteiro é moldura menos este retângulo.
        h0, w0 = rgb.shape[:2]
        for x0, y0, x1, y1 in ([window] if np.ndim(window[0]) == 0 else window):
            r = _grow((int(x0 * w0), int(y0 * h0), int(x1 * w0), int(y1 * h0)))
            win_mask[r[1]:r[3], r[0]:r[2]] = True
            windows.append(r)
        silhouette |= win_mask
    else:
        holes = silhouette & ~solid
        hlab, hn = _label(holes)
        area = silhouette.sum()
        for i in range(1, hn + 1):
            c = hlab == i
            if c.sum() < window_min * area:
                continue
            ys, xs = np.nonzero(c)
            r = _grow((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
            windows.append(r)
            if rect_window:
                win_mask[r[1]:r[3], r[0]:r[2]] = True
            else:
                win_mask |= c

    # 3. Alfa. No miolo é opaca por construção — é isso que mantém a perfuração
    #    branca sólida. Só a beirada usa a tinta contínua, e é ela que preserva
    #    antialiasing e borda rasgada.
    inner = silhouette & ~win_mask
    edge = np.asarray(
        Image.fromarray(inner.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(5)),
        np.float32) / 255.0
    alpha = np.where(edge > 0.5, 1.0, np.clip(tinta, 0.0, 1.0) * inner)

    # 4. Desmistura a beirada: o pixel meio-transparente veio misturado com o
    #    fundo, e guardar essa mistura no RGB deixaria halo do fundo na aplicação.
    a = np.clip(alpha, 0.0, 1.0)[..., None]
    fg = np.where(a > 0.02, (rgb - (1.0 - a) * b) / np.maximum(a, 0.02), rgb)
    out = np.concatenate([np.clip(fg, 0.0, 1.0), a], axis=2)

    # 5. Recorta na silhueta e reamostra.
    ys, xs = np.nonzero(silhouette)
    y0, y1, x0, x1 = int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1
    out = out[y0:y1, x0:x1]
    windows = [(a0 - x0, b0 - y0, a1 - x0, b1 - y0) for a0, b0, a1, b1 in windows]
    h, w = out.shape[:2]

    scale = width / max(w, h)
    tw, th = max(1, round(w * scale)), max(1, round(h * scale))
    img = Image.fromarray((out * 255).astype(np.uint8), "RGBA").resize(
        (tw, th), Image.LANCZOS)

    if mode == "sharp" and scale > 1.0:
        # Arte chapada: a alfa ampliada vira degradê, e a borda de uma tira de
        # filme não é degradê. Relimiarizar no meio devolve o contorno duro que a
        # fonte tinha — a forma é geométrica, então nada se perde nisso.
        r, g, bl, al = img.split()
        al = al.point(lambda v: 0 if v < 128 else 255)

        # E o RGB precisa do mesmo tratamento, senão sobra metade do problema.
        # Endurecer só a alfa deixa a rampa cinza do contorno original valendo
        # alfa 1: na aplicação ela vira uma linha clara em volta de cada quadro,
        # tanto mais grossa quanto maior a ampliação — numa tira ampliada oito
        # vezes ficava impossível de ignorar. A mediana escolhe o lado que
        # domina e transforma a rampa em degrau; letreiro e furo, que são dezenas
        # de vezes mais largos que ela, não sentem.
        med = ImageFilter.MedianFilter(5)
        img = Image.merge("RGBA", (r.filter(med), g.filter(med), bl.filter(med),
                                   al.filter(ImageFilter.SMOOTH)))

    win = [[round(a0 / w, 5), round(b0 / h, 5), round(a1 / w, 5), round(b1 / h, 5)]
           for a0, b0, a1, b1 in windows]
    win.sort(key=lambda r: (r[0], r[1]))
    return img, win


def main() -> None:
    ap = argparse.ArgumentParser(description="Extrai máscaras de moldura das referências")
    ap.add_argument("src", help="pasta com as referências de moldura")
    ap.add_argument("-o", "--output", default="borders")
    ap.add_argument("--manifest", required=True, help="JSON com uma entrada por máscara")
    ap.add_argument("--width", type=int, default=3000, help="lado maior da máscara")
    a = ap.parse_args()

    os.makedirs(a.output, exist_ok=True)
    with open(a.manifest, encoding="utf-8") as f:
        spec: dict[str, Any] = json.load(f)

    frames: dict[str, Any] = {}
    for name, e in spec.items():
        if name.startswith("_"):
            continue
        img, win = extract(
            os.path.join(a.src, e["src"]), e.get("crop"), e.get("bg", "plain"),
            e.get("mode", "sharp"), a.width, e.get("window_min", 0.03),
            e.get("ink", 0.35), e.get("despeckle", 0),
            e.get("bg_rgb", (1.0, 1.0, 1.0)), e.get("tol", 0.10), e.get("window"),
            e.get("rect_window", True), e.get("window_grow", 2),
        )
        img.save(os.path.join(a.output, f"{name}.png"))
        frames[name] = {"note": e.get("note", ""), "size": list(img.size), "windows": win}
        cov = np.asarray(img.split()[-1], np.float32).mean() / 255 * 100
        print(f"{name:<18} ← {e['src']:<50} {img.size[0]}x{img.size[1]} "
              f"cobertura {cov:5.1f}%  janelas {len(win)}")

    with open(os.path.join(a.output, "frames.json"), "w", encoding="utf-8") as f:
        json.dump(frames, f, indent=2, ensure_ascii=False)
    print(f"→ {os.path.join(a.output, 'frames.json')}")


if __name__ == "__main__":
    main()
