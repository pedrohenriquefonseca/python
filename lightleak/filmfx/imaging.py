"""Conversões de espaço de cor e I/O.

Todos os efeitos são compostos em luz linear, porque no filme a luz parasita
soma exposição no negativo — em sRGB a soma daria resultado errado.
"""
from __future__ import annotations

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def load_rgb(path: str) -> np.ndarray:
    img = Image.open(path)
    img = img.convert("RGB")
    return np.asarray(img, dtype=np.float32) / 255.0


def save_rgb(arr: np.ndarray, path: str, quality: int = 95) -> None:
    out = np.clip(arr, 0.0, 1.0) * 255.0 + 0.5
    Image.fromarray(out.astype(np.uint8), mode="RGB").save(
        path, quality=quality, subsampling=0
    )


def srgb_to_linear(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4).astype(np.float32)


def linear_to_srgb(x: np.ndarray) -> np.ndarray:
    x = np.clip(x, 0.0, None)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055).astype(np.float32)


def screen_add(base: np.ndarray, add: np.ndarray) -> np.ndarray:
    """Soma luz num meio que já satura: `1 - (1-base)·exp(-add)`.

    Forma de Beer–Lambert, e ela resolve de uma vez o que um ombro compressivo
    não consegue:

    * `add = 0` devolve a base bit-a-bit — o efeito desligado é identidade exata;
    * base = 1 continua 1, então branco puro na entrada não escurece;
    * para `add` pequeno é praticamente aditivo, que é o regime das sombras, onde
      tanto o vazamento quanto a halação de fato importam;
    * `add` grande satura suavemente em 1, sem corte duro no núcleo.

    Um ombro com assíntota em 1 não podia atender ao segundo item: qualquer curva
    compressiva que passe por (joelho, joelho) com derivada 1 fica *abaixo* da
    identidade daí em diante, e o branco da entrada saía cinza.
    """
    return (1.0 - (1.0 - np.clip(base, 0.0, 1.0)) * np.exp(-np.maximum(add, 0.0))).astype(np.float32)


def resize_field(field: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """Reamostra um mapa escalar float32 para (largura, altura)."""
    if field.shape[1] == size[0] and field.shape[0] == size[1]:
        return field
    im = Image.fromarray(field.astype(np.float32), mode="F")
    return np.asarray(im.resize(size, Image.BICUBIC), dtype=np.float32)
