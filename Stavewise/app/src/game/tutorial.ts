// Tutorial: overlay em papel claro, estilo desenhado à mão (doodle). São 3 momentos
// ESTÁTICOS (sem animação); cada toque avança um momento e o último começa o jogo.
// Aparece SOMENTE ao escolher "New game" (ver main.ts). A cena (pauta, clave de fá,
// notas, linha de acerto e os 7 botões) e as setas são desenhadas em SVG aqui — as
// setas saem do texto de cada momento e apontam para o elemento correspondente.

const MK = ["#7E5BD8", "#3D9CD6", "#E25C9A", "#6FB23F", "#E8A33D", "#2FB7A4", "#E2603F"]
const BX = [120, 228, 336, 444, 552, 660, 768]
const NOTES = [
  { x: 250, y: 160 },
  { x: 355, y: 135 },
  { x: 455, y: 185 },
  { x: 560, y: 150 },
  { x: 660, y: 172 },
]

interface StepCopy {
  h: string // título manuscrito do momento
  col: string // cor do título e da seta
  pos: string // posição (inline) do texto sobre a cena
}

// Os 3 títulos ficam no mesmo lugar (canto superior direito); de lá saem as setas.
const STEPS: StepCopy[] = [
  { h: "Read the notes", col: "#7E5BD8", pos: "right:4%; top:9%;" },
  { h: "Watch the line", col: "#E25C9A", pos: "right:4%; top:9%;" },
  { h: "Tap the position", col: "#6FB23F", pos: "right:4%; top:9%;" },
]

function staffLines(): string {
  let s = ""
  for (let i = 0; i < 5; i++) {
    const y = 110 + i * 25
    s += `<line x1="70" y1="${y}" x2="800" y2="${y}" stroke="#3a3a3a" stroke-width="2.6"/>`
  }
  return s
}

// Clave de fá desenhada à mão e encorpada: olho cheio sobre a linha do Fá, corpo
// grosso curvando à direita e para baixo, e os dois pontos ladeando a linha do Fá.
function clef(): string {
  return (
    `<path d="M106 125 C 138 112, 160 130, 154 152 C 148 176, 126 188, 104 190" fill="none" stroke="#2b2b2b" stroke-width="9" stroke-linecap="round"/>` +
    `<circle cx="106" cy="133" r="12" fill="#2b2b2b"/>` +
    `<circle cx="170" cy="126" r="5.5" fill="#2b2b2b"/>` +
    `<circle cx="170" cy="144" r="5.5" fill="#2b2b2b"/>`
  )
}

function note(n: { x: number; y: number }, color: string, big: boolean): string {
  const rx = big ? 16 : 13
  const ry = big ? 12.5 : 10
  return (
    `<g><ellipse cx="${n.x}" cy="${n.y}" rx="${rx}" ry="${ry}" transform="rotate(-20 ${n.x} ${n.y})" fill="${color}"/>` +
    `<line x1="${n.x + rx - 1}" y1="${n.y - 2}" x2="${n.x + rx - 1}" y2="${n.y - 46}" stroke="${color}" stroke-width="3.4"/></g>`
  )
}

function notes(step: number): string {
  let s = ""
  for (let i = 0; i < NOTES.length; i++) {
    const emph = step === 1 && i === 0 // no momento 2, a nota na linha é destacada
    s += note(NOTES[i], emph ? "#E25C9A" : "#2b2b2b", emph)
  }
  return s
}

function hitline(step: number): string {
  const glow = step === 1
  return `<line x1="250" y1="76" x2="250" y2="252" stroke="${glow ? "#E25C9A" : "#D11E6B"}" stroke-width="${glow ? 8 : 5}" stroke-linecap="round"/>`
}

function btnCircles(active: number): string {
  let s = ""
  for (let i = 0; i < 7; i++) {
    const on = active === i
    s += `<circle cx="${BX[i]}" cy="314" r="40" fill="${on ? MK[i] : "#fff"}" stroke="${MK[i]}" stroke-width="5"/>`
  }
  return s
}

function btnNums(active: number): string {
  let s = ""
  for (let i = 0; i < 7; i++) {
    const on = active === i
    s += `<text x="${BX[i]}" y="328" text-anchor="middle" font-family="Permanent Marker, cursive" font-size="38" fill="${on ? "#fff" : "#2b2b2b"}">${i + 1}</text>`
  }
  return s
}

