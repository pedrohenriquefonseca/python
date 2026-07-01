// Seleção de nível: grade com os 12 níveis (número + música + estrelas). Só os
// níveis liberados pela porta de domínio são jogáveis; os demais aparecem trancados.
// Overlay sobre o #app, no estilo do menu; resolve com o número do nível escolhido,
// ou null se voltar para a tela inicial.

import { LEVELS } from "./levels"
import { loadProgress } from "./storage"

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

    const progress = loadProgress()
    const unlocked = progress?.unlocked ?? 1
    const stars = progress?.stars ?? {}

    for (const lv of LEVELS) {
      const locked = lv.n > unlocked
      const tile = document.createElement("button")
      tile.className = locked ? "level-tile locked" : "level-tile"
      tile.disabled = locked

      const num = document.createElement("span")
      num.className = "level-tile-num"
      num.textContent = locked ? "🔒" : String(lv.n)

      const music = document.createElement("span")
      music.className = "level-tile-music"
      music.textContent = lv.music

      // Estrelas conquistadas (3 espaços; preenchidas até o melhor resultado).
      const earned = stars[lv.n] ?? 0
      const starRow = document.createElement("span")
      starRow.className = "level-tile-stars"
      for (let i = 1; i <= 3; i++) {
        const star = document.createElement("span")
        star.className = i <= earned ? "lc-star on" : "lc-star"
        star.textContent = "★"
        starRow.appendChild(star)
      }

      tile.append(num, music, starRow)
      if (!locked) tile.addEventListener("pointerdown", () => finish(lv.n))
      grid.appendChild(tile)
    }

    screen.append(header, grid)
    host.appendChild(screen)
  })
}
