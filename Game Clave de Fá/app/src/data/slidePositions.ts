// Porte validado de ../../Partituras/src/slide_positions.py
// Trombone tenor reto, clave de fá. Índice = midi - 40 (E2 .. C5).

const POSITIONS: number[] = [
  7, 6, 5, 4, 3, 2, 1, // 40-46  E2 F2 Gb2 G2 Ab2 A2 Bb2
  7, 6, 5, 4, // 47-50  B2 C3 Db3 D3
  3, 2, 1, 5, 4, 3, 2, // 51-57  Eb3 E3 F3 Gb3 G3 Ab3 A3
  1, 4, 3, // 58-60  Bb3 B3 C4
  2, 1, 3, 2, 1, 5, 4, // 61-67  Db4 D4 Eb4 E4 F4 Gb4 G4
  3, 2, 1, 2, 1, // 68-72  Ab4 A4 Bb4 B4 C5
]

export const LOWEST_MIDI = 40 // E2
export const HIGHEST_MIDI = 72 // C5

// Posições ALTERNATIVAS conhecidas (partials mais agudos), a validar.
// Ver docs/02-input-e-posicoes-vara.md.
const ALTERNATES: Record<number, number[]> = {
  52: [7], // E3: 2 (principal) + 7
  53: [6], // F3: 1 + 6
  58: [5], // Bb3: 1 + 5
  60: [6], // C4: 3 + 6
  65: [6], // F4: 1 + 6
}

export function positionForMidi(midi: number): number | null {
  if (midi < LOWEST_MIDI || midi > HIGHEST_MIDI) return null
  return POSITIONS[midi - LOWEST_MIDI]
}

export function validPositionsForMidi(midi: number): number[] {
  const primary = positionForMidi(midi)
  if (primary === null) return []
  const alts = ALTERNATES[midi] ?? []
  return [primary, ...alts]
}

const NOTE_NAMES: Record<string, number> = {
  C: 0, "C#": 1, DB: 1, D: 2, "D#": 3, EB: 3, E: 4, FB: 4,
  F: 5, "E#": 5, "F#": 6, GB: 6, G: 7, "G#": 8, AB: 8,
  A: 9, "A#": 10, BB: 10, B: 11, CB: 11,
}

// 'Bb3', 'F#4', 'C5' -> número MIDI. Convenção: C4 = 60.
export function nameToMidi(name: string): number {
  const s = name.trim().replace("♭", "b").replace("♯", "#")
  let i = 1
  while (i < s.length && (s[i] === "#" || s[i] === "b")) i++
  const pitch = s.slice(0, i).toUpperCase()
  const octave = parseInt(s.slice(i), 10)
  const semitone = NOTE_NAMES[pitch]
  if (semitone === undefined || Number.isNaN(octave)) {
    throw new Error(`Nota desconhecida: ${name}`)
  }
  return semitone + (octave + 1) * 12
}
