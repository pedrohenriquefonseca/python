// Progresso do jogo persistido entre sessões. Hoje só guarda o nível atual — o
// bastante para "continuar o último jogo". Usa localStorage, que persiste na
// WKWebView do app nativo; isolado aqui para trocar por @capacitor/preferences
// depois sem mexer no resto.

export interface Progress {
  level: number
}

const KEY = "stavewise.progress.v1"

export function loadProgress(): Progress | null {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as Partial<Progress>
    if (typeof parsed?.level === "number" && Number.isFinite(parsed.level)) {
      return { level: parsed.level }
    }
    return null
  } catch {
    return null
  }
}

export function saveProgress(progress: Progress): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(progress))
  } catch {
    // Modo privado/cota cheia: seguimos sem persistir.
  }
}

export function clearProgress(): void {
  try {
    localStorage.removeItem(KEY)
  } catch {
    // ignore
  }
}

export function hasSavedGame(): boolean {
  return loadProgress() !== null
}
