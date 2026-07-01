// Tela de fim de NÍVEL (dominado nas 3 velocidades — Largo→Adagio→Andante): libera
// e avança para o próximo. Sem estrelas/recorde. Fundo sólido e escala grande, no
// mesmo estilo da home/splash. A tela intermediária "vamos acelerar" (entre uma
// velocidade e outra, dentro do MESMO nível) é outra — ver speedUp.ts.

export interface LevelResult {
  level: number
  music: string
  accuracy: number // fração 0..1 de acertos na fase (na última velocidade)
}

export type LevelCompleteChoice = "next" | "home"

export function showLevelComplete(
  host: HTMLElement,
  result: LevelResult,
  isLast: boolean,
): Promise<LevelCompleteChoice> {
  return new Promise((resolve) => {
    const screen = document.createElement("div")
    screen.id = "levelcomplete"

    const title = document.createElement("div")
    title.className = "eo-title"
    title.textContent = isLast ? "Você conseguiu!" : "Nível completo!"

    const sub = document.createElement("div")
    sub.className = "eo-sub"
    sub.textContent = `Level ${result.level} · ${result.music} · ${Math.round(result.accuracy * 100)}%`

    const menu = document.createElement("div")
    menu.className = "eo-menu"

    const choose = (choice: LevelCompleteChoice) => {
      screen.classList.add("hide")
      const done = () => {
        screen.remove()
        resolve(choice)
      }
      screen.addEventListener("transitionend", done, { once: true })
      setTimeout(done, 600) // rede de segurança
    }

    const next = makeButton(isLast ? "Jogar de novo" : "Next level", isLast ? "Level 12 outra vez" : `Level ${result.level + 1}`, "primary")
    next.addEventListener("pointerdown", () => choose("next"))
    const home = makeButton("Home", "Voltar ao menu", "ghost")
    home.addEventListener("pointerdown", () => choose("home"))
    menu.append(next, home)

    screen.append(title, sub, menu)
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
