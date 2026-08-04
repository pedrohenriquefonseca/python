"""Linha de comando para gerar e revisar vazamentos de luz.

    python3 cli.py foto.jpg -o out/foto.jpg --preset fogo-na-borda --seed 7
    python3 cli.py foto.jpg --gallery -o out/gallery.jpg     # os 20 presets
    python3 cli.py foto.jpg --sheet 12                       # sorteio livre
"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw

from filmfx import (
    PALETTES, PRESETS, HalationParams, LeakParams, apply, halation,
    preset_params, preset_recipe, roll_recipe,
)
from filmfx.imaging import load_rgb, save_rgb

_SLIDERS = ("intensity", "chroma", "spread", "softness", "complexity", "texture", "veil", "grain")


def _params(a: argparse.Namespace, seed: int, preset: str | None) -> LeakParams:
    """Preset define os defaults; qualquer slider passado na linha vence."""
    p = preset_params(preset) if preset else LeakParams()
    for name in _SLIDERS:
        given = getattr(a, name)
        if given is not None:
            setattr(p, name, given)
    if a.palette:
        p.palette = a.palette
    p.seed = seed
    return p


def _thumb(arr: np.ndarray, width: int) -> np.ndarray:
    h, w = arr.shape[:2]
    im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8))
    return np.asarray(
        im.resize((width, max(1, round(h * width / w))), Image.LANCZOS), dtype=np.float32
    ) / 255.0


def _mosaic(tiles: list[np.ndarray], labels: list[str] | None, cols: int, out: str) -> None:
    th, tw = tiles[0].shape[:2]
    rows = math.ceil(len(tiles) / cols)
    pad = 26 if labels else 0
    sheet = np.zeros((rows * (th + pad), cols * tw, 3), dtype=np.float32)
    for i, t in enumerate(tiles):
        r, c = divmod(i, cols)
        y0 = r * (th + pad) + pad
        sheet[y0 : y0 + t.shape[0], c * tw : c * tw + t.shape[1]] = t

    if labels:
        im = Image.fromarray((np.clip(sheet, 0, 1) * 255).astype(np.uint8))
        d = ImageDraw.Draw(im)
        for i, text in enumerate(labels):
            r, c = divmod(i, cols)
            d.text((c * tw + 6, r * (th + pad) + 7), text, fill=(235, 235, 235))
        sheet = np.asarray(im, dtype=np.float32) / 255.0

    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    save_rgb(sheet, out)
    print(f"→ {out}")


def _halation(a: argparse.Namespace, img: np.ndarray) -> None:
    base = a.intensity if a.intensity is not None else HalationParams.intensity
    if a.sweep:
        levels = np.linspace(0.0, base * 2.0, a.sweep)
        tiles, labels = [], []
        for v in levels:
            tiles.append(_thumb(halation.apply(img, HalationParams(intensity=float(v))), a.width))
            labels.append(f"intensity {v:.2f}")
        _mosaic(tiles, labels, a.sweep, a.output or "out/halation_sweep.jpg")
        return

    out = a.output or "out/halation.jpg"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    save_rgb(halation.apply(img, HalationParams(intensity=base)), out)
    print(f"→ {out}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Light leak generativo")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", default=None)
    ap.add_argument("--preset", default=None, choices=sorted(PRESETS))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--sheet", type=int, default=0, help="N variações do sorteio livre")
    ap.add_argument("--gallery", action="store_true", help="um quadro por preset")
    ap.add_argument("--palettes", action="store_true", help="um quadro por paleta de corante")
    ap.add_argument("--palette", default=None, choices=sorted(PALETTES) + ["auto", "permutar"])
    ap.add_argument("--width", type=int, default=430, help="largura das miniaturas")
    ap.add_argument("--effect", default="leak", choices=("leak", "halation"))
    ap.add_argument("--sweep", type=int, default=0, help="N intensidades lado a lado")
    for name in _SLIDERS:
        ap.add_argument(f"--{name}", type=float, default=None)
    a = ap.parse_args()

    img = load_rgb(a.input)

    if a.effect == "halation":
        _halation(a, img)
        return

    if a.gallery:
        tiles, labels = [], []
        for i, name in enumerate(PRESETS):
            p = _params(a, (a.seed or 0) + i, name)
            tiles.append(_thumb(apply(img, p, preset_recipe(name, p)), a.width))
            labels.append(PRESETS[name]["label"])
            print(f"{name:<22} {PRESETS[name]['note']}")
        _mosaic(tiles, labels, 4, a.output or "out/gallery.jpg")
        return

    if a.palettes:
        tiles, labels = [], []
        for pal in PALETTES:
            # Mesma semente em todas: só a cor muda, a geometria fica fixa.
            p = _params(a, a.seed or 0, a.preset)
            p.palette = pal
            recipe = preset_recipe(a.preset, p) if a.preset else roll_recipe(p)
            tiles.append(_thumb(apply(img, p, recipe), a.width))
            labels.append(pal)
        _mosaic(tiles, labels, 4, a.output or "out/palettes.jpg")
        return

    if a.sheet:
        tiles = []
        for i in range(a.sheet):
            p = _params(a, (a.seed or 0) + i, a.preset)
            recipe = preset_recipe(a.preset, p) if a.preset else roll_recipe(p)
            tiles.append(_thumb(apply(img, p, recipe), a.width))
        _mosaic(tiles, None, min(4, a.sheet), a.output or "out/sheet.jpg")
        return

    seed = a.seed if a.seed is not None else int(np.random.default_rng().integers(0, 2**31))
    p = _params(a, seed, a.preset)
    recipe = preset_recipe(a.preset, p) if a.preset else roll_recipe(p)
    out = a.output or "out/leak.jpg"
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    save_rgb(apply(img, p, recipe), out)
    print(json.dumps(recipe.to_dict(), indent=2, ensure_ascii=False))
    print(f"→ {out}")


if __name__ == "__main__":
    main()
