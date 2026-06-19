export interface Tier {
  name: string
  color: string
  mult: number
}

// Rampa de "heat" do combo. A reconciliar com a paleta — ver docs/06.
export const TIERS: Tier[] = [
  { name: "cold", color: "#8A8FA0", mult: 1 },
  { name: "warming up", color: "#159E91", mult: 1 },
  { name: "in the zone", color: "#378ADD", mult: 2 },
  { name: "hot", color: "#D85A30", mult: 3 },
  { name: "on fire", color: "#EFA12A", mult: 4 },
]

export function tierForCombo(combo: number): Tier {
  if (combo <= 0) return TIERS[0]
  if (combo < 5) return TIERS[1]
  if (combo < 10) return TIERS[2]
  if (combo < 20) return TIERS[3]
  return TIERS[4]
}
