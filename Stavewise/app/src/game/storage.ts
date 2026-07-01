// Progresso do jogo persistido entre sessões: nível atual (p/ "continuar") e maior
// nível liberado (porta de domínio). Sem estrelas/recorde de propósito — o jogo é
// simples e o foco é aprendizado, não pontuação. Usa localStorage, que persiste na
// WKWebView do app nativo; isolado aqui para trocar por @capacitor/preferences
// depois sem mexer no resto.

export interface Progress {
  level: number // nível atual (continuar de onde parou)
  unlocked: number // maior nível liberado e jogável no level select
}

const KEY = "stavewise.progress.v1"
const MAX_LEVEL = 12

// Normaliza dados crus (e saves antigos com campos que não existem mais, ex.
// `stars`): sem `unlocked`, libera só até o nível salvo.
function normalize(raw: Partial<Progress> | null): Progress | null {
  if (!raw || typeof raw.level !== "number" || !Number.isFinite(raw.level)) return null
  return {
    level: raw.level,
    unlocked: typeof raw.unlocked === "number" && Number.isFinite(raw.unlocked) ? raw.unlocked : raw.level,
  }
}

export function loadProgress(): Progress | null {
  try {
    const raw = localStorage.getItem(KEY)
    if (!raw) return null
    return normalize(JSON.parse(raw) as Partial<Progress>)
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

// Maior nível liberado (1 quando não há progresso): o teto do level select.
export function unlockedLevel(): number {
  return loadProgress()?.unlocked ?? 1
}

// Atualiza o nível atual ("continuar") preservando o liberado.
export function saveCurrentLevel(level: number): void {
  const cur = loadProgress()
  saveProgress({
    level,
    unlocked: Math.max(cur?.unlocked ?? level, level),
  })
}

// Libera um nível (ao dominar o anterior nas 3 velocidades), sem ultrapassar o
// último nem mexer no nível atual — quem avança é o jogo.
export function unlockLevel(n: number): void {
  const cur = loadProgress()
  const level = cur?.level ?? n
  saveProgress({
    level,
    unlocked: Math.max(cur?.unlocked ?? n, Math.min(MAX_LEVEL, n)),
  })
}
