import type { Note } from "./types"
import { theme } from "../theme"
import { Particles } from "./particles"
import { drawScene, noteScreenY } from "./render"
import { tierForCombo } from "./combo"
import { validPositionsForMidi } from "../data/slidePositions"

// Pool inicial: Dó maior do centro ao lá (C3 D3 E3 F3 G3 A3). Sem linhas suplementares.
const POOL = [48, 50, 52, 53, 55, 57]

export class Game {
  private ctx: CanvasRenderingContext2D
  private cssW = 0
  private cssH = 0
  private dpr = 1

  private notes: Note[] = []
  private particles = new Particles()
  private combo = 0
  private best = 0
  private score = 0
  private flash = 0
  private shake = 0

  private spawnAcc = 0
  private spawnInterval = 1100 // ms entre notas
  private speed = 160 // px/s de rolagem
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
      if (n >= 1 && n <= 7) this.press(n)
    })
  }

  private get hitX(): number {
    return Math.max(90, this.cssW * 0.2)
  }

  private get hitWindowPx(): number {
    return Math.max(30, this.cssW * 0.05)
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
      if (note.judged || note.state !== "live") continue
      const dist = Math.abs(note.x - this.hitX)
      if (dist <= this.hitWindowPx && dist < bestDist) {
        bestDist = dist
        target = note
      }
    }
    if (!target) return
    if (target.positions.includes(pos)) this.hit(target)
    else this.wrong(target)
  }

  private hit(note: Note): void {
    note.judged = true
    this.combo += 1
    if (this.combo > this.best) this.best = this.combo
    const tier = tierForCombo(this.combo)
    this.score += tier.mult * 10
    this.particles.burst(this.hitX, noteScreenY(note.midi, this.cssW, this.cssH), tier.color, this.combo)
    this.notes = this.notes.filter((n) => n !== note)
  }

  private wrong(note: Note): void {
    note.judged = true
    note.state = "missed"
    this.combo = 0
    this.flash = 1
    this.shake = 8
  }

  private buildButtons(): void {
    this.controls.innerHTML = ""
    for (let i = 1; i <= 7; i++) {
      const button = document.createElement("button")
      button.className = "pos-btn"
      button.textContent = String(i)
      button.dataset.pos = String(i)
      button.addEventListener("pointerdown", (ev: Event) => {
        ev.preventDefault()
        this.press(i)
      })
      this.controls.appendChild(button)
    }
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
  }

  private spawn(): void {
    let midi = POOL[Math.floor(Math.random() * POOL.length)]
    while (midi === this.lastMidi) midi = POOL[Math.floor(Math.random() * POOL.length)]
    this.lastMidi = midi
    this.notes.push({
      midi,
      x: this.cssW + 30,
      positions: validPositionsForMidi(midi),
      judged: false,
      state: "live",
      alpha: 1,
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
    for (const note of this.notes) {
      note.x -= dx
      if (!note.judged && note.x < this.hitX - this.hitWindowPx) {
        note.judged = true
        note.state = "missed"
        this.combo = 0
        this.flash = Math.max(this.flash, 0.6)
      }
      if (note.state === "missed") note.alpha -= 0.02 * s
    }
    this.notes = this.notes.filter((n) => n.x > -40 && n.alpha > 0)
    this.particles.update(s)
    this.flash *= Math.pow(0.88, s)
    this.shake *= Math.pow(0.82, s)
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
    })
    this.particles.draw(ctx)
    ctx.restore()
  }
}
