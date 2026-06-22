// Tela inicial (menu): o jogador escolhe entre continuar o último jogo ou começar
// um novo. Mostra "Continue" só quando há progresso salvo; senão, só "New game".
// Overlay sobre o #app, no estilo da splash; resolve a Promise com a escolha.

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

// Waveform decorativa na base da home: equalizador que atravessa a tela de fora a
// fora, com as barras animadas (mesma "respiração" da splash). A cor faz um
// degradê magenta→ciano ao longo da largura e é esmaecida por uma máscara vertical
// (forte no rodapé, dissolvendo para cima). Fica atrás do menu (z-index no CSS).
function buildWave(): HTMLDivElement {
  const wave = document.createElement("div")
  wave.className = "home-wave"

  const N = 34
  const MAG = [255, 46, 136] // --hud (magenta)
  const CY = [25, 227, 214] // --secondary (ciano)
  const mix = (a: number, b: number, t: number) => Math.round(a + (b - a) * t)

  for (let i = 0; i < N; i++) {
    const bar = document.createElement("div")
    bar.className = "home-wave-bar"
    const t = i / (N - 1)
    bar.style.background = `rgb(${mix(MAG[0], CY[0], t)}, ${mix(MAG[1], CY[1], t)}, ${mix(MAG[2], CY[2], t)})`
    const h = 0.42 + 0.58 * Math.abs(Math.sin(i * 0.7 + (i % 4) * 0.45) * Math.cos(i * 0.18))
    bar.style.height = `${Math.max(16, Math.min(100, h * 100))}%`
    // Fases dessincronizadas: a onda "respira" em vez de pulsar em bloco.
    bar.style.animationDelay = `${(i % 7) * -0.13}s`
    bar.style.animationDuration = `${1.1 + (i % 5) * 0.12}s`
    wave.appendChild(bar)
  }
  return wave
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
