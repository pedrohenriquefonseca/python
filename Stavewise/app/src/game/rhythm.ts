// Figuras rítmicas como DADOS: duração (em tempos), se é pausa e o peso de
// amostragem. O motor de ritmo (Game.spawn) sorteia uma figura do rhythmPool do
// nível por estes pesos. A duração comanda três coisas: o espaçamento na pauta
// (nota mais longa nasce mais cedo e ocupa mais espaço), a duração do som no
// acerto e o desenho da figura (cabeça aberta, haste, bandeirola, ponto, pausa).
// Ver docs/03-progressao-de-dificuldade.md (coluna "Ritmo novo").

export type RhythmId = "quarter" | "half" | "eighth" | "dotted" | "rest" | "sixteenth"

export interface RhythmFigure {
  id: RhythmId
  beats: number // duração em tempos (semínima = 1)
  isRest: boolean // pausa: sem altura, não se toca
  weight: number // peso de amostragem quando a figura está liberada no nível
}

// Pesos puxam para a semínima, com variedade ocasional. Pausa e síncopes (colcheia,
// pontuado) entram com peso menor; semicolcheia é rara (só no nível 11).
export const RHYTHMS: Record<RhythmId, RhythmFigure> = {
  quarter: { id: "quarter", beats: 1, isRest: false, weight: 6 },
  half: { id: "half", beats: 2, isRest: false, weight: 3 },
  eighth: { id: "eighth", beats: 0.5, isRest: false, weight: 3 },
  dotted: { id: "dotted", beats: 1.5, isRest: false, weight: 1.5 }, // semínima pontuada
  rest: { id: "rest", beats: 1, isRest: true, weight: 1.5 }, // pausa de semínima
  sixteenth: { id: "sixteenth", beats: 0.25, isRest: false, weight: 1 },
}

// Ordem em que as figuras entram na curva (docs/03). rhythmPool(k) = as primeiras
// k figuras desta ordem — sempre acumulativo.
export const RHYTHM_ORDER: RhythmId[] = ["quarter", "half", "eighth", "dotted", "rest", "sixteenth"]

export function rhythmPool(count: number): RhythmId[] {
  return RHYTHM_ORDER.slice(0, count)
}

// Sorteia uma figura do pool do nível por peso.
export function pickRhythm(pool: RhythmId[]): RhythmFigure {
  const figs = pool.map((id) => RHYTHMS[id])
  const total = figs.reduce((sum, f) => sum + f.weight, 0)
  let r = Math.random() * total
  for (const f of figs) {
    r -= f.weight
    if (r <= 0) return f
  }
  return figs[figs.length - 1]
}
