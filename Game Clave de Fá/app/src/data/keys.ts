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

const SHARP_NAMES = ["Dó", "Sol", "Ré", "Lá", "Mi", "Si", "Fá♯", "Dó♯"]
const FLAT_NAMES = ["Dó", "Fá", "Si♭", "Mi♭", "Lá♭", "Ré♭", "Sol♭", "Dó♭"]

export function keyName(fifths: number): string {
  if (fifths === 0) return "Dó maior"
  const count = Math.abs(fifths)
  const name = fifths > 0 ? SHARP_NAMES[Math.min(fifths, 7)] : FLAT_NAMES[Math.min(count, 7)]
  const sym = fifths > 0 ? "♯" : "♭"
  return `${name} maior (${count}${sym})`
}
