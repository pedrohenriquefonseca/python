import "./style.css"
import { applyThemeVars } from "./theme"
import { Game } from "./game/Game"
import { lockLandscape } from "./game/orientation"
import { showSplash } from "./game/splash"
import { showHome } from "./game/home"
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

// Fluxo de entrada: splash "Waveform" → tela inicial (novo jogo / continuar) → jogo.
// O toque que dispensa a splash também destrava o áudio na WKWebView.
void showSplash(app)
  .then(() => {
    const saved = loadProgress()
    return showHome(app, saved ? { level: saved.level, music: levelByNumber(saved.level).music } : null)
  })
  .then((choice) => {
    if (choice === "continue") {
      const saved = loadProgress()
      if (saved) game.loadLevel(saved.level)
    } else {
      clearProgress()
      game.loadLevel(1)
    }
    game.start()
  })

if (import.meta.env.DEV) {
  ;(globalThis as unknown as { __game: Game }).__game = game
}
