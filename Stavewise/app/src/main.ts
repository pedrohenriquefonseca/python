import "./style.css"
import { applyThemeVars } from "./theme"
import { Game } from "./game/Game"
import { lockLandscape } from "./game/orientation"
import { showSplash } from "./game/splash"
import { showHome } from "./game/home"
import { showLevelSelect } from "./game/levelSelect"
import { showGameOver } from "./game/gameOver"
import { showLevelComplete } from "./game/levelComplete"
import { showTutorial } from "./game/tutorial"
import { loadProgress, clearProgress } from "./game/storage"
import { levelByNumber, LEVELS } from "./game/levels"

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
      // O tutorial aparece somente ao começar um jogo novo.
      await showTutorial(app!)
      break
    }
    // "levels": abre a grade (só níveis liberados); null = voltou ao menu (repete o
    // laço). Escolher um nível preserva liberados/estrelas — só muda onde se joga.
    const level = await showLevelSelect(app!)
    if (level == null) continue
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

// Ao resolver a cota de notas: tela de fim de fase. Dominou → avançar (ou repetir/
// menu); não dominou → tentar de novo (ou menu). "Next" só existe se houver próximo.
game.onLevelComplete = async (result) => {
  const isLast = result.level >= LEVELS.length
  const choice = await showLevelComplete(app!, result, isLast)
  if (choice === "next") {
    game.advanceLevel()
  } else if (choice === "retry") {
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
