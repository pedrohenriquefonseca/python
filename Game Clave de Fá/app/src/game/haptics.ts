// Feedback tátil via @capacitor/haptics — Taptic Engine no app iOS/Android.
// - hapticHit: impacto LEVE no acerto.
// - hapticMiss: impacto FORTE (Heavy) no erro — uma batida seca e abrupta.
//
// No app nativo usa o Taptic Engine de verdade. No preview/web o plugin cai
// para navigator.vibrate (aproximação). Chamadas são fire-and-forget: erros são
// engolidos para nunca interromper o gameplay.

import { Haptics, ImpactStyle } from "@capacitor/haptics"

export function hapticHit(): void {
  void Haptics.impact({ style: ImpactStyle.Light }).catch(() => {})
}

export function hapticMiss(): void {
  void Haptics.impact({ style: ImpactStyle.Heavy }).catch(() => {})
}
