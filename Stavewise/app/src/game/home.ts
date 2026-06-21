// Tela inicial (menu): o jogador escolhe entre continuar o último jogo ou começar
// um novo. Mostra "Continue" só quando há progresso salvo; senão, só "New game".
// Overlay sobre o #app, no estilo da splash; resolve a Promise com a escolha.

export type HomeChoice = "new" | "continue"

export interface SavedInfo {
  level: number
  music: string
}

export function showHome(host: HTMLElement, saved: SavedInfo | null): Promise<HomeChoice> {
  return new Promise((resolve) => {
    const screen = document.createElement("div")
    screen.id = "home"

    const brand = document.createElement("div")
    brand.className = "home-brand"
    brand.textContent = "Stavewise"

    const menu = document.createElement("div")
    menu.className = "home-menu"

    const choose = (choice: HomeChoice) => {
      screen.classList.add("hide")
      const done = () => {
        screen.remove()
        resolve(choice)
      }
      screen.addEventListener("transitionend", done, { once: true })
      setTimeout(done, 600) // rede de segurança
    }

    if (saved) {
      const cont = makeButton("Continue", `Level ${saved.level} · ${saved.music}`, "primary")
      cont.addEventListener("pointerdown", () => choose("continue"))
      const fresh = makeButton("New game", "Start over from level 1", "ghost")
      fresh.addEventListener("pointerdown", () => choose("new"))
      menu.append(cont, fresh)
    } else {
      const fresh = makeButton("New game", "Start from level 1", "primary")
      fresh.addEventListener("pointerdown", () => choose("new"))
      menu.append(fresh)
    }

    screen.append(brand, menu)
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
