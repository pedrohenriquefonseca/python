export interface Note {
  midi: number
  x: number
  positions: number[]
  judged: boolean
  state: "live" | "missed"
  alpha: number
}
