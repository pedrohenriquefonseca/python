// Tela "vamos acelerar": aparece ao passar de velocidade dentro do MESMO nível
// (Largo→Adagio→Andante). SEM botões — festeja com confete, balões, estrelas e
// flores (estética circense/carnaval) e volta pro jogo sozinha depois de contar
// 3→2→1→Go! (cada dígito estoura: cresce e esmaece antes do próximo). Resolve a
// Promise quando a celebração termina; o main chama advanceTempo() em seguida.
// Mockup aprovado pelo usuário em 1/jul antes de implementar.

export interface SpeedUpInfo {
  level: number
  music: string
  nextTempoName: string // "Adagio" ou "Andante"
}

const CONFETTI_COLORS = ["#FF2E88", "#19E3D6", "#FFC53D", "#7F77DD", "#5DCAA5", "#F0997B"]
const SPARK_EMOJI = ["✨", "🎉", "⭐"]
const DECO_EMOJI = ["🌸", "💗", "🌸", "💗", "⭐"]

function rnd(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

export function showSpeedUp(host: HTMLElement, info: SpeedUpInfo): Promise<void> {
  return new Promise((resolve) => {
    const screen = document.createElement("div")
    screen.id = "speedup"

    const title = document.createElement("div")
    title.className = "su-title"
    title.textContent = "Congrats! Let's speed things up!"

    const sub = document.createElement("div")
    sub.className = "su-sub"
    sub.textContent = `Level ${info.level} · ${info.music} · now in ${info.nextTempoName}`

    const countWrap = document.createElement("div")
    countWrap.className = "su-count-wrap"
    const count = document.createElement("div")
    count.className = "su-count"
    countWrap.appendChild(count)

    screen.append(title, sub, countWrap)
    spawnDecor(screen)
    host.appendChild(screen)

    // Contagem 3→2→1→"Go!" a 1s cada; cada dígito estoura (su-burst: cresce e
    // esmaece) antes do próximo aparecer. Ao fim, esmaece a tela toda e resolve —
    // sem espera por toque (esta tela não tem botão nenhum).
    let n = 3
    const burst = () => {
      count.textContent = n > 0 ? String(n) : "Go!"
      count.style.animation = "none"
      void count.offsetWidth // força reflow p/ reiniciar a animação do zero
      count.style.animation = "su-burst 0.95s ease-out"
    }
    burst()
    const tick = setInterval(() => {
      if (n === 0) {
        clearInterval(tick)
        screen.classList.add("hide")
        const done = () => {
          screen.remove()
          resolve()
        }
        screen.addEventListener("transitionend", done, { once: true })
        setTimeout(done, 600) // rede de segurança
        return
      }
      n -= 1
      burst()
    }, 1000)
  })
}

// Confete caindo, balões subindo balançando, faíscas/estrelas e flores/corações
// nos cantos — gerados uma vez ao montar a tela, puramente decorativos.
function spawnDecor(screen: HTMLElement): void {
  for (let i = 0; i < 28; i++) {
    const c = document.createElement("div")
    c.className = "su-confetti"
    c.style.left = `${rnd(0, 100)}%`
    c.style.width = `${rnd(7, 12)}px`
    c.style.height = `${rnd(12, 18)}px`
    c.style.background = CONFETTI_COLORS[i % CONFETTI_COLORS.length]
    c.style.animationDuration = `${rnd(2.4, 4)}s`
    c.style.animationDelay = `${rnd(0, 3)}s`
    screen.appendChild(c)
  }
  for (let i = 0; i < 6; i++) {
    const b = document.createElement("div")
    b.className = "su-balloon"
    b.textContent = "🎈"
    b.style.left = `${rnd(3, 92)}%`
    b.style.fontSize = `${rnd(38, 58)}px`
    b.style.filter = `hue-rotate(${rnd(0, 360)}deg)`
    b.style.animationDuration = `${rnd(5, 8)}s`
    b.style.animationDelay = `${rnd(0, 4)}s`
    screen.appendChild(b)
  }
  for (let i = 0; i < 7; i++) {
    const s = document.createElement("div")
    s.className = "su-spark"
    s.textContent = SPARK_EMOJI[i % SPARK_EMOJI.length]
    s.style.top = `${rnd(6, 62)}%`
    s.style.left = `${rnd(6, 92)}%`
    s.style.fontSize = `${rnd(28, 44)}px`
    s.style.animationDuration = `${rnd(1.6, 2.6)}s`
    s.style.animationDelay = `${rnd(0, 3)}s`
    screen.appendChild(s)
  }
  for (let i = 0; i < 6; i++) {
    const d = document.createElement("div")
    d.className = "su-spark"
    d.textContent = DECO_EMOJI[i % DECO_EMOJI.length]
    d.style.top = `${rnd(4, 24)}%`
    d.style.left = i % 2 === 0 ? `${rnd(2, 12)}%` : `${rnd(86, 97)}%`
    d.style.fontSize = `${rnd(26, 38)}px`
    d.style.animationDuration = `${rnd(2, 3.2)}s`
    d.style.animationDelay = `${rnd(0, 3)}s`
    screen.appendChild(d)
  }
}
