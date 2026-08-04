"""Extrai máscaras de dano das fotografias de referência.

Duas propriedades separam dano de fotografia, e o extrator usa as duas em
sequência.

**Escala.** Dano é estrutura fina e clara por cima de conteúdo largo. Abrir a
imagem com um elemento maior que a largura do vinco apaga o vinco e deixa o
resto; o que sobra na diferença é candidato a dano — é o top-hat branco.

    tophat = img − abertura(img, r)

Só que isso não basta. Cabelo, cílio, brilho de olho e textura de tricô também
são finos e claros, e passam inteiros: a primeira extração trouxe a barba do
retrato junto com os riscos.

**Comprimento.** É aqui que os dois se separam de verdade. Vinco e risco são
longos e conexos — dezenas de vezes mais compridos que largos. Grão de papel,
poro de pele e textura de tricô são curtos, por mais claros que sejam.

A medida é o comprimento do maior caminho conexo que passa por cada pixel, e
*não* uma abertura por segmento de reta. A abertura por reta exige alinhamento
perfeito no comprimento inteiro, e vinco de verdade entorta: com ela os riscos
saíam picotados em bastões retos, justamente o aspecto sintético que se quer
evitar. O caminho aqui pode subir ou descer uma linha a cada coluna que avança,
então ele acompanha a curva.

O comprimento é medido num mapa binário de limiar baixo, para que trechos fracos
do mesmo vinco continuem conectados, mas quem passa pelo portão é a imagem em
tom contínuo — assim a variação de espessura e brilho ao longo do traço
sobrevive, e é ela que dá o aspecto orgânico.

Não uso o par antes/depois das referências que têm os dois lados: o lado
restaurado foi recolorido e reenquadrado, então a diferença carrega a mudança
de cor junto. O caminho morfológico não depende de par nenhum.

    python3 tools/extract_masks.py refs/ -o masks/
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Any

import numpy as np
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None


def _ridge(a: np.ndarray, d: int) -> np.ndarray:
    """Resposta de crista: o pixel tem de ser mais claro que os dois lados.

    É o teste que separa dano de conteúdo, e faltava. Trinca, vinco e risco são
    *cristas* — uma linha clara com escuro de cada lado. Contorno de objeto é
    *degrau*: claro de um lado e claro do outro também, porque do outro lado
    começa a região vizinha. O top-hat sozinho não vê diferença, e foi por isso
    que a lataria do carro, o letreiro pintado e a silhueta da figura entraram
    nas máscaras como se fossem arranhão.

    Exigir escuro dos dois lados mata o degrau e deixa a crista intacta. Quatro
    orientações bastam: uma crista fina responde forte na perpendicular a ela e
    o máximo entre as quatro cobre qualquer direção.
    """
    best = np.zeros_like(a)
    for dy, dx in ((0, d), (d, 0), (d, d), (d, -d)):
        p = np.roll(np.roll(a, dy, 0), dx, 1)
        m = np.roll(np.roll(a, -dy, 0), -dx, 1)
        best = np.maximum(best, np.minimum(a - p, a - m))
    return np.clip(best, 0.0, None)


def _sweep(b: np.ndarray, reverse: bool) -> np.ndarray:
    """Comprimento do caminho que chega a cada pixel, varrendo em x.

    Recorrência de programação dinâmica: o caminho pode avançar uma coluna e ao
    mesmo tempo subir ou descer uma linha. É esse ±1 que deixa o caminho
    *entortar* — e é a diferença entre isto e uma abertura por reta, que exige
    alinhamento perfeito e por isso picota vinco curvo em bastões.
    """
    h, w = b.shape
    out = np.zeros((h, w), np.int32)
    prev = np.zeros(h, np.int32)
    cols = range(w - 1, -1, -1) if reverse else range(w)
    for x in cols:
        up = np.empty_like(prev); up[:-1] = prev[1:]; up[-1] = 0
        dn = np.empty_like(prev); dn[1:] = prev[:-1]; dn[0] = 0
        cur = np.where(b[:, x], np.maximum(np.maximum(prev, up), dn) + 1, 0)
        out[:, x] = cur
        prev = cur
    return out


def _path_length(b: np.ndarray) -> np.ndarray:
    """Maior caminho conexo por pixel, tomando o melhor entre os dois eixos."""
    horiz = _sweep(b, False) + _sweep(b, True) - 1
    vert = (_sweep(b.T, False) + _sweep(b.T, True) - 1).T
    return np.where(b, np.maximum(horiz, vert), 0)


def _elongated(a: np.ndarray, length: int, seed: float = 0.12) -> np.ndarray:
    """Guarda só o que faz parte de um traço longo — curvo ou reto, tanto faz.

    Vinco e risco são longos e conexos; grão de papel, poro de pele e textura de
    tricô são curtos, por mais claros que sejam. Medir o comprimento do caminho
    separa os dois de um jeito que nenhum limiar de brilho consegue.

    O comprimento é medido num mapa binário de limiar baixo — para que trechos
    fracos do mesmo vinco continuem conectados — mas quem passa pelo portão é a
    imagem em tom contínuo, que preserva a variação de espessura e de brilho ao
    longo do traço. É essa variação que dá o aspecto orgânico.
    """
    peak = max(float(np.percentile(a, 99.5)), 1e-3)
    keep = _path_length(a > seed * peak) >= length
    return np.where(keep, a, 0.0).astype(np.float32)


def extract(path: str, width: int = 2200, radius: float = 0.004,
            reach: float = 0.10, floor: float = 0.10,
            crop: tuple[float, float, float, float] | None = None,
            polarity: str = "light", mode: str = "print") -> Image.Image:
    """Devolve a máscara de dano de uma referência, em tons de cinza.

    `polarity` diz de que cor o dano está *na referência*, não na saída. Em
    cópia de papel o vinco é claro, porque a emulsão soltou e apareceu o papel.
    Em negativo de vidro a trinca é escura. A geometria é a mesma nos dois e é
    ela que a máscara guarda, então as duas viram máscara clara no fim.

    `mode` escolhe quanto filtrar, e a escolha certa é a que preserva a
    *densidade* da referência. Filtrar demais foi o erro que mais custou aqui:
    cada teste que eu somava deixava a máscara mais limpa e mais vazia, até
    sobrar meia dúzia de fios onde a referência tinha uma teia fechada. Numa
    rede densa, um pouco de conteúdo vazado é invisível; uma rede que virou
    cinco riscos não tem conserto.

    * `raw` — a referência já é campo de risco sobre fundo escuro. Não há o que
      extrair: só estica o nível. Zero artefato, densidade intacta.
    * `print` — cópia de papel amassado. Top-hat mais comprimento de caminho, e
      **sem** o teste de crista: numa foto de papel o dano é a maior parte da
      estrutura fina, e a crista custa metade da rede para tirar pouco ruído.
    * `plate` — negativo de vidro. Aí sim entra a crista, porque a cena atrás é
      nítida e as bordas de objeto competem com as poucas trincas que existem.
    """
    im = Image.open(path).convert("L")
    if crop:
        x0, y0, x1, y1 = crop
        im = im.crop((int(x0 * im.width), int(y0 * im.height),
                      int(x1 * im.width), int(y1 * im.height)))
    if im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    if polarity == "dark":
        im = Image.eval(im, lambda v: 255 - v)

    g = np.asarray(im, np.float32)

    if mode == "raw":
        # O piso é percentil alto de propósito. Nessas referências o fundo ocupa
        # a maior parte do quadro, então um piso na mediana deixa o fundo inteiro
        # entrar com valor baixo — e o resultado não é risco, é névoa cobrindo a
        # foto. `floor` aqui é o percentil, não uma fração.
        lo = float(np.percentile(g, floor))
        hi = float(np.percentile(g, 99.7))
        m = np.clip((g - lo) / max(hi - lo, 1e-3), 0.0, 1.0)
        return Image.fromarray((m * 255).astype(np.uint8), mode="L")

    # Os dois raios acompanham o quadro e não o número de pixels: vinco mede uma
    # fração do lado, então a mesma referência escaneada maior dá a mesma máscara.
    s = max(im.size)
    r = max(1, int(round(radius * s)))
    top = np.clip(g - np.asarray(
        im.filter(ImageFilter.MinFilter(2 * r + 1)).filter(ImageFilter.MaxFilter(2 * r + 1)),
        np.float32), 0.0, None)

    if mode == "plate":
        top = np.minimum(top, _ridge(g, max(2, r)))
    top = _elongated(top, max(5, int(round(reach * s))))

    # Normaliza por um percentil alto, não pelo máximo: um pixel estourado no
    # scan achataria a máscara inteira.
    m = np.clip(top / max(float(np.percentile(top, 99.5)), 1e-3), 0.0, 1.0)
    # Piso: abaixo dele é grão de scan. Reescala o que sobra para o intervalo
    # cheio em vez de só cortar, senão a máscara perde contraste.
    m = np.clip((m - floor) / max(1.0 - floor, 1e-3), 0.0, 1.0)
    return Image.fromarray((m * 255).astype(np.uint8), mode="L")


def main() -> None:
    ap = argparse.ArgumentParser(description="Extrai máscaras de dano das referências")
    ap.add_argument("src", help="pasta com as fotos de referência")
    ap.add_argument("-o", "--output", default="masks")
    ap.add_argument("--manifest", default=None,
                    help="JSON {arquivo: [x0,y0,x1,y1]} com o recorte da parte danificada")
    ap.add_argument("--width", type=int, default=2200,
                    help="resolução de trabalho — a máscara é usada em fotos de "
                         "milhares de px, extrair pequeno vira borrão na aplicação")
    ap.add_argument("--radius", type=float, default=0.004)
    ap.add_argument("--reach", type=float, default=0.10, help="comprimento mínimo do risco")
    ap.add_argument("--floor", type=float, default=0.10)
    a = ap.parse_args()

    os.makedirs(a.output, exist_ok=True)

    if not a.manifest:
        # Sem manifesto: uma máscara por arquivo, quadro inteiro. Serve para
        # triagem, antes de decidir recortes.
        for n in sorted(x for x in os.listdir(a.src)
                        if x.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))):
            mask = extract(os.path.join(a.src, n), a.width, a.radius, a.reach, a.floor)
            mask.save(os.path.join(a.output, os.path.splitext(n)[0] + ".png"))
            print(f"{n:<24} cobertura {np.asarray(mask, np.float32).mean()/255*100:5.2f}%")
        return

    # Com manifesto: cada entrada é um filtro nomeado, e uma mesma referência
    # pode render vários — o recorte de uma região é o que separa, por exemplo,
    # o núcleo estilhaçado da periferia limpa da mesma foto.
    with open(a.manifest, encoding="utf-8") as f:
        spec: dict[str, Any] = json.load(f)

    for name, entry in spec.items():
        if name.startswith("_"):
            continue
        mask = extract(os.path.join(a.src, entry["src"]), a.width, a.radius,
                       entry.get("reach", a.reach), entry.get("floor", a.floor),
                       tuple(entry["crop"]), entry.get("polarity", "light"),
                       entry.get("mode", "print"))
        out = os.path.join(a.output, f"{name}.png")
        mask.save(out)
        print(f"{name:<24} ← {entry['src']:<18} "
              f"cobertura {np.asarray(mask, np.float32).mean()/255*100:5.2f}%")


if __name__ == "__main__":
    main()
