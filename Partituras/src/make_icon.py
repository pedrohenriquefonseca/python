"""Gera o ícone do app: trombone de latão sobre fundo verde-petróleo.

Desenha em vetor via AppKit (mesmas curvas do mockup aprovado) e salva o
master 1024×1024 em resources/icon_1024.png. O .icns é montado depois com
sips + iconutil (ver __main__).
"""

from __future__ import annotations

import os

from AppKit import (
    NSBezierPath,
    NSBitmapImageRep,
    NSColor,
    NSImage,
    NSMakeRect,
    NSPNGFileType,
)

S = 1024 / 240  # o desenho foi projetado num grid de 240
TEAL = NSColor.colorWithSRGBRed_green_blue_alpha_(0.078, 0.267, 0.235, 1.0)
BRASS = NSColor.colorWithSRGBRed_green_blue_alpha_(0.910, 0.651, 0.259, 1.0)


def _pt(x: float, y: float) -> tuple[float, float]:
    """Converte do grid 240 (y p/ baixo, como no SVG) p/ pontos AppKit."""
    return x * S, (240 - y) * S


def draw_icon() -> NSImage:
    img = NSImage.alloc().initWithSize_((1024, 1024))
    img.lockFocus()

    # fundo: squircle verde-petróleo
    TEAL.set()
    NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
        NSMakeRect(8 * S, 8 * S, 224 * S, 224 * S), 50 * S, 50 * S).fill()

    BRASS.set()

    # campana (cone que flare p/ a direita) — preenchida
    bell = NSBezierPath.bezierPath()
    bell.moveToPoint_(_pt(85, 95))
    bell.curveToPoint_controlPoint1_controlPoint2_(
        _pt(192, 66), _pt(135, 94), _pt(162, 81))
    bell.lineToPoint_(_pt(192, 136))
    bell.curveToPoint_controlPoint1_controlPoint2_(
        _pt(85, 107), _pt(162, 121), _pt(135, 108))
    bell.closePath()
    bell.fill()

    # bocal
    NSBezierPath.bezierPathWithOvalInRect_(
        NSMakeRect((40 - 10) * S, (240 - 101 - 10) * S, 20 * S, 20 * S)).fill()

    def tube(width: float) -> NSBezierPath:
        p = NSBezierPath.bezierPath()
        p.setLineWidth_(width * S)
        p.setLineCapStyle_(1)  # round
        return p

    # tubo da campana
    p = tube(12)
    p.moveToPoint_(_pt(45, 101))
    p.lineToPoint_(_pt(90, 101))
    p.stroke()

    # volta esquerda (semicírculo)
    p = tube(12)
    p.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_clockwise_(
        _pt(45, 131), 30 * S, 90, 270, False)
    p.stroke()

    # vara: tubo superior
    p = tube(9)
    p.moveToPoint_(_pt(45, 161))
    p.lineToPoint_(_pt(203, 161))
    p.stroke()

    # curva da vara (ponta direita)
    p = tube(9)
    p.appendBezierPathWithArcWithCenter_radius_startAngle_endAngle_clockwise_(
        _pt(203, 174), 13 * S, 90, 270, True)
    p.stroke()

    # vara: tubo inferior
    p = tube(9)
    p.moveToPoint_(_pt(203, 187))
    p.lineToPoint_(_pt(62, 187))
    p.stroke()

    img.unlockFocus()
    return img


def save_png(img: NSImage, path: str) -> None:
    rep = NSBitmapImageRep.imageRepWithData_(img.TIFFRepresentation())
    rep.representationUsingType_properties_(NSPNGFileType, None) \
       .writeToFile_atomically_(path, True)


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "resources")
    os.makedirs(out, exist_ok=True)
    dest = os.path.abspath(os.path.join(out, "icon_1024.png"))
    save_png(draw_icon(), dest)
    print(dest)
