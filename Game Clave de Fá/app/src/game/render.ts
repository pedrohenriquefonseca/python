import type { Note } from "./types"
import { theme } from "../theme"
import { tierForCombo } from "./combo"

const SEMI_TO_DIATONIC: Record<number, number> = {
  0: 0, 2: 1, 4: 2, 5: 3, 7: 4, 9: 5, 11: 6,
}

interface Layout {
  midY: number
  lineGap: number
  staffLeft: number
  staffRight: number
  panelTop: number
  panelH: number
}

export interface Scene {
  w: number
  h: number
  notes: Note[]
  combo: number
  best: number
  score: number
  hitX: number
  flash: number
}

function layoutFor(w: number, h: number): Layout {
  const lineGap = Math.max(14, Math.min(30, h * 0.11))
  const midY = h * 0.54
  return {
    midY,
    lineGap,
    staffLeft: 16,
    staffRight: w - 16,
    panelTop: midY - 3.4 * lineGap,
    panelH: 6.8 * lineGap,
  }
}

function diatonicIndex(midi: number): number {
  const octave = Math.floor(midi / 12) - 1
  const semi = ((midi % 12) + 12) % 12
  const d = SEMI_TO_DIATONIC[semi] ?? 0
  return octave * 7 + d
}

const D3_INDEX = diatonicIndex(50)

function noteY(midi: number, L: Layout): number {
  const rel = diatonicIndex(midi) - D3_INDEX
  return L.midY - rel * (L.lineGap / 2)
}

export function noteScreenY(midi: number, w: number, h: number): number {
  return noteY(midi, layoutFor(w, h))
}

function drawClef(ctx: CanvasRenderingContext2D, L: Layout): void {
  const x = 34
  const y = L.midY - L.lineGap // linha do Fá
  ctx.fillStyle = theme.ink
  ctx.beginPath()
  ctx.arc(x, y + 3, L.lineGap * 0.34, 0, Math.PI * 2)
  ctx.fill()
  ctx.beginPath()
  ctx.arc(x + 16, y - 4, 2.2, 0, Math.PI * 2)
  ctx.fill()
  ctx.beginPath()
  ctx.arc(x + 16, y + 5, 2.2, 0, Math.PI * 2)
  ctx.fill()
}

function drawLedgers(ctx: CanvasRenderingContext2D, midi: number, x: number, L: Layout): void {
  const rel = diatonicIndex(midi) - D3_INDEX
  const len = L.lineGap * 1.1
  ctx.lineWidth = 1
  if (rel > 4) {
    for (let e = 6; e <= rel; e += 2) {
      const y = L.midY - e * (L.lineGap / 2)
      ctx.beginPath()
      ctx.moveTo(x - len, y)
      ctx.lineTo(x + len, y)
      ctx.stroke()
    }
  } else if (rel < -4) {
    for (let e = -6; e >= rel; e -= 2) {
      const y = L.midY - e * (L.lineGap / 2)
      ctx.beginPath()
      ctx.moveTo(x - len, y)
      ctx.lineTo(x + len, y)
      ctx.stroke()
    }
  }
}

function drawNote(ctx: CanvasRenderingContext2D, note: Note, L: Layout, hitX: number): void {
  const y = noteY(note.midi, L)
  const active = note.state === "live" && Math.abs(note.x - hitX) < L.lineGap * 0.9
  const color = note.state === "missed" ? theme.muted : active ? theme.accent : theme.ink

  ctx.globalAlpha = note.alpha
  if (active) {
    ctx.fillStyle = theme.accent
    ctx.globalAlpha = note.alpha * 0.16
    ctx.beginPath()
    ctx.arc(note.x, y, L.lineGap * 0.9, 0, Math.PI * 2)
    ctx.fill()
    ctx.globalAlpha = note.alpha
  }

  ctx.strokeStyle = color
  drawLedgers(ctx, note.midi, note.x, L)

  ctx.save()
  ctx.translate(note.x, y)
  ctx.rotate(-0.32)
  ctx.fillStyle = color
  ctx.beginPath()
  ctx.ellipse(0, 0, L.lineGap * 0.48, L.lineGap * 0.36, 0, 0, Math.PI * 2)
  ctx.fill()
  ctx.restore()

  ctx.lineWidth = 1.6
  ctx.beginPath()
  ctx.moveTo(note.x + L.lineGap * 0.44, y - 2)
  ctx.lineTo(note.x + L.lineGap * 0.44, y - L.lineGap * 2)
  ctx.stroke()

  ctx.globalAlpha = 1
}

