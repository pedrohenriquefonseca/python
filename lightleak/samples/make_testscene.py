"""Cena sintética de referência: céu em gradiente, silhueta escura, alta-luz
estourada e uma régua de patches neutros. Serve para julgar como o vazamento
trata pretos, meios-tons e o rolloff de branco.
"""
import numpy as np

from filmfx.imaging import linear_to_srgb, save_rgb

W, H = 1600, 1067
x = np.linspace(0, 1, W, dtype=np.float32)[None, :]
y = np.linspace(0, 1, H, dtype=np.float32)[:, None]
X, Y = np.repeat(x, H, 0), np.repeat(y, W, 1)

sky_top = np.array([0.05, 0.11, 0.28], np.float32)
sky_bot = np.array([0.62, 0.34, 0.16], np.float32)
t = np.clip(Y / 0.62, 0, 1)[..., None] ** 1.4
img = sky_top + (sky_bot - sky_top) * t

sun = np.exp(-(((X - 0.72) * 1.5) ** 2 + ((Y - 0.52) * 1.5) ** 2) / 0.0016)
img += sun[..., None] * np.array([2.4, 2.0, 1.3], np.float32)

hill = 0.63 + 0.06 * np.sin(X * 9.0) + 0.03 * np.sin(X * 23.0 + 1.0)
mask = (Y > hill).astype(np.float32)
rng = np.random.default_rng(3)
tex = 0.5 + 0.5 * np.sin(X * 220) * np.sin(Y * 160)
img = img * (1 - mask[..., None]) + (
    np.array([0.010, 0.012, 0.018], np.float32) * (0.4 + 1.2 * tex[..., None])
) * mask[..., None]

patches = np.array([0.02, 0.06, 0.18, 0.45, 0.80, 1.00], np.float32)
for i, v in enumerate(patches):
    x0, x1 = int(W * (0.06 + i * 0.07)), int(W * (0.115 + i * 0.07))
    y0, y1 = int(H * 0.78), int(H * 0.90)
    img[y0:y1, x0:x1] = v

img += rng.standard_normal(img.shape).astype(np.float32) * 0.004
save_rgb(linear_to_srgb(np.clip(img, 0, None)), "samples/sample02.jpg")
print("ok")
