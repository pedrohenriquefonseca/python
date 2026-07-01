import type { Note } from "./types"
import { theme } from "../theme"
import { accidentalsForKey, keyAccidental, keyName } from "../data/keys"
import { RHYTHMS } from "./rhythm"

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
  lives: number
  hitX: number
  flash: number
  tempoName: string
  tempoColor: string
  fifths: number
  level: number
  music: string
  minMidi: number
  maxMidi: number
}

// Faixa de cabeçalho (cinza) reservada acima da pauta. Nenhum texto do topo pode
// invadir a região branca da pauta — ela começa em panelTop = headerH(h).
// Proporcional à altura (18% do viewport) em vez de px fixo, para o preview
// reduzido do editor bater com o aparelho real; piso/teto evitam extremos em
// telas muito baixas ou muito altas.
const HEADER_FRACTION = 0.18
const HEADER_MIN = 56
const HEADER_MAX = 88
function headerH(h: number): number {
  return Math.max(HEADER_MIN, Math.min(HEADER_MAX, h * HEADER_FRACTION))
}

const BOTTOM_MARGIN = 0 // o painel da pauta vai até a base do canvas; o respiro
// para a barra rosa vem do padding-top de #controls (CSS), mantendo os 3 vãos iguais.

// A pauta tem 5 linhas (4 lineGaps); a linha de cima/baixo ficam a HALF_STAFF
// lineGaps do meio (ré³). Acima/abaixo reservamos só o necessário para as notas
// EFETIVAMENTE em jogo (o intervalo min..max do pool): pauta compacta quando tudo
// cabe nas 5 linhas, encolhendo para abrir suplementares quando notas agudas ou
// graves entram. Intervalo de trabalho do jogo: mi² (E2) … lá⁴ (A4).
const HALF_STAFF = 2 // do meio até a linha de cima/baixo, em lineGaps
const EDGE_MARGIN = 0.6 // folga (em lineGaps) p/ a cabeça da nota extrema

