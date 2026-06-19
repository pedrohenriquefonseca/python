// Trava de orientação em PAISAGEM via @capacitor/screen-orientation.
//
// No app nativo (iOS/Android) força e mantém paisagem. No preview/web o plugin
// não trava de verdade (o navegador não permite fora de fullscreen), então a
// chamada falha em silêncio — o letterbox do CSS já cuida do aspecto ali.
import { ScreenOrientation } from "@capacitor/screen-orientation"

export async function lockLandscape(): Promise<void> {
  try {
    await ScreenOrientation.lock({ orientation: "landscape" })
  } catch {
    // sem suporte (web/preview) — ignorado de propósito
  }
}
