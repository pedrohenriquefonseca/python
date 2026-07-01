// Tela inicial (menu): o jogador escolhe entre continuar o último jogo ou começar
// um novo. Mostra "Continue" só quando há progresso salvo; senão, só "New game".
// Overlay sobre o #app, no estilo da splash; resolve a Promise com a escolha.

import { buildWave } from "./wave"

export type HomeChoice = "new" | "continue" | "levels"

export interface SavedInfo {
  level: number
  music: string
}

export function showHome(host: HTMLElement, saved: SavedInfo | null): Promise<HomeChoice> {
  return new Promise((resolve) => {
    const screen = document.createElement("div")
    screen.id = "home"

    // Layout horizontal (paisagem): marca + tagline à esquerda, menu à direita.
    const left = document.createElement("div")
    left.className = "home-left"
    const brand = document.createElement("div")
    brand.className = "home-brand"
    brand.textContent = "Stavewise"
    const tag = document.createElement("div")
    tag.className = "home-tag"
    tag.textContent = "Read it · play it"
    left.append(brand, tag)

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

    const pick = makeButton("Choose a level", "Jump to any of the 12", "ghost")
    pick.addEventListener("pointerdown", () => choose("levels"))

    const right = document.createElement("div")
    right.className = "home-right"
    right.append(menu, pick)

    const row = document.createElement("div")
    row.className = "home-row"
    row.append(left, right)

    screen.append(row, buildWave())
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
