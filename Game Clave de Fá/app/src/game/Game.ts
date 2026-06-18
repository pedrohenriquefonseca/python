import type { Note, FloatingLabel } from "./types"
import { theme } from "../theme"
import { Particles } from "./particles"
import { drawScene, noteScreenY, hitXForKey } from "./render"
import { tierForCombo } from "./combo"
import { validPositionsForMidi, solfege } from "../data/slidePositions"
import { MAX_ACCIDENTALS } from "../data/keys"
import { tempoById, type Tempo, type TempoId } from "./tempo"

// Pool inicial: Dó maior do centro ao lá (C3 D3 E3 F3 G3 A3). Sem linhas suplementares.
const POOL = [48, 50, 52, 53, 55, 57]

export class Game {
  private ctx: CanvasRenderingContext2D
  private cssW = 0
  private cssH = 0
  private dpr = 1

  private notes: Note[] = []
  private labels: FloatingLabel[] = []
  private particles = new Particles()
  private combo = 0
  private best = 0
  private score = 0
  private flash = 0
  private shake = 0

  private spawnAcc = 0
  private tempo: Tempo = tempoById("andante")
  private keySig = 0 // ciclo de quintas: -7 (7♭) … 0 (Dó) … +7 (7♯)
  private timeSig: [number, number] = [4, 4] // por enquanto sempre 4/4
  private lastMidi = -1
  private lastTime = 0
  private running = false

  constructor(
    private canvas: HTMLCanvasElement,
    private controls: HTMLElement,
  ) {
    const ctx = canvas.getContext("2d")
    if (!ctx) throw new Error("Canvas 2D indisponível")
    this.ctx = ctx
    this.buildButtons()
    this.resize()
    window.addEventListener("resize", () => this.resize())
    window.addEventListener("keydown", (e) => {
      const n = parseInt(e.key, 10)
      if (n >= 1 && n <= 7) {
        this.press(n)
        return
      }
      const tempoKey: Record<string, TempoId> = { "`": "largo", q: "adagio", w: "andante", e: "allegro" }
      const id = tempoKey[e.key.toLowerCase()]
      if (id) {
        this.setTempo(id)
        return
      }
      if (e.key === "[") this.keySig = Math.max(-MAX_ACCIDENTALS, this.keySig - 1) // mais bemóis
      else if (e.key === "]") this.keySig = Math.min(MAX_ACCIDENTALS, this.keySig + 1) // mais sustenidos
      else return
      this.recomputeHitX() // a linha acompanha o novo tom
    })
  }

  private hitXValue = 110

  // Posição da linha de acerto: o mínimo que ainda deixa o nome da nota caber sem
  // invadir clave + armadura (calculado da notação real em resize()).
  private get hitX(): number {
    return this.hitXValue
  }

  private get hitWindowPx(): number {
    return Math.max(48, this.cssW * 0.1)
  }

  // Velocidade e cadência derivam do BPM do andamento (Andante ≈ ritmo atual).
  private get speed(): number {
    return this.tempo.bpm * 1.8 // px/s de rolagem
  }

  private get spawnInterval(): number {
    return 66000 / this.tempo.bpm // ms entre notas (≈ 1 nota por tempo)
  }

  setTempo(id: TempoId): void {
    this.tempo = tempoById(id)
  }

  start(): void {
    if (this.running) return
    this.running = true
    this.lastTime = performance.now()
    requestAnimationFrame(this.frame)
  }

  press(pos: number): void {
    this.flashButton(pos)
    let target: Note | null = null
    let bestDist = Infinity
    for (const note of this.notes) {
      const dist = Math.abs(note.x - this.hitX)
      if (dist <= this.hitWindowPx && dist < bestDist) {
        bestDist = dist
        target = note
      }
    }
    if (!target) return
    if (target.positions.includes(pos)) this.resolveHit(target)
    else this.resolveMiss(target, true)
  }

  private remove(note: Note): void {
    this.notes = this.notes.filter((n) => n !== note)
  }

  private addLabel(note: Note, color: string, size: number): void {
    this.labels.push({
      text: solfege(note.midi),
      x: this.hitX,
      y: noteScreenY(note.midi, this.cssW, this.cssH),
      life: 0.9,
      maxLife: 0.9,
      color,
      size,
    })
  }

  private resolveHit(note: Note): void {
    this.combo += 1
    if (this.combo > this.best) this.best = this.combo
    const tier = tierForCombo(this.combo)
    this.score += tier.mult * 10
    this.particles.explode(this.hitX, noteScreenY(note.midi, this.cssW, this.cssH), tier.color, this.combo)
    this.addLabel(note, tier.color, 28)
    this.remove(note)
  }

