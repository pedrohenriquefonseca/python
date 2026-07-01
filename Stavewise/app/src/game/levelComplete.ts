// Tela de fim de fase: aparece quando a cota de notas do nível é resolvida.
// Domínio (precisão ≥ porta) → estrelas + "Next level". Não dominou → "Almost!" e
// "Try again" na mesma fase. Overlay translúcido sobre a pauta congelada, no estilo
// da tela de game over. Resolve com a escolha do jogador.

export interface LevelResult {
  level: number
  music: string
  mastered: boolean // atingiu a porta de domínio (precisão mínima)?
  stars: number // 0–3 (0 quando não dominou)
  accuracy: number // fração 0..1 de acertos na fase
}

export type LevelCompleteChoice = "next" | "retry" | "home"

export function showLevelComplete(
  host: HTMLElement,
  result: LevelResult,
  isLast: boolean,
): Promise<LevelCompleteChoice> {
  return new Promise((resolve) => {
    const screen = document.createElement("div")
    screen.id = "levelcomplete"

    const head = document.createElement("div")
    head.className = "lc-head"
    const title = document.createElement("div")
    title.className = "lc-title"
    title.textContent = result.mastered ? (isLast ? "You did it!" : "Level complete") : "Almost!"
    const sub = document.createElement("div")
    sub.className = "lc-sub"
    sub.textContent = `Level ${result.level} · ${result.music} · ${Math.round(result.accuracy * 100)}%`
    head.append(title, sub)

    // Fileira de 3 estrelas: preenchidas até `stars`. Sempre exibida (vazia quando
    // não dominou), para o jogador ver o alvo.
    const stars = document.createElement("div")
    stars.className = "lc-stars"
    for (let i = 1; i <= 3; i++) {
      const star = document.createElement("span")
      star.className = i <= result.stars ? "lc-star on" : "lc-star"
      star.textContent = "★"
      stars.appendChild(star)
    }

    const row = document.createElement("div")
    row.className = "lc-row"

    const choose = (choice: LevelCompleteChoice) => {
      screen.classList.add("hide")
      const done = () => {
        screen.remove()
        resolve(choice)
      }
      screen.addEventListener("transitionend", done, { once: true })
      setTimeout(done, 600) // rede de segurança
    }

    // Botões conforme o desfecho. Dominou e há próximo → Next (destaque) + Replay +
    // Home. Dominou o último → Replay (destaque) + Home. Não dominou → Try again
    // (destaque) + Home.
    if (result.mastered && !isLast) {
      row.append(
        makeButton("Next level", "primary", () => choose("next")),
        makeButton("Replay", "ghost", () => choose("retry")),
        makeButton("Home", "ghost", () => choose("home")),
      )
    } else if (result.mastered) {
      row.append(
        makeButton("Replay", "primary", () => choose("retry")),
        makeButton("Home", "ghost", () => choose("home")),
      )
    } else {
      row.append(
        makeButton("Try again", "primary", () => choose("retry")),
        makeButton("Home", "ghost", () => choose("home")),
      )
    }

    screen.append(head, stars, row)
    host.appendChild(screen)
  })
}

function makeButton(label: string, variant: "primary" | "ghost", onTap: () => void): HTMLButtonElement {
  const button = document.createElement("button")
  button.className = `go-btn ${variant}`
  button.textContent = label
  button.addEventListener("pointerdown", onTap)
  return button
}
