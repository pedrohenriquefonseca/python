// Tela de game over: recomeçar a fase atual do zero (Retry), ou voltar para a
// tela inicial (Home). Fundo sólido e escala grande, no mesmo estilo da home/
// splash (não translúcida — a pauta congelada não precisa aparecer por trás), com
// a mesma waveform decorativa da Home no rodapé. Resolve com a escolha.

import { buildWave } from "./wave"

export type GameOverChoice = "retry" | "home"

export interface GameOverInfo {
  level: number
  music: string
}

export function showGameOver(host: HTMLElement, info: GameOverInfo): Promise<GameOverChoice> {
  return new Promise((resolve) => {
    const screen = document.createElement("div")
    screen.id = "gameover"

    const title = document.createElement("div")
    title.className = "eo-title"
    title.textContent = "Game over"

    const sub = document.createElement("div")
    sub.className = "eo-sub"
    sub.textContent = `Level ${info.level} · ${info.music}`

    const menu = document.createElement("div")
    menu.className = "eo-menu"

    const choose = (choice: GameOverChoice) => {
      screen.classList.add("hide")
      const done = () => {
        screen.remove()
        resolve(choice)
      }
      screen.addEventListener("transitionend", done, { once: true })
      setTimeout(done, 600) // rede de segurança
    }

    const retry = makeButton("Retry", `Level ${info.level} again`, "primary")
    retry.addEventListener("pointerdown", () => choose("retry"))
    const home = makeButton("Home", "Back to menu", "ghost")
    home.addEventListener("pointerdown", () => choose("home"))
    menu.append(retry, home)

    screen.append(title, sub, menu, buildWave())
    host.appendChild(screen)
  })
}

function makeButton(label: string, sub: string, variant: "primary" | "ghost"): HTMLButtonElement {
  const button = document.createElement("button")
  button.className = `home-btn ${variant}`

  const main = document.createElement("span")
  main.className = "home-btn-label"
  main.textContent = label

  const note = document.createElement("span")
  note.className = "home-btn-sub"
  note.textContent = sub

  button.append(main, note)
  return button
}