  private resolveMiss(note: Note, wrong: boolean): void {
    this.combo = 0
    this.flash = Math.max(this.flash, wrong ? 1 : 0.6)
    if (wrong) this.shake = 8
    this.particles.puff(this.hitX, noteScreenY(note.midi, this.cssW, this.cssH), theme.muted)
    this.addLabel(note, theme.muted, 24)
    this.remove(note)
  }

  private buildButtons(): void {
    this.controls.innerHTML = ""

    const label = document.createElement("div")
    label.className = "controls-label"
    label.textContent = "Trombone Slide Positions"
    this.controls.appendChild(label)

    const row = document.createElement("div")
    row.className = "btn-row"
    for (let i = 1; i <= 7; i++) {
      const button = document.createElement("button")
      button.className = "pos-btn"
      button.textContent = String(i)
      button.dataset.pos = String(i)
      button.addEventListener("pointerdown", (ev: Event) => {
        ev.preventDefault()
        this.press(i)
      })
      row.appendChild(button)
    }
    this.controls.appendChild(row)
  }

  private flashButton(pos: number): void {
    const button = this.controls.querySelector<HTMLButtonElement>(`[data-pos="${pos}"]`)
    if (!button) return
    button.classList.add("flash")
    setTimeout(() => button.classList.remove("flash"), 120)
  }

  private resize(): void {
    this.dpr = Math.min(window.devicePixelRatio || 1, 2)
    const rect = this.canvas.getBoundingClientRect()
    this.cssW = rect.width
    this.cssH = rect.height
    this.canvas.width = Math.round(rect.width * this.dpr)
    this.canvas.height = Math.round(rect.height * this.dpr)
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0)
    this.recomputeHitX()
  }

  // A linha de acerto depende do tom (último acidente) e do tamanho da pauta,
  // então recalcula no resize e a cada troca de armadura.
  private recomputeHitX(): void {
    this.hitXValue = Math.max(110, hitXForKey(this.ctx, this.cssW, this.cssH, Math.abs(this.keySig)))
  }

  private spawn(): void {
    let midi = POOL[Math.floor(Math.random() * POOL.length)]
    while (midi === this.lastMidi) midi = POOL[Math.floor(Math.random() * POOL.length)]
    this.lastMidi = midi
    this.notes.push({
      midi,
      x: this.cssW + 30,
      positions: validPositionsForMidi(midi),
    })
  }

  private frame = (now: number): void => {
    if (!this.running) return
    const dt = Math.min(now - this.lastTime, 50)
    this.lastTime = now
    const s = dt / 16.667
    this.update(dt, s)
    this.render()
    requestAnimationFrame(this.frame)
  }

  private update(dt: number, s: number): void {
    this.spawnAcc += dt
    if (this.spawnAcc >= this.spawnInterval) {
      this.spawnAcc = 0
      this.spawn()
    }

    const dx = this.speed * (dt / 1000)
    for (const note of this.notes) note.x -= dx

    // Nota que chega na linha sem ser acertada: resolve e some ali mesmo.
    for (const note of [...this.notes]) {
      if (note.x <= this.hitX) this.resolveMiss(note, false)
    }

    this.particles.update(s)

    for (const label of this.labels) label.life -= dt / 1000
    this.labels = this.labels.filter((l) => l.life > 0)

    this.flash *= Math.pow(0.88, s)
    this.shake *= Math.pow(0.82, s)
  }

  private drawLabels(): void {
    const ctx = this.ctx
    ctx.textAlign = "right"
    ctx.textBaseline = "middle"
    for (const label of this.labels) {
      const k = label.life / label.maxLife
      ctx.globalAlpha = Math.max(0, k)
      ctx.fillStyle = label.color
      ctx.font = `500 ${label.size}px -apple-system, system-ui, sans-serif`
      ctx.fillText(label.text, label.x - 26, label.y)
    }
    ctx.globalAlpha = 1
  }

  private render(): void {
    const ctx = this.ctx
    ctx.clearRect(0, 0, this.cssW, this.cssH)
    ctx.fillStyle = theme.bg
    ctx.fillRect(0, 0, this.cssW, this.cssH)
    ctx.save()
    if (this.shake > 0.5) {
      ctx.translate((Math.random() - 0.5) * this.shake, (Math.random() - 0.5) * this.shake)
    }
    drawScene(ctx, {
      w: this.cssW,
      h: this.cssH,
      notes: this.notes,
      combo: this.combo,
      best: this.best,
      score: this.score,
      hitX: this.hitX,
      flash: this.flash,
      tempoName: this.tempo.name,
      tempoColor: this.tempo.color,
      fifths: this.keySig,
      timeSig: this.timeSig,
    })
    this.particles.draw(ctx)
    this.drawLabels()
    ctx.restore()
  }
}
