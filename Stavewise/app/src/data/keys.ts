// Armaduras (key signatures) para CLAVE DE FÁ.
//
// A referência clássica do ciclo de quintas costuma aparecer em clave de sol;
// aqui as posições já estão TRANSPOSTAS para a clave de fá (a linha do meio da
// pauta é o ré³). Cada acidente é fixado na linha/espaço do seu próprio nome de
// nota, no registro convencional que mantém a armadura compacta no centro da
// pauta. As posições são dadas como o MIDI da nota *natural* cuja linha/espaço o
// glifo ocupa — o render usa o mesmo `noteY` das notas para alinhar tudo.

// Teto de acidentes do jogo (bemóis ou sustenidos). A partir daqui o ciclo de
// quintas não avança — decisão de jogo (jun/2026). O módulo sabe desenhar até 7,
// mas a jogabilidade fica em ±5.
export const MAX_ACCIDENTALS = 5

export type AccidentalSymbol = "♯" | "♭"

export interface Accidental {
  midi: number // nota natural cuja linha/espaço o glifo ocupa
  symbol: AccidentalSymbol
}

// Ordem dos sustenidos (Fá Dó Sol Ré Lá Mi Si) em clave de fá:
//   F3=53  C3=48  G3=55  D3=50  A2=45  E3=52  B2=47
const SHARP_ORDER = [53, 48, 55, 50, 45, 52, 47]

// Ordem dos bemóis (Si Mi Lá Ré Sol Dó Fá) em clave de fá:
//   B2=47  E3=52  A2=45  D3=50  G2=43  C3=48  F2=41
const FLAT_ORDER = [47, 52, 45, 50, 43, 48, 41]

// `fifths`: +n = n sustenidos, -n = n bemóis, 0 = Dó maior (sem armadura).
export function accidentalsForKey(fifths: number): Accidental[] {
  if (fifths > 0) {
    return SHARP_ORDER.slice(0, Math.min(fifths, 7)).map((midi) => ({ midi, symbol: "♯" }))
  }
  if (fifths < 0) {
    return FLAT_ORDER.slice(0, Math.min(-fifths, 7)).map((midi) => ({ midi, symbol: "♭" }))
  }
  return []
}

const SHARP_NAMES = ["C", "G", "D", "A", "E", "B", "F♯", "C♯"]
const FLAT_NAMES = ["C", "F", "B♭", "E♭", "A♭", "D♭", "G♭", "C♭"]

export function keyName(fifths: number): string {
  if (fifths === 0) return "C major"
  const count = Math.abs(fifths)
  const name = fifths > 0 ? SHARP_NAMES[Math.min(fifths, 7)] : FLAT_NAMES[Math.min(count, 7)]
  const sym = fifths > 0 ? "♯" : "♭"
  return `${name} major (${count}${sym})`
}

const pitchClass = (midi: number): number => ((midi % 12) + 12) % 12

// Semitom que a armadura aplica à LETRA da nota: -1 (♭), +1 (♯) ou 0. A nota é
// sempre desenhada na sua linha/espaço natural; a armadura altera a altura soante.
export function keyAccidental(midi: number, fifths: number): number {
  if (fifths === 0) return 0
  const pc = pitchClass(midi)
  for (const acc of accidentalsForKey(fifths)) {
    if (pitchClass(acc.midi) === pc) return acc.symbol === "♯" ? 1 : -1
  }
  return 0
}

// Altura soante de uma nota natural sob a armadura — usada para achar a posição
// de vara correta (ex.: si em Fá maior soa si♭, indo para a 1ª/5ª posição).
export function soundingMidi(midi: number, fifths: number): number {
  return midi + keyAccidental(midi, fifths)
}
