// Waveform decorativa (equalizador neon): compartilhada entre Home e Game Over.
// Barras animadas com degradê magenta→ciano ao longo da largura, esmaecidas por
// uma máscara vertical (CSS `.home-wave`) — forte no rodapé, dissolvendo para
// cima. Cada barra "respira" fora de fase (delay dessincronizado) em vez de
// pulsar em bloco.
export function buildWave(): HTMLDivElement {
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
    bar.style.animationDelay = `${(i % 7) * -0.13}s`
    bar.style.animationDuration = `${1.1 + (i % 5) * 0.12}s`
    wave.appendChild(bar)
  }
  return wave
}