// Setas grossas que saem do texto de cada momento e apontam para o elemento. A do
// momento 3 termina ACIMA do botão, com folga (a cabeça não encosta no círculo).
// Todas as setas saem de baixo do texto (canto sup. direito) e apontam para o
// elemento. Traço grosso + cabeça em triângulo cheio (calculada pela direção da
// curva), que não deforma sob o filtro de rabisco como dois traços finos.
const TAIL_X = 650
const TAIL_Y = 72

function arrowFromText(c1x: number, c1y: number, c2x: number, c2y: number, tx: number, ty: number, color: string): string {
  const ang = Math.atan2(ty - c2y, tx - c2x) // direção no ponto da ponta
  const len = 30
  const half = 15
  const bx = tx - len * Math.cos(ang)
  const by = ty - len * Math.sin(ang)
  const px = Math.sin(ang) * half
  const py = -Math.cos(ang) * half
  return (
    `<path d="M${TAIL_X} ${TAIL_Y} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${tx} ${ty}" fill="none" stroke="${color}" stroke-width="8" stroke-linecap="round"/>` +
    `<polygon points="${tx},${ty} ${bx + px},${by + py} ${bx - px},${by - py}" fill="${color}"/>`
  )
}

function arrow(step: number): string {
  if (step === 0) return arrowFromText(600, 92, 558, 120, 505, 142, "#7E5BD8") // → notas
  if (step === 1) return arrowFromText(520, 92, 360, 128, 272, 158, "#E25C9A") // → linha de acerto
  return arrowFromText(602, 150, 520, 216, 458, 266, "#6FB23F") // → botão da posição
}

function emph(step: number): string {
  if (step === 0)
    return `<ellipse cx="500" cy="160" rx="270" ry="60" fill="none" stroke="#7E5BD8" stroke-width="3.5" stroke-dasharray="3 10" opacity="0.6"/>`
  if (step === 1)
    return `<circle cx="250" cy="160" r="36" fill="none" stroke="#E25C9A" stroke-width="3.5" stroke-dasharray="3 10"/>`
  return ""
}

function scene(step: number): string {
  const active = step === 2 ? 3 : -1 // momento 3 acende o botão apontado (nº 4)
  return (
    `<svg viewBox="0 0 844 390" width="100%" height="100%" preserveAspectRatio="xMidYMid meet">` +
    `<defs><filter id="tutRough"><feTurbulence type="fractalNoise" baseFrequency="0.013" numOctaves="2" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="2.2"/></filter></defs>` +
    `<g>${staffLines()}</g>` +
    `<g filter="url(#tutRough)">${clef()}${hitline(step)}${notes(step)}${btnCircles(active)}${arrow(step)}${emph(step)}</g>` +
    `<g>${btnNums(active)}</g>` +
    `</svg>`
  )
}

function dots(step: number): string {
  let s = ""
  for (let i = 0; i < STEPS.length; i++) s += `<span class="tut-dot${i === step ? " on" : ""}"></span>`
  return s
}

export function showTutorial(host: HTMLElement): Promise<void> {
  return new Promise((resolve) => {
    const screen = document.createElement("div")
    screen.id = "tutorial"
    screen.innerHTML = `<div class="tut-scene"></div><div class="tut-title">Tutorial</div><div class="tut-co"></div><div class="tut-foot"></div>`
    const sceneEl = screen.querySelector<HTMLDivElement>(".tut-scene")!
    const coEl = screen.querySelector<HTMLDivElement>(".tut-co")!
    const footEl = screen.querySelector<HTMLDivElement>(".tut-foot")!

    let step = 0
    const last = STEPS.length - 1
    // Tempo mínimo em tela por passo: sem isso, um toque duplo/rápido (comum em
    // quem vem de outros apps) atravessa os 3 momentos quase instantaneamente e o
    // tutorial parece "não ter aberto".
    let paintedAt = 0

    const paint = (): void => {
      sceneEl.innerHTML = scene(step)
      const c = STEPS[step]
      coEl.setAttribute("style", c.pos)
      coEl.innerHTML = `<div class="h" style="color:${c.col}">${c.h}</div>`
      footEl.innerHTML = dots(step)
      paintedAt = performance.now()
    }
    paint()

    screen.addEventListener("pointerdown", () => {
      if (performance.now() - paintedAt < 350) return // debounce: ver comentário acima
      if (step < last) {
        step++
        paint()
        return
      }
      screen.classList.add("hide")
      const done = () => {
        screen.remove()
        resolve()
      }
      screen.addEventListener("transitionend", done, { once: true })
      setTimeout(done, 600) // rede de segurança
    })

    host.appendChild(screen)
  })
}