function drawHud(
  ctx: CanvasRenderingContext2D,
  w: number,
  score: number,
  combo: number,
  best: number,
): void {
  const tier = tierForCombo(combo)
  const sans = "-apple-system, system-ui, sans-serif"

  ctx.textAlign = "left"
  ctx.textBaseline = "alphabetic"
  ctx.fillStyle = tier.color
  ctx.font = `500 26px ${sans}`
  ctx.fillText(String(combo), 16, 34)
  const cw = ctx.measureText(String(combo)).width

  ctx.fillStyle = theme.muted
  ctx.font = `13px ${sans}`
  ctx.fillText("combo", 16 + cw + 6, 34)
  const lw = ctx.measureText("combo").width

  ctx.fillStyle = tier.color
  ctx.font = `500 15px ${sans}`
  ctx.fillText(`×${tier.mult}  ${tier.name}`, 16 + cw + 6 + lw + 12, 33)

  const bw = 180
  const bh = 6
  const fill = Math.min(combo, 20) / 20
  ctx.fillStyle = theme.muted
  ctx.globalAlpha = 0.25
  ctx.fillRect(16, 42, bw, bh)
  ctx.globalAlpha = 1
  ctx.fillStyle = tier.color
  ctx.fillRect(16, 42, bw * fill, bh)

  ctx.textAlign = "right"
  ctx.fillStyle = theme.ink
  ctx.font = `500 16px ${sans}`
  ctx.fillText(`${score.toLocaleString("pt-BR")} pts`, w - 16, 30)
  ctx.fillStyle = theme.muted
  ctx.font = `12px ${sans}`
  ctx.fillText(`recorde ${best}`, w - 16, 48)
}

export function drawScene(ctx: CanvasRenderingContext2D, scene: Scene): void {
  const { w, h, notes, combo, best, score, hitX, flash } = scene
  const L = layoutFor(w, h)

  ctx.fillStyle = theme.panel
  ctx.beginPath()
  ctx.roundRect(8, L.panelTop, w - 16, L.panelH, 16)
  ctx.fill()

  ctx.strokeStyle = theme.ink
  ctx.globalAlpha = 0.42
  ctx.lineWidth = 1
  for (let i = 0; i < 5; i++) {
    const y = L.midY + (i - 2) * L.lineGap
    ctx.beginPath()
    ctx.moveTo(L.staffLeft, y)
    ctx.lineTo(L.staffRight, y)
    ctx.stroke()
  }
  ctx.globalAlpha = 1

  drawClef(ctx, L)

  ctx.fillStyle = theme.accent
  ctx.globalAlpha = 0.1
  ctx.fillRect(hitX - 16, L.panelTop + 6, 32, L.panelH - 12)
  ctx.globalAlpha = 1
  ctx.strokeStyle = theme.accent
  ctx.lineWidth = 3
  ctx.beginPath()
  ctx.moveTo(hitX, L.panelTop + 6)
  ctx.lineTo(hitX, L.panelTop + L.panelH - 6)
  ctx.stroke()

  for (const note of notes) drawNote(ctx, note, L, hitX)

  drawHud(ctx, w, score, combo, best)

  if (flash > 0.02) {
    ctx.fillStyle = "#E24B4A"
    ctx.globalAlpha = flash * 0.16
    ctx.fillRect(0, 0, w, h)
    ctx.globalAlpha = 1
  }
}
