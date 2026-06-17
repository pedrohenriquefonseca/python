"""Tabela de posições de vara do trombone tenor (clave de fá).

Cada nota escrita (ao tom real) corresponde a uma posição de vara de 1 a 7,
conforme a fundamental da série harmônica:

    1ª — Sib  (vara recolhida)
    2ª — Lá
    3ª — Láb
    4ª — Sol
    5ª — Solb / Fá#
    6ª — Fá
    7ª — Mi   (vara estendida)

A tabela cobre o registro E2 (MIDI 40) até C5 (MIDI 72), que é a faixa
prática do trombone tenor. As notas são indexadas por número MIDI, então
qualquer enarmonia (Fá# = Solb, etc.) cai na mesma posição automaticamente.
"""

from __future__ import annotations

# MIDI 40 (E2) .. MIDI 72 (C5). Índice = midi - 40.
# Fonte: "Trombone tenor — posições de vara em clave de fá".
_POSITIONS: tuple[int, ...] = (
    7,  # 40  E2
    6,  # 41  F2
    5,  # 42  Gb2 / F#2
    4,  # 43  G2
    3,  # 44  Ab2 / G#2
    2,  # 45  A2
    1,  # 46  Bb2 / A#2
    7,  # 47  B2
    6,  # 48  C3
    5,  # 49  Db3 / C#3
    4,  # 50  D3
    3,  # 51  Eb3 / D#3
    2,  # 52  E3
    1,  # 53  F3
    5,  # 54  Gb3 / F#3
    4,  # 55  G3
    3,  # 56  Ab3 / G#3
    2,  # 57  A3
    1,  # 58  Bb3 / A#3
    4,  # 59  B3
    3,  # 60  C4
    2,  # 61  Db4 / C#4
    1,  # 62  D4
    3,  # 63  Eb4 / D#4
    2,  # 64  E4
    1,  # 65  F4
    5,  # 66  Gb4 / F#4
    4,  # 67  G4
    3,  # 68  Ab4 / G#4
    2,  # 69  A4
    1,  # 70  Bb4 / A#4
    2,  # 71  B4
    1,  # 72  C5
)

LOWEST_MIDI = 40   # E2
HIGHEST_MIDI = 72  # C5

_NOTE_NAMES = {
    "C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3,
    "E": 4, "FB": 4, "F": 5, "E#": 5, "F#": 6, "GB": 6,
    "G": 7, "G#": 8, "AB": 8, "A": 9, "A#": 10, "BB": 10,
    "B": 11, "CB": 11,
}


def position_for_midi(midi: int) -> int | None:
    """Posição de vara (1-7) para um número MIDI, ou None se fora da faixa."""
    if LOWEST_MIDI <= midi <= HIGHEST_MIDI:
        return _POSITIONS[midi - LOWEST_MIDI]
    return None


def name_to_midi(name: str) -> int:
    """Converte um nome de nota como 'Bb3', 'F#4', 'C5' em número MIDI.

    Convenção: C4 = 60 (dó central / middle C).
    """
    s = name.strip().replace("♭", "b").replace("♯", "#")
    i = 1
    while i < len(s) and (s[i] in "#b"):
        i += 1
    pitch = s[:i].upper()
    octave = int(s[i:])
    if pitch not in _NOTE_NAMES:
        raise ValueError(f"Nota desconhecida: {name!r}")
    return _NOTE_NAMES[pitch] + (octave + 1) * 12


def position_for_name(name: str) -> int | None:
    """Posição de vara (1-7) para um nome de nota, ou None se fora da faixa."""
    return position_for_midi(name_to_midi(name))


if __name__ == "__main__":
    # Autoteste: confere a tabela inteira contra a referência do PDF.
    reference = {
        "E2": 7, "F2": 6, "Gb2": 5, "G2": 4, "Ab2": 3, "A2": 2, "Bb2": 1,
        "B2": 7, "C3": 6, "Db3": 5, "D3": 4,
        "Eb3": 3, "E3": 2, "F3": 1, "Gb3": 5, "G3": 4, "Ab3": 3, "A3": 2,
        "Bb3": 1, "B3": 4, "C4": 3,
        "Db4": 2, "D4": 1, "Eb4": 3, "E4": 2, "F4": 1, "Gb4": 5, "G4": 4,
        "Ab4": 3, "A4": 2, "Bb4": 1, "B4": 2, "C5": 1,
    }
    ok = True
    for note, expected in reference.items():
        got = position_for_name(note)
        flag = "ok" if got == expected else "ERRO"
        if got != expected:
            ok = False
        print(f"  {note:>4}  ->  {got}   (esperado {expected})  {flag}")
    # Enarmonia: F#3 deve dar o mesmo que Gb3.
    assert position_for_name("F#3") == position_for_name("Gb3") == 5
    assert position_for_name("C#4") == position_for_name("Db4") == 2
    print()
    print("Todas as posições conferem." if ok else "HÁ DIVERGÊNCIAS!")
