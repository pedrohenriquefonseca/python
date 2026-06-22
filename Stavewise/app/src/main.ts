import "./style.css"
import { applyThemeVars } from "./theme"
import { Game } from "./game/Game"
import { lockLandscape } from "./game/orientation"
import { showSplash } from "./game/splash"
import { showHome } from "./game/home"
import { showLevelSelect } from "./game/levelSelect"
import { showGameOver } from "./game/gameOver"
import { loadProgress, clearProgress } from "./game/storage"
import { levelByNumber } from "./game/levels"

applyThemeVars()
void lockLandscape() // app nativo: trava em paisagem (no-op no preview/web)

const app = document.querySelector<HTMLDivElement>("#app")
if (!app) throw new Error("Elemento #app não encontrado")

app.innerHTML = `
  <div id="stage"><canvas id="playfield"></canvas></div>
  <div id="controls"></div>
`

const canvas = document.querySelector<HTMLCanvasElement>("#playfield")
const controls = document.querySelector<HTMLDivElement>("#controls")
if (!canvas || !controls) throw new Error("Canvas ou controles não encontrados")

const game = new Game(canvas, controls)

// Tela inicial: o jogador continua o último jogo, começa um novo, ou escolhe um
// nível qualquer (1–12). Carrega a fase escolhida e inicia o jogo.
async function menu(): Promise<void> {
  for (;;) {
    const saved = loadProgress()
    const choice = await showHome(app!, saved ? { level: saved.level, music: levelByNumber(saved.level).music } : null)

    if (choice === "continue") {
      const current = loadProgress()
      if (current) game.loadLevel(current.level)
      break
    }
    if (choice === "new") {
      clearProgress()
      game.loadLevel(1)
      break
    }
    // "levels": abre a grade; null = voltou ao menu (repete o laço).
    const level = await showLevelSelect(app!)
    if (level == null) continue
    clearProgress()
    game.loadLevel(level)
    break
  }
  game.start()
}

// Ao zerar as vidas: tela de game over → recomeçar a fase, ou voltar ao menu.
game.onGameOver = async () => {
  const choice = await showGameOver(app!, {
    level: game.currentLevel,
    music: levelByNumber(game.currentLevel).music,
  })
  if (choice === "retry") {
    game.retryLevel()
  } else {
    game.stop()
    await menu()
  }
}

// Fluxo de entrada: splash "Waveform" → tela inicial → jogo. O toque que dispensa
// a splash também destrava o áudio na WKWebView.
async function enter(): Promise<void> {
  await showSplash(app!)
  await menu()
}

void enter()

if (import.meta.env.DEV) {
  ;(globalThis as unknown as { __game: Game }).__game = game
}
