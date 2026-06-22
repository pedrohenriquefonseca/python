// Tela de game over: recomeçar a fase atual do zero (Continue), ou voltar para a
// tela inicial (Home). Overlay translúcido leve sobre o #app — a pauta congelada
// fica esmaecida atrás. Título pequeno e botões compactos. Resolve com a escolha.

export type GameOverChoice = "retry" | "home"

export interface GameOverInfo {
  level: number
  music: string
}

export function showGameOver(host: HTMLElement, info: GameOverInfo): Promise<GameOverChoice> {
  return new Promise((resolve) => {
    const screen = document.createElement("div")
    screen.id = "gameover"

    const head = document.createElement("div")
    head.className = "gameover-head"
    const title = document.createElement("div")
    title.className = "gameover-title"
    title.textContent = "Game over"
    const sub = document.createElement("div")
    sub.className = "gameover-sub"
    sub.textContent = `Level ${info.level} · ${info.music}`
    head.append(title, sub)

    const row = document.createElement("div")
    row.className = "gameover-row"

    const choose = (choice: GameOverChoice) => {
      screen.classList.add("hide")
      const done = () => {
        screen.remove()
        resolve(choice)
      }
      screen.addEventListener("transitionend", done, { once: true })
      setTimeout(done, 600) // rede de segurança
    }

    const cont = makeButton("Continue", "primary")
    cont.addEventListener("pointerdown", () => choose("retry"))
    const home = makeButton("Home", "ghost")
    home.addEventListener("pointerdown", () => choose("home"))
    row.append(cont, home)

    screen.append(head, row)
    host.appendChild(screen)
  })
}

function makeButton(label: string, variant: "primary" | "ghost"): HTMLButtonElement {
  const button = document.createElement("button")
  button.className = `go-btn ${variant}`
  button.textContent = label
  return button
}
