import { nameToMidi } from "../data/slidePositions"

// Os 12 níveis como DADOS (ver docs/03-progressao-de-dificuldade.md). O âmbito
// (notePool) cresce de dó³ ré³ mi³ até dó³–sol⁴ e a armadura (keySig em quintas,
// negativo = bemóis) entra distribuída. O intervalo min..max do pool é o que
// redimensiona a pauta: níveis 1–6 cabem nas 5 linhas (pauta compacta); a 2ª
// oitava (níveis 7–8+) abre linhas suplementares acima e a pauta encolhe sozinha.

export interface Level {
  n: number // número do nível (1-based)
  notePool: number[] // notas em jogo (MIDI)
  keySig: number // armadura em quintas: 0=Dó, -1=Fá, -2=Si♭, -3=Mi♭, -4=Lá♭
  music: string // tema/música liberada no nível
}

const pool = (...names: string[]): number[] => names.map(nameToMidi)

const TO_A3 = ["C3", "D3", "E3", "F3", "G3", "A3", "B3"]
const TO_G4 = [...TO_A3, "C4", "D4", "E4", "F4", "G4"]

export const LEVELS: Level[] = [
  { n: 1, keySig: 0, music: "Hot Cross Buns", notePool: pool("C3", "D3", "E3") },
  { n: 2, keySig: 0, music: "Ode to Joy", notePool: pool("C3", "D3", "E3", "F3", "G3") },
  { n: 3, keySig: 0, music: "Twinkle Twinkle", notePool: pool("C3", "D3", "E3", "F3", "G3", "A3") },
  { n: 4, keySig: 0, music: "London Bridge", notePool: pool(...TO_A3) },
  { n: 5, keySig: -1, music: "F major theme", notePool: pool(...TO_A3) },
  { n: 6, keySig: -2, music: "Silent Night", notePool: pool(...TO_A3) },
  { n: 7, keySig: -2, music: "Upper octave", notePool: pool(...TO_A3, "C4", "D4") },
  { n: 8, keySig: -2, music: "When the Saints", notePool: pool(...TO_G4) },
  { n: 9, keySig: -3, music: "Eb major theme", notePool: pool(...TO_G4) },
  { n: 10, keySig: -3, music: "Samba / choro", notePool: pool(...TO_G4) },
  { n: 11, keySig: -4, music: "Ab major theme", notePool: pool(...TO_G4) },
  { n: 12, keySig: 0, music: "Free play", notePool: pool(...TO_G4) },
]

export function levelByNumber(n: number): Level {
  const i = Math.max(1, Math.min(LEVELS.length, n)) - 1
  return LEVELS[i]
}
