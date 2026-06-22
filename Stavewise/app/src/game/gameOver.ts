// Tela de game over: recomeçar a fase atual do zero, ou voltar para a tela
// inicial. Overlay translúcido sobre o #app (deixa ver a pauta congelada atrás);
// reaproveita os estilos de botão do menu (.home-btn). Resolve com a escolha.

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
    title.className = "gameover-title"
    title.textContent = "Game over"

    const menu = document.createElement("div")
    menu.className = "home-menu"

    const choose = (choice: GameOverChoice) => {
      screen.classList.add("hide")
      const done = () => {
        screen.remove()
        resolve(choice)
      }
      screen.addEventListener("transitionend", done, { once: true })
      setTimeout(done, 600) // rede de segurança
    }

    const retry = makeButton("Retry level", `Restart level ${info.level} · ${info.music}`, "primary")
    retry.addEventListener("pointerdown", () => choose("retry"))
    const home = makeButton("Home", "Back to the menu", "ghost")
    home.addEventListener("pointerdown", () => choose("home"))
    menu.append(retry, home)

    screen.append(title, menu)
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
