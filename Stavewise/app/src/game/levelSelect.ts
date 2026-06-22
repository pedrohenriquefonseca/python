// Seleção de nível: grade com os 12 níveis (número + música liberada). O jogador
// pode começar em qualquer um. Overlay sobre o #app, no estilo do menu; resolve
// com o número do nível escolhido, ou null se voltar para a tela inicial.

import { LEVELS } from "./levels"

export function showLevelSelect(host: HTMLElement): Promise<number | null> {
  return new Promise((resolve) => {
    const screen = document.createElement("div")
    screen.id = "levels"

    const header = document.createElement("div")
    header.className = "levels-header"
    const back = document.createElement("button")
    back.className = "levels-back"
    back.textContent = "‹ Back"
    const title = document.createElement("div")
    title.className = "levels-title"
    title.textContent = "Choose a level"
    header.append(back, title)

    const grid = document.createElement("div")
    grid.className = "levels-grid"

    const finish = (value: number | null) => {
      screen.classList.add("hide")
      const done = () => {
        screen.remove()
        resolve(value)
      }
      screen.addEventListener("transitionend", done, { once: true })
      setTimeout(done, 600) // rede de segurança
    }

    back.addEventListener("pointerdown", () => finish(null))

    for (const lv of LEVELS) {
      const tile = document.createElement("button")
      tile.className = "level-tile"

      const num = document.createElement("span")
      num.className = "level-tile-num"
      num.textContent = String(lv.n)

      const music = document.createElement("span")
      music.className = "level-tile-music"
      music.textContent = lv.music

      tile.append(num, music)
      tile.addEventListener("pointerdown", () => finish(lv.n))
      grid.appendChild(tile)
    }

    screen.append(header, grid)
    host.appendChild(screen)
  })
}