// `minMidi`/`maxMidi`: extremos do intervalo de notas em jogo. A nota mais aguda
// puxa a folga de cima; a mais grave, a de baixo. Cada lado nunca fica menor que
// meia-pauta (HALF_STAFF), para as 5 linhas aparecerem sempre por inteiro.
function layoutFor(w: number, h: number, minMidi: number, maxMidi: number): Layout {
  const relAbove = Math.max(0, diatonicIndex(maxMidi) - D3_INDEX) // meios-lineGaps
  const relBelow = Math.max(0, D3_INDEX - diatonicIndex(minMidi))
  const spanAbove = Math.max(HALF_STAFF, relAbove / 2) + EDGE_MARGIN
  const spanBelow = Math.max(HALF_STAFF, relBelow / 2) + EDGE_MARGIN
  const units = spanAbove + spanBelow
  const hh = headerH(h)
  const avail = h - hh - BOTTOM_MARGIN
  // Sem teto: o painel preenche todo o `avail`, então o fundo do painel é estável
  // (não sobra folga variável acima da barra rosa). Piso de 14 para telas mínimas.
  const lineGap = Math.max(14, avail / units)
  const panelTop = hh
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

export function noteScreenY(
  midi: number,
  w: number,
  h: number,
  minMidi: number,
  maxMidi: number,
): number {
  return noteY(midi, layoutFor(w, h, minMidi, maxMidi))
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

const LABEL_FONT = `500 28px -apple-system, system-ui, sans-serif`
const LABEL_GUTTER = 14 // o nome da nota é desenhado em hitX - 14 (ver Game.drawLabels)
const HITLINE_GAP = 36 // px do fim da notação (clave+armadura) até a linha

// Linha de acerto ADAPTÁVEL: fica HITLINE_GAP px à direita do último acidente da
// armadura atual, então anda conforme o tom da partitura. Medido na fonte real,
// então acompanha o lineGap do aparelho. A folga nunca encolhe abaixo do espaço
// do nome da nota, para o label não voltar a invadir a notação.
export function hitXForKey(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  accidentals: number,
  minMidi: number,
  maxMidi: number,
): number {
  const L = layoutFor(w, h, minMidi, maxMidi)
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

// Pausa: glifo de pausa de semínima (𝄽) centrado na linha do meio. Não tem altura,
// não recebe o destaque de "toque agora" nem nome — só marca o silêncio rolando.
function drawRest(ctx: CanvasRenderingContext2D, x: number, L: Layout): void {
  ctx.fillStyle = theme.muted
  ctx.font = `${L.lineGap * 3.2}px ${MUSIC_FONT}`
  ctx.textAlign = "center"
  ctx.textBaseline = "middle"
  ctx.fillText("𝄽", x, L.midY)
}

// Bandeirolas (colcheia = 1, semicolcheia = 2) na ponta livre da haste, curvando
// para a direita e na direção da cabeça. toHead = sinal de y da ponta para a
// cabeça (+1 haste p/ cima, -1 haste p/ baixo): empilha as 2 e dá a queda da curva.
function drawFlags(
  ctx: CanvasRenderingContext2D,
  stemX: number,
  tipY: number,
  toHead: number,
  count: number,
  L: Layout,
  color: string,
): void {
  ctx.strokeStyle = color
  ctx.lineWidth = L.lineGap * 0.16
  for (let k = 0; k < count; k++) {
    const ty = tipY + toHead * k * (L.lineGap * 0.34)
    ctx.beginPath()
    ctx.moveTo(stemX, ty)
    ctx.quadraticCurveTo(
      stemX + L.lineGap * 0.95,
      ty + toHead * L.lineGap * 0.5,
      stemX + L.lineGap * 0.55,
      ty + toHead * L.lineGap * 1.15,
    )
    ctx.stroke()
  }
}

function drawNote(ctx: CanvasRenderingContext2D, note: Note, L: Layout, hitX: number, fifths: number): void {
  const fig = RHYTHMS[note.rhythm]
  if (fig.isRest) {
    drawRest(ctx, note.x, L)
    return
  }

  const y = noteY(note.midi, L)
  const active = Math.abs(note.x - hitX) < L.lineGap * 0.9
  // Notas que a armadura altera (ex.: si → si♭ em Fá M) ganham cor própria
  // enquanto rolam, sinalizando o acidente antes de chegar à linha. A nota ativa
  // ainda vence (magenta) — perto da linha o destaque de "toque agora" prevalece e
  // o nome com ♭ aparece ali ao lado. Ver docs/03 (cada bemol recolore uma nota).
  const altered = keyAccidental(note.midi, fifths) !== 0
  const color = active ? theme.accent : altered ? theme.altered : theme.ink

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

  // Cabeça: cheia na maioria; aberta (anel) na mínima.
  const open = note.rhythm === "half"
  ctx.save()
  ctx.translate(note.x, y)
  ctx.rotate(-0.32)
  ctx.beginPath()
  ctx.ellipse(0, 0, L.lineGap * 0.48, L.lineGap * 0.36, 0, 0, Math.PI * 2)
  if (open) {
    ctx.strokeStyle = color
    ctx.lineWidth = L.lineGap * 0.14
    ctx.stroke()
  } else {
    ctx.fillStyle = color
    ctx.fill()
  }
  ctx.restore()

  // Ponto de aumento (pontuado): à direita da cabeça; sobe meio espaço quando a
  // nota está sobre uma linha, para o ponto cair no espaço acima.
  if (note.rhythm === "dotted") {
    const onLine = ((diatonicIndex(note.midi) - D3_INDEX) % 2) === 0
    const dotY = onLine ? y - L.lineGap * 0.5 : y
    ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(note.x + L.lineGap * 0.95, dotY, L.lineGap * 0.16, 0, Math.PI * 2)
    ctx.fill()
  }

  // Haste: notas acima da linha do meio (D3) levam haste para baixo.
  const rel = diatonicIndex(note.midi) - D3_INDEX
  const stemDown = rel > 0
  const stemX = stemDown ? note.x - L.lineGap * 0.44 : note.x + L.lineGap * 0.44
  const tipY = stemDown ? y + L.lineGap * 2 : y - L.lineGap * 2
  ctx.strokeStyle = color
  ctx.lineWidth = 1.6
  ctx.beginPath()
  ctx.moveTo(stemX, stemDown ? y + 2 : y - 2)
  ctx.lineTo(stemX, tipY)
  ctx.stroke()

  // Bandeirolas: colcheia (1) e semicolcheia (2) penduram da ponta da haste, de
  // volta na direção da cabeça (flagDir).
  const flags = note.rhythm === "eighth" ? 1 : note.rhythm === "sixteenth" ? 2 : 0
  if (flags > 0) drawFlags(ctx, stemX, tipY, stemDown ? -1 : 1, flags, L, color)
}

const HEART = "♥"
const HEART_RED = "#E5484D"
const HUD_SANS = "-apple-system, system-ui, sans-serif"

// Tamanhos/posições do HUD foram desenhados para headerH = 74 (o valor fixo
// antigo). Como headerH agora é proporcional (56–88, ver headerH(h)), todo texto
// do cabeçalho escala por hudScale = headerH(h)/74 — senão, em headerH pequeno
// (telas baixas), a 2ª linha (tom/música) mantinha sua posição Y fixa e vazava
// para dentro da pauta branca logo abaixo. Escalar posição E fonte junto resolve
// de vez (headerH sozinho não bastava).
const HEADER_DESIGN_H = 74

// Encolhe o font-size (nunca abaixo de minPx) até o texto medido caber em
// maxWidth. Mesmo princípio do headerH proporcional: medir de verdade em vez de
// supor espaço, para o subtítulo central (andamento/música) nunca colidir com o
// nível/tom à esquerda nem as vidas à direita — sobretudo em telas estreitas ou
// com títulos compostos mais longos (ex.: "Sixteenth Flourish").
function fitFontSize(ctx: CanvasRenderingContext2D, text: string, weight: number, basePx: number, minPx: number, maxWidth: number): number {
  let size = basePx
  while (size > minPx) {
    ctx.font = `${weight} ${size}px ${HUD_SANS}`
    if (ctx.measureText(text).width <= maxWidth) break
    size -= 1
  }
  return size
}

// Desenha nível+tom (esquerda) e vidas (direita); devolve as bordas internas
// (borda direita do bloco esquerdo, borda esquerda do bloco de vidas) e a
// posição Y da 2ª linha (tom) — a música central usa essa MESMA linha de base,
// escalada igual, para as duas colunas ficarem alinhadas e dentro do cabeçalho.
function drawHud(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  lives: number,
  level: number,
  fifths: number,
): { leftEdge: number; rightEdge: number; line1Y: number; line2Y: number; scale: number } {
  const sans = HUD_SANS
  const scale = headerH(h) / HEADER_DESIGN_H
  const line1Y = 33 * scale
  const line2Y = 56 * scale

  // Nível (esquerda) — 2 linhas: número do nível em destaque, tom abaixo.
  ctx.textAlign = "left"
  ctx.textBaseline = "alphabetic"
  ctx.fillStyle = theme.hud
  ctx.font = `600 ${28 * scale}px ${sans}` // mesmo tamanho E peso do andamento (Largo)
  const levelText = `Level ${level}`
  const levelW = ctx.measureText(levelText).width
  ctx.fillText(levelText, 16, line1Y)
  ctx.fillStyle = theme.muted
  ctx.font = `500 ${16 * scale}px ${sans}` // mesmo tamanho do nome da música
  const keyText = keyName(fifths)
  const keyW = ctx.measureText(keyText).width
  ctx.fillText(keyText, 16, line2Y)
  const leftEdge = 16 + Math.max(levelW, keyW)

  // Vidas (direita), na ordem coração = número, centralizado na vertical do
  // cabeçalho. Desenhado da direita p/ a esquerda: número → "=" → coração. Fonte
  // FIXA (não escala por `scale`): já fica centralizada por cy = headerH/2, então
  // nunca teve o risco de vazar pra pauta — escalar só encolhia sem necessidade.
  const cy = headerH(h) / 2
  ctx.textAlign = "right"
  ctx.textBaseline = "middle"
  const livesStr = String(lives)
  ctx.fillStyle = theme.hud
  ctx.font = `700 26px ${sans}`
  ctx.fillText(livesStr, w - 16, cy)
  let x = w - 16 - ctx.measureText(livesStr).width - 9
  ctx.fillText("=", x, cy)
  x -= ctx.measureText("=").width + 9
  ctx.fillStyle = HEART_RED
  ctx.font = `700 28px ${sans}`
  ctx.fillText(HEART, x, cy)
  const heartW = ctx.measureText(HEART).width
  const rightEdge = x - heartW

  return { leftEdge, rightEdge, line1Y, line2Y, scale }
}

function drawTempo(ctx: CanvasRenderingContext2D, w: number, name: string, color: string, maxHalfWidth: number, y: number, scale: number): void {
  const size = fitFontSize(ctx, name, 600, 28 * scale, 14 * scale, maxHalfWidth * 2)
  ctx.textAlign = "center"
  ctx.textBaseline = "alphabetic"
  ctx.fillStyle = color
  ctx.font = `600 ${size}px ${HUD_SANS}`
  ctx.fillText(name, w / 2, y)
}

export function drawScene(ctx: CanvasRenderingContext2D, scene: Scene): void {
  const { w, h, notes, lives, hitX, flash, tempoName, tempoColor, fifths, level, music, minMidi, maxMidi } = scene
  const L = layoutFor(w, h, minMidi, maxMidi)

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
  drawKeySignature(ctx, L, fifths, clefRight)

  ctx.strokeStyle = theme.accent
  ctx.lineWidth = 3
  ctx.beginPath()
  ctx.moveTo(hitX, L.panelTop + 6)
  ctx.lineTo(hitX, L.panelTop + L.panelH - 6)
  ctx.stroke()

  for (const note of notes) drawNote(ctx, note, L, hitX, fifths)

  const { leftEdge, rightEdge, line1Y, line2Y, scale } = drawHud(ctx, w, h, lives, level, fifths)
  // Meia-largura disponível pro subtítulo central sem invadir nível/tom (esquerda)
  // nem vidas (direita); GAP dá um respiro visível entre os blocos.
  const GAP = 14
  const maxHalfWidth = Math.max(20, Math.min(w / 2 - leftEdge, rightEdge - w / 2) - GAP)
  drawTempo(ctx, w, tempoName, tempoColor, maxHalfWidth, line1Y, scale)

  // Subtítulo central: a música/tema do nível (nível e tom já vão à esquerda).
  // Mesma linha de base (line2Y) e escala do tom — headerH pequeno (tela baixa)
  // encolhe as duas juntas, então o texto nunca vaza pra dentro da pauta abaixo.
  // Encolhe também se preciso pra nunca colidir com os blocos laterais (fitFontSize).
  if (music) {
    const size = fitFontSize(ctx, music, 500, 16 * scale, 10 * scale, maxHalfWidth * 2)
    ctx.textAlign = "center"
    ctx.textBaseline = "alphabetic"
    ctx.fillStyle = theme.muted
    ctx.font = `500 ${size}px ${HUD_SANS}`
    ctx.fillText(music, w / 2, line2Y)
  }

  if (flash > 0.02) {
    ctx.fillStyle = "#E24B4A"
    ctx.globalAlpha = flash * 0.16
    ctx.fillRect(0, 0, w, h)
    ctx.globalAlpha = 1
  }
}
