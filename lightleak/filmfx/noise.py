"""Ruído procedural determinístico (semente → sempre o mesmo resultado).

Value noise amostrado em coordenadas arbitrárias, o que permite avaliar o ruído
no sistema de coordenadas local do vazamento (u = ao longo do eixo, v = através
dele). Frequências diferentes em u e v produzem estrias alongadas sem precisar
de blur direcional caro.
"""
from __future__ import annotations

import numpy as np

_GRID = 64


def _grid(rng: np.random.Generator) -> np.ndarray:
    return rng.random((_GRID, _GRID), dtype=np.float32)


def _sample(grid: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    i0 = np.floor(u).astype(np.int64)
    j0 = np.floor(v).astype(np.int64)
    fu = (u - i0).astype(np.float32)
    fv = (v - j0).astype(np.float32)

    n = grid.shape[0]
    i0 %= n
    j0 %= n
    i1 = (i0 + 1) % n
    j1 = (j0 + 1) % n

    su = fu * fu * (3.0 - 2.0 * fu)
    sv = fv * fv * (3.0 - 2.0 * fv)

    top = grid[j0, i0] * (1 - su) + grid[j0, i1] * su
    bot = grid[j1, i0] * (1 - su) + grid[j1, i1] * su
    return (top * (1 - sv) + bot * sv).astype(np.float32)


def fbm(
    rng: np.random.Generator,
    u: np.ndarray,
    v: np.ndarray,
    octaves: int = 4,
    freq_u: float = 3.0,
    freq_v: float = 3.0,
    gain: float = 0.5,
    lacunarity: float = 2.0,
) -> np.ndarray:
    """Ruído fractal em [0,1] com frequência independente por eixo."""
    total = np.zeros_like(u, dtype=np.float32)
    amp = 1.0
    norm = 0.0
    fu, fv = freq_u, freq_v
    for _ in range(octaves):
        total += amp * _sample(_grid(rng), u * fu, v * fv)
        norm += amp
        amp *= gain
        fu *= lacunarity
        fv *= lacunarity
    return total / max(norm, 1e-6)


def grain(rng: np.random.Generator, shape: tuple[int, int], sigma: float = 1.0) -> np.ndarray:
    """Granulado branco levemente suavizado, média 0, desvio ~1."""
    n = rng.standard_normal(shape, dtype=np.float32)
    if sigma > 0:
        # Box blur 3x3 repetido aproxima uma gaussiana barata.
        for _ in range(max(1, int(round(sigma)))):
            n = (
                n
                + np.roll(n, 1, 0)
                + np.roll(n, -1, 0)
                + np.roll(n, 1, 1)
                + np.roll(n, -1, 1)
            ) / 5.0
        n /= max(n.std(), 1e-6)
    return n.astype(np.float32)
