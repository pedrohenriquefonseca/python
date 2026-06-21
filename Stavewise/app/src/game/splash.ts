// Tela de splash "Waveform": equalizador de neon (magenta com picos ciano) sobre o
// fundo escuro, com a marca e a chamada "tap to play". O toque dispensa o splash
// (e serve de gesto do usuário p/ destravar o áudio na WKWebView) e resolve a
// Promise — o main encadeia o início do jogo nela.

// Alturas relativas das barras (silhueta de forma de onda). O índice em CYAN vira
// pico ciano; o resto é magenta. Normalizadas pelo maior valor abaixo.
const BAR_HEIGHTS = [30, 52, 80, 116, 72, 40, 96, 140, 60, 36, 78, 156, 112, 68, 44, 100, 128, 56, 32, 124, 22, 14]
const CYAN = new Set([7, 11, 16, 19])
const MAX = Math.max(...BAR_HEIGHTS)

export function showSplash(host: HTMLElement): Promise<void> {
  return new Promise((resolve) => {
    const splash = document.createElement("div")
    splash.id = "splash"

    const title = document.createElement("div")
    title.className = "splash-title"
    title.textContent = "Stavewise"

    const tag = document.createElement("div")
    tag.className = "splash-tag"
    tag.textContent = "Read it · play it · feel the tempo"

    const wave = document.createElement("div")
    wave.className = "splash-wave"
    BAR_HEIGHTS.forEach((h, i) => {
      const bar = document.createElement("div")
      bar.className = "splash-bar" + (CYAN.has(i) ? " cy" : "")
      bar.style.height = `${(h / MAX) * 100}%`
      // Fases dessincronizadas: a onda "respira" em vez de pulsar em bloco.
      bar.style.animationDelay = `${(i % 7) * -0.13}s`
      bar.style.animationDuration = `${1 + (i % 5) * 0.12}s`
      wave.appendChild(bar)
    })

    const cta = document.createElement("div")
    cta.className = "splash-cta"
    cta.textContent = "Tap to start"

    splash.append(title, tag, wave, cta)
    host.appendChild(splash)

    const dismiss = () => {
      splash.classList.add("hide")
      const done = () => {
        splash.remove()
        resolve()
      }
      splash.addEventListener("transitionend", done, { once: true })
      // Rede de segurança caso o transitionend não dispare.
      setTimeout(done, 600)
    }
    splash.addEventListener("pointerdown", dismiss, { once: true })
  })
}
