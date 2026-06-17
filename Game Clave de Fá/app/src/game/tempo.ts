// Andamentos: 3 velocidades por exercício. Color-coded por dificuldade.
// Ver docs/03-progressao-de-dificuldade.md.
export type TempoId = "adagio" | "andante" | "allegro"

export interface Tempo {
  id: TempoId
  name: string
  bpm: number
  color: string
}

export const TEMPOS: Tempo[] = [
  { id: "adagio", name: "Adagio", bpm: 66, color: "#159E91" }, // fácil — teal
  { id: "andante", name: "Andante", bpm: 92, color: "#EFA12A" }, // médio — âmbar
  { id: "allegro", name: "Allegro", bpm: 126, color: "#D85A30" }, // difícil — coral
]

export function tempoById(id: TempoId): Tempo {
  return TEMPOS.find((t) => t.id === id) ?? TEMPOS[1]
}
