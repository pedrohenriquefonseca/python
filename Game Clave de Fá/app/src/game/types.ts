export interface Note {
  midi: number
  x: number
  positions: number[]
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
