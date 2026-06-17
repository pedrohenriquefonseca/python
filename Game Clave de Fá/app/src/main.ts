import "./style.css"
import { applyThemeVars } from "./theme"
import { Game } from "./game/Game"

applyThemeVars()

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
game.start()

if (import.meta.env.DEV) {
  ;(globalThis as unknown as { __game: Game }).__game = game
}
