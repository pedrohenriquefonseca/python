// Progresso do jogo persistido entre sessões: nível atual (p/ "continuar"), maior
// nível liberado (porta de domínio) e as melhores estrelas por nível. Usa
// localStorage, que persiste na WKWebView do app nativo; isolado aqui para trocar
// por @capacitor/preferences depois sem mexer no resto.

export interface Progress {
  level: number // nível atual (continuar de onde parou)
  unlocked: number // maior nível liberado e jogável no level select
  stars: Record<number, number> // melhor nº de estrelas (0–3) por nível
}

const KEY = "stavewise.progress.v1"
const MAX_LEVEL = 12

// Normaliza dados crus (e saves antigos que só tinham `level`): sem `unlocked`,
// libera só até o nível salvo; sem `stars`, mapa vazio.
function normalize(raw: Partial<Progress> | null): Progress | null {
  if (!raw || typeof raw.level !== "number" || !Number.isFinite(raw.level)) return null
  return {
    level: raw.level,
    unlocked: typeof raw.unlocked === "number" && Number.isFinite(raw.unlocked) ? raw.unlocked : raw.level,
    stars: raw.stars && typeof raw.stars === "object" ? raw.stars : {},
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

// Atualiza o nível atual ("continuar") preservando liberados e estrelas.
export function saveCurrentLevel(level: number): void {
  const cur = loadProgress()
  saveProgress({
    level,
    unlocked: Math.max(cur?.unlocked ?? level, level),
    stars: cur?.stars ?? {},
  })
}

// Registra o domínio de um nível: guarda a melhor pontuação de estrelas e libera o
// próximo (sem ultrapassar o último). Não mexe no nível atual — quem avança é o jogo.
export function recordMastery(level: number, stars: number): void {
  const cur = loadProgress()
  const best = Math.max(cur?.stars?.[level] ?? 0, stars)
  saveProgress({
    level: cur?.level ?? level,
    unlocked: Math.max(cur?.unlocked ?? level, Math.min(MAX_LEVEL, level + 1)),
    stars: { ...(cur?.stars ?? {}), [level]: best },
  })
}
