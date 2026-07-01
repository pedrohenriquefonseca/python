import type { RhythmId } from "./rhythm"

export interface Note {
  midi: number
  x: number
  positions: number[]
  rhythm: RhythmId // figura rítmica: comanda duração (espaçamento + som) e desenho
}

export interface FloatingLabel {
  text: string
  x: number
  y: number
  life: number
  maxLife: number
  color: string
  size: number
}
