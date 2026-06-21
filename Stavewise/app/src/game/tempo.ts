// Andamentos: 3 velocidades por exercício. Color-coded por dificuldade.
// Ver docs/03-progressao-de-dificuldade.md.
export type TempoId = "largo" | "adagio" | "andante"

export interface Tempo {
  id: TempoId
  name: string
  bpm: number
  color: string
}

export const TEMPOS: Tempo[] = [
  { id: "largo", name: "Largo", bpm: 40, color: "#3FA66B" }, // iniciante — verde
  { id: "adagio", name: "Adagio", bpm: 66, color: "#159E91" }, // fácil — teal
  { id: "andante", name: "Andante", bpm: 92, color: "#EFA12A" }, // domínio — âmbar
]

export function tempoById(id: TempoId): Tempo {
  return TEMPOS.find((t) => t.id === id) ?? TEMPOS.find((t) => t.id === "andante")!
}
