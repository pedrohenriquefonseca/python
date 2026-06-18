import type { Note } from "./types"
import { theme } from "../theme"
import { tierForCombo } from "./combo"
import { accidentalsForKey, keyName } from "../data/keys"

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
  tempoName: string
  tempoColor: string
  fifths: number
  timeSig: [number, number]
}

// Faixa de cabeçalho (cinza) reservada acima da pauta. Nenhum texto do topo
// pode invadir a região branca da pauta — ela começa em panelTop = HEADER_H.
const HEADER_H = 74
const BOTTOM_MARGIN = 4

// Linhas suplementares aprovisionadas. Intervalo de trabalho dó³–sol⁴:
// sol⁴ exige 3 linhas acima; dó³ fica dentro da pauta (0 abaixo necessárias),
// mas reservamos 1 de folga abaixo. A pauta tem 5 linhas (4 lineGaps de altura)
// e a linha de cima/baixo ficam a 2 lineGaps do meio.
const LEDGERS_ABOVE = 3
const LEDGERS_BELOW = 0
const EDGE_MARGIN = 0.9 // folga (em lineGaps) p/ a cabeça da nota além da última suplementar

function layoutFor(w: number, h: number): Layout {
  const spanAbove = 2 + LEDGERS_ABOVE + EDGE_MARGIN // do meio até o topo, em lineGaps
  const spanBelow = 2 + LEDGERS_BELOW + EDGE_MARGIN
  const units = spanAbove + spanBelow
  const avail = h - HEADER_H - BOTTOM_MARGIN
  const lineGap = Math.max(14, Math.min(28, avail / units))
  const panelTop = HEADER_H
  const midY = panelTop + spanAbove * lineGap
  const panelH = units * lineGap
  return {
    midY,
    lineGap,
    staffLeft: 16,
    staffRight: w - 16,
    panelTop,
    panelH,
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

const MUSIC_FONT = `"Bravura","Petaluma","Noto Music","Segoe UI Symbol","Apple Symbols",serif`

// Desenha a clave de fá e devolve a borda direita (x) para a armadura seguir.
function drawClef(ctx: CanvasRenderingContext2D, L: Layout): number {
  const fLineY = L.midY - L.lineGap // linha do Fá (2ª de cima)
  const size = L.lineGap * 3.6
  const x = 20
  ctx.fillStyle = theme.ink
  ctx.textAlign = "left"
  ctx.textBaseline = "alphabetic"
  ctx.font = `${size}px ${MUSIC_FONT}`
  // U+1D122 MUSICAL SYMBOL F CLEF — baseline calibrada (medida no canvas) para
  // que a linha do Fá caia exatamente no meio dos 2 pontos da clave.
  ctx.fillText("𝄢", x, fLineY + size * 0.45)
  return x + ctx.measureText("𝄢").width
}

// Armadura logo após a clave. Cada glifo (♯/♭) fica na linha/espaço da sua nota,
// usando o mesmo noteY das notas. Devolve a borda direita.
function drawKeySignature(
  ctx: CanvasRenderingContext2D,
  L: Layout,
  fifths: number,
  startX: number,
): number {
  const accs = accidentalsForKey(fifths)
  if (accs.length === 0) return startX
  ctx.fillStyle = theme.ink
  ctx.textAlign = "left"
  ctx.textBaseline = "middle"
  const step = L.lineGap * 0.78
  let x = startX + L.lineGap * 0.35
  for (const acc of accs) {
    const isFlat = acc.symbol === "♭"
    const size = isFlat ? L.lineGap * 2.5 : L.lineGap * 2.2
    // O corpo do ♭ fica na metade de baixo do glifo; sobe um pouco para a barriga
    // cair na linha/espaço. O ♯ é simétrico. Ambos descem um tico para assentar
    // melhor na linha/espaço.
    const dy = isFlat ? -size * 0.095 : size * 0.035
    ctx.font = `${size}px ${MUSIC_FONT}`
    ctx.fillText(acc.symbol, x, noteY(acc.midi, L) + dy)
    x += step
  }
  return x
}

const TIMESIG_FONT_SCALE = 2.3 // tamanho de cada dígito em lineGaps
const TIMESIG_PAD = 0.45 // respiro (em lineGaps) entre a armadura e a fórmula

// Fórmula de compasso após a armadura. Numerador centrado na linha 4, denominador
// na linha 2 (cada dígito ~2 espaços). Devolve a borda direita.
function drawTimeSignature(
  ctx: CanvasRenderingContext2D,
  L: Layout,
  startX: number,
  top: number,
  bottom: number,
): number {
  ctx.fillStyle = theme.ink
  ctx.font = `700 ${L.lineGap * TIMESIG_FONT_SCALE}px Georgia, "Times New Roman", serif`
  ctx.textAlign = "center"
  ctx.textBaseline = "middle"
  const w = Math.max(ctx.measureText(String(top)).width, ctx.measureText(String(bottom)).width)
  const cx = startX + L.lineGap * TIMESIG_PAD + w / 2
  ctx.fillText(String(top), cx, L.midY - L.lineGap)
  ctx.fillText(String(bottom), cx, L.midY + L.lineGap)
  return cx + w / 2
}

const LABEL_FONT = `500 28px -apple-system, system-ui, sans-serif`
const LABEL_GUTTER = 26 // o nome da nota é desenhado em hitX - 26 (ver Game.drawLabels)
const HITLINE_GAP = 72 // px do fim da notação (clave+armadura+fórmula) até a linha

// Linha de acerto ADAPTÁVEL: fica HITLINE_GAP px à direita do último acidente da
// armadura atual, então anda conforme o tom da partitura. Medido na fonte real,
// então acompanha o lineGap do aparelho. A folga nunca encolhe abaixo do espaço
// do nome da nota, para o label não voltar a invadir a notação.
export function hitXForKey(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  accidentals: number,
): number {
  const L = layoutFor(w, h)
  ctx.save()
  ctx.font = `${L.lineGap * 3.6}px ${MUSIC_FONT}`
  let accRight = 20 + ctx.measureText("𝄢").width // borda direita da clave (Dó M)
  if (accidentals > 0) {
    const step = L.lineGap * 0.78
    ctx.font = `${L.lineGap * 2.5}px ${MUSIC_FONT}`
    const flatW = ctx.measureText("♭").width
    ctx.font = `${L.lineGap * 2.2}px ${MUSIC_FONT}`
    const sharpW = ctx.measureText("♯").width
    accRight += L.lineGap * 0.35 + (accidentals - 1) * step + Math.max(flatW, sharpW)
  }
  // fórmula de compasso, sempre presente (hoje 4/4 — dígito de 1 caractere)
  ctx.font = `700 ${L.lineGap * TIMESIG_FONT_SCALE}px Georgia, "Times New Roman", serif`
  accRight += L.lineGap * TIMESIG_PAD + ctx.measureText("4").width
  ctx.font = LABEL_FONT
  const labelClear = LABEL_GUTTER + ctx.measureText("sol").width // nome de nota mais largo
  ctx.restore()
  return accRight + Math.max(HITLINE_GAP, labelClear)
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
  const active = Math.abs(note.x - hitX) < L.lineGap * 0.9
  const color = active ? theme.accent : theme.ink

  if (active) {
    ctx.fillStyle = theme.accent
    ctx.globalAlpha = 0.16
    ctx.beginPath()
    ctx.arc(note.x, y, L.lineGap * 0.9, 0, Math.PI * 2)
    ctx.fill()
    ctx.globalAlpha = 1
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

  // Haste: notas acima da linha do meio (D3) levam haste para baixo.
  const rel = diatonicIndex(note.midi) - D3_INDEX
  const stemDown = rel > 0
  ctx.lineWidth = 1.6
  ctx.beginPath()
  if (stemDown) {
    ctx.moveTo(note.x - L.lineGap * 0.44, y + 2)
    ctx.lineTo(note.x - L.lineGap * 0.44, y + L.lineGap * 2)
  } else {
    ctx.moveTo(note.x + L.lineGap * 0.44, y - 2)
    ctx.lineTo(note.x + L.lineGap * 0.44, y - L.lineGap * 2)
  }
  ctx.stroke()
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

  ctx.textAlign = "right"
  ctx.fillStyle = theme.ink
  ctx.font = `500 16px ${sans}`
  ctx.fillText(`${score.toLocaleString("pt-BR")} pts`, w - 16, 30)
  ctx.fillStyle = theme.muted
  ctx.font = `12px ${sans}`
  ctx.fillText(`recorde ${best}`, w - 16, 48)
}

function drawTempo(ctx: CanvasRenderingContext2D, w: number, name: string, color: string): void {
  const sans = "-apple-system, system-ui, sans-serif"
  ctx.textAlign = "center"
  ctx.textBaseline = "alphabetic"
  ctx.fillStyle = color
  ctx.font = `600 24px ${sans}`
  ctx.fillText(name, w / 2, 36)
}

export function drawScene(ctx: CanvasRenderingContext2D, scene: Scene): void {
  const { w, h, notes, combo, best, score, hitX, flash, tempoName, tempoColor, fifths, timeSig } = scene
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

  const clefRight = drawClef(ctx, L)
  const keyRight = drawKeySignature(ctx, L, fifths, clefRight)
  drawTimeSignature(ctx, L, keyRight, timeSig[0], timeSig[1])

  ctx.strokeStyle = theme.accent
  ctx.lineWidth = 3
  ctx.beginPath()
  ctx.moveTo(hitX, L.panelTop + 6)
  ctx.lineTo(hitX, L.panelTop + L.panelH - 6)
  ctx.stroke()

  for (const note of notes) drawNote(ctx, note, L, hitX)

  drawHud(ctx, w, score, combo, best)
  drawTempo(ctx, w, tempoName, tempoColor)

  ctx.textAlign = "center"
  ctx.textBaseline = "alphabetic"
  ctx.fillStyle = theme.muted
  ctx.font = `500 13px -apple-system, system-ui, sans-serif`
  ctx.fillText(keyName(fifths), w / 2, 56)

  if (flash > 0.02) {
    ctx.fillStyle = "#E24B4A"
    ctx.globalAlpha = flash * 0.16
    ctx.fillRect(0, 0, w, h)
    ctx.globalAlpha = 1
  }
}
