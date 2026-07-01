import type { Note, FloatingLabel } from "./types"
import { theme } from "../theme"
import { Particles } from "./particles"
import { drawScene, noteScreenY, hitXForKey } from "./render"
import { validPositionsForMidi, noteName } from "../data/slidePositions"
import { keyAccidental, soundingMidi } from "../data/keys"
import { tempoById, type Tempo, type TempoId } from "./tempo"
import { levelByNumber, LEVELS } from "./levels"
import { RHYTHMS, pickRhythm, type RhythmId, type RhythmFigure } from "./rhythm"
import { MELODIES, shuffledIds, type MelodyNote } from "./melodies"
import { Audio, MISS_LABELS, type MissSound } from "./audio"
import { hapticHit, hapticMiss } from "./haptics"
import { saveCurrentLevel, unlockLevel, clearProgress } from "./storage"
import type { LevelResult } from "./levelComplete"
import type { SpeedUpInfo } from "./speedUp"

// Intensidade fixa da explosão de acerto (antes escalava com o combo, removido).
const HIT_INTENSITY = 10

// Vidas: começa em MAX_LIVES, perde 1 por erro de nota (posição errada OU nota que
// passa sem ser tocada). Zerou → Game Over. Cada mudança de fase reenche.
const MAX_LIVES = 10

// Cota de notas (com altura — pausas não contam) que define uma "fase". Ao
// resolver essa quantidade, a porta de domínio (masteryGate) é avaliada. Ver
// docs/03.
const LEVEL_QUOTA = 28

// As 3 velocidades, na ordem em que se sobem dentro do MESMO nível (docs/03):
// todo nível estreia em Largo; passar a cota acelera para a próxima; passar em
// Andante (a última) libera o próximo nível. Sem estrelas/recorde — só precisão.
const TEMPO_STAGES: TempoId[] = ["largo", "adagio", "andante"]

export class Game {
  private ctx: CanvasRenderingContext2D
  private cssW = 0
  private cssH = 0
  private dpr = 1

  private notes: Note[] = []
  private labels: FloatingLabel[] = []
  private particles = new Particles()
  private audio = new Audio()
  private toast = ""
  private toastLife = 0
  private score = 0 // mantido p/ a futura tela de Game Over (resultado); não exibido
  private lives = MAX_LIVES
  private gameOver = false
  private flash = 0
  private shake = 0

  // Desempenho da fase atual (zera a cada resetRound). roundDone = notas com
  // altura resolvidas (acerto ou erro); roundHits = acertos. roundOver congela o
  // jogo enquanto a tela de fim de fase/game over decide o próximo passo.
  private roundDone = 0
  private roundHits = 0
  private roundOver = false
  // Preenchimento da barra "Trombone Slide Position" (DOM): dobra como medidor de
  // progresso da fase, crescendo da esquerda p/ a direita — evita um elemento
  // separado no canvas que colidiria com o HUD (ver render.ts, sem barra própria).
  private progressFillEl: HTMLDivElement | null = null

  private spawnAcc = 0
  // Todo nível (e toda troca de velocidade dentro dele) começa em Largo — quem
  // acelera é resetRound()/loadLevel(), nunca uma escolha de DEV/produção.
  private tempo: Tempo = tempoById(TEMPO_STAGES[0])
  private tempoStage: 0 | 1 | 2 = 0 // índice em TEMPO_STAGES da velocidade atual do nível
  // Estado dirigido pelo nível atual (ver loadLevel). O pool e os extremos do
  // intervalo definem as notas que entram e o tamanho da pauta; a armadura vem
  // junto. `[`/`]` navegam os níveis.
  private level = 1
  private music = "" // tema/música do nível atual (exibido no HUD central)
  private pool: number[] = []
  private rhythmPool: RhythmId[] = ["quarter"] // figuras liberadas no nível
  private nextSpawnIn = 0 // ms até a próxima nota (varia pela duração da anterior)
  private lastWasRest = false // evita duas pausas seguidas (silêncio longo estranho)
  private melodyIds: string[] = [] // melodySources do nível (ids em melodies.ts)
  private proceduralWeight = 1 // fração de sorteios que ficam procedurais (vs. melodia servida)
  private melodyQueue: MelodyNote[] = [] // notas restantes do fragmento em execução
  private melodyCycle: string[] = [] // ids do nível ainda não tocados nesta fase (embaralhados)
  private keySig = 0 // armadura do nível, em quintas (negativo = bemóis)
  private rangeMin = 48
  private rangeMax = 57
  private lastMidi = -1
  private lastTime = 0
  private running = false
  // Só persiste progresso depois que um jogo de fato começou (start). O loadLevel
  // do construtor não cria um "jogo salvo" — senão "Continuar" apareceria já na
  // 1ª abertura, sem nada para continuar.
  private active = false

  // Chamado uma vez quando as vidas zeram OU a cota fecha com < 80% de acerto —
  // mesmo tratamento por simplicidade. O main mostra a tela de game over e decide:
  // recomeçar a MESMA fase/velocidade (retryLevel) ou voltar ao menu.
  onGameOver?: () => void

  // Chamado ao passar a cota (≥ 80%) numa velocidade que não é a última. O main
  // mostra "vamos acelerar" e chama advanceTempo() para seguir na mesma fase.
  onSpeedUp?: (info: SpeedUpInfo) => void

  // Chamado ao passar a cota (≥ 80%) na última velocidade (Andante): o nível foi
  // dominado. O main mostra a tela de fim de nível e chama advanceLevel().
  onLevelComplete?: (result: LevelResult) => void

  constructor(
    private canvas: HTMLCanvasElement,
    private controls: HTMLElement,
  ) {
    const ctx = canvas.getContext("2d")
    if (!ctx) throw new Error("Canvas 2D indisponível")
    this.ctx = ctx
    this.buildButtons()
    this.loadLevel(1)
    this.resize()
    window.addEventListener("resize", () => this.resize())
    // Atalhos de teclado são apenas ferramentas de DEV/preview — o app nativo é só
    // toque e não tem teclado. Não embarcam em produção.
    if (import.meta.env.DEV) this.bindDevKeys()
  }

  // Teclado (DEV): 1-7 toca posição; `/q/w/e troca andamento; [ ] muda de nível;
  // m audita os sons de erro.
  private bindDevKeys(): void {
    window.addEventListener("keydown", (e) => {
      const n = parseInt(e.key, 10)
      if (n >= 1 && n <= 7) {
        this.press(n)
        return
      }
      const tempoKey: Record<string, TempoId> = { "`": "largo", q: "adagio", w: "andante" }
      const id = tempoKey[e.key.toLowerCase()]
      if (id) {
        this.setTempo(id)
        return
      }
      if (e.key === "[") this.loadLevel(this.level - 1) // nível anterior
      else if (e.key === "]") this.loadLevel(this.level + 1) // próximo nível
      else if (e.key.toLowerCase() === "m") this.cycleMissSound() // audita os sons de erro
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

  // Duração de 1 tempo em ms, com ~10% de folga p/ respiro (mantém o espaçamento de
  // semínima de antes). O intervalo até a próxima nota = beatMs × tempos da figura,
  // então a mínima nasce 2× mais cedo, a colcheia metade — o espaçamento na pauta
  // espelha a duração. (Independe do BPM no espaço: o andamento só muda a rolagem.)
  private get beatMs(): number {
    return 66000 / this.tempo.bpm
  }

  setTempo(id: TempoId): void {
    this.tempo = tempoById(id)
  }

  // Carrega um nível: define o pool de notas, a armadura e o intervalo (min..max)
  // que redimensiona a pauta. Todo nível novo estreia em Largo (tempoStage = 0).
  loadLevel(n: number): void {
    const lv = levelByNumber(n)
    this.level = lv.n
    this.music = lv.music
    this.pool = lv.notePool
    this.rhythmPool = lv.rhythmPool
    this.melodyIds = lv.melodySources
    this.proceduralWeight = lv.proceduralWeight
    this.keySig = lv.keySig
    this.rangeMin = Math.min(...lv.notePool)
    this.rangeMax = Math.max(...lv.notePool)
    this.tempoStage = 0
    this.tempo = tempoById(TEMPO_STAGES[0])
    this.resetRound()
    this.recomputeHitX()
    // Cada avanço de nível durante o jogo atualiza o "continuar" (preserva o liberado).
    if (this.active) saveCurrentLevel(this.level)
  }

  // Nível atual (para a tela de game over saber qual fase reiniciar/mostrar).
  get currentLevel(): number {
    return this.level
  }

  // Limpa o desempenho da fase (notas em tela, vidas, cota) sem tocar em
  // nível/velocidade — usado tanto ao carregar um nível quanto ao acelerar dentro
  // do mesmo nível (advanceTempo) e ao repetir a mesma tentativa (retryLevel).
  private resetRound(): void {
    this.melodyQueue = []
    this.melodyCycle = []
    this.notes = []
    this.lastMidi = -1
    this.lastWasRest = false
    this.spawnAcc = 0
    this.nextSpawnIn = this.beatMs // a 1ª nota da fase entra após ~1 tempo
    this.lives = MAX_LIVES // toda nova tentativa reenche as vidas
    this.gameOver = false
    this.roundDone = 0
    this.roundHits = 0
    this.roundOver = false
    this.updateProgressFill()
  }

  // Recomeça a MESMA tentativa (Retry do game over — vidas zeradas ou < 80% de
  // acerto na cota). Mantém nível e velocidade atuais: não é um nível novo, é a
  // mesma prova de novo.
  retryLevel(): void {
    this.score = 0
    this.labels = []
    this.resetRound()
  }

  // Acelera para a próxima velocidade dentro do MESMO nível (Largo→Adagio→Andante,
  // "vamos acelerar as coisas"). Conteúdo (notas/ritmo/armadura/melodias) não muda.
  advanceTempo(): void {
    this.score = 0
    this.labels = []
    this.tempoStage = Math.min(2, this.tempoStage + 1) as 0 | 1 | 2
    this.tempo = tempoById(TEMPO_STAGES[this.tempoStage])
    this.resetRound()
  }

  // Avança para o próximo nível (dominado nas 3 velocidades). levelByNumber satura
  // no último, então no nível 12 isto repete o 12 — o main só oferece isso quando
  // há próximo.
  advanceLevel(): void {
    this.score = 0
    this.labels = []
    this.loadLevel(this.level + 1)
  }

  // Para o loop (escolha "Home" do game over, antes de voltar ao menu).
  stop(): void {
    this.running = false
  }

  start(): void {
    if (this.running) return
    this.running = true
    // A partir daqui há um jogo em andamento: registra o ponto de continuação
    // (nível 1 num jogo novo, ou o nível retomado num "continuar").
    this.active = true
    saveCurrentLevel(this.level)
    this.lastTime = performance.now()
    requestAnimationFrame(this.frame)
  }

  press(pos: number): void {
    if (this.gameOver || this.roundOver) return // a tela de fim (DOM) cuida do resto
    this.flashButton(pos)
    let target: Note | null = null
    let bestDist = Infinity
    for (const note of this.notes) {
      if (RHYTHMS[note.rhythm].isRest) continue // pausa não se toca: invisível ao julgamento
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
    const acc = keyAccidental(note.midi, this.keySig)
    this.labels.push({
      text: noteName(note.midi) + (acc < 0 ? "♭" : acc > 0 ? "♯" : ""),
      x: this.hitX,
      y: noteScreenY(note.midi, this.cssW, this.cssH, this.rangeMin, this.rangeMax),
      life: 0.9,
      maxLife: 0.9,
      color,
      size,
    })
  }

  private resolveHit(note: Note): void {
    this.score += 10
    // Som da nota na altura soante (com a armadura), pela duração da figura: 1 tempo
    // = 60/bpm s, então a mínima soa 2 tempos, a colcheia meio, etc.
    this.audio.playNote(soundingMidi(note.midi, this.keySig), (60 / this.tempo.bpm) * RHYTHMS[note.rhythm].beats)
    hapticHit() // feedback tátil leve no acerto
    this.particles.explode(this.hitX, noteScreenY(note.midi, this.cssW, this.cssH, this.rangeMin, this.rangeMax), theme.accent, HIT_INTENSITY)
    this.addLabel(note, theme.accent, 28)
    this.remove(note)
    this.roundHits++
    this.countNote() // acerto conta para a cota da fase
  }

  private resolveMiss(note: Note, wrong: boolean): void {
    this.flash = Math.max(this.flash, wrong ? 1 : 0.6)
    if (wrong) {
      this.shake = 8
      this.audio.playMiss() // som de erro só na posição errada (não no tempo esgotado)
      hapticMiss() // feedback tátil forte e abrupto no erro
    }
    this.particles.puff(this.hitX, noteScreenY(note.midi, this.cssW, this.cssH, this.rangeMin, this.rangeMax), theme.muted)
    this.addLabel(note, theme.muted, 24)
    this.remove(note)
    this.loseLife() // todo erro de nota custa 1 vida
    this.countNote() // erro também conta para a cota (puxa a precisão p/ baixo)
  }

  // Uma nota (com altura) foi resolvida: avança a cota e, ao completá-la, fecha a
  // fase. Game over (vidas = 0) tem prioridade — não avalia domínio se já perdeu.
  private countNote(): void {
    this.roundDone++
    this.updateProgressFill()
    if (!this.gameOver && this.roundDone >= LEVEL_QUOTA) this.endRound()
  }

  // Sincroniza a largura do preenchimento da barra "Trombone Slide Position" com o
  // progresso da fase (0 → LEVEL_QUOTA).
  private updateProgressFill(): void {
    if (!this.progressFillEl) return
    const frac = Math.max(0, Math.min(1, this.roundDone / LEVEL_QUOTA))
    this.progressFillEl.style.width = `${frac * 100}%`
  }

  // Avalia a porta de domínio ao fim da cota e congela o jogo. < 80%: cai na MESMA
  // lógica de game over (sem tela "quase lá" separada — simplicidade). ≥ 80% e
  // ainda não é a última velocidade: acelera (Largo→Adagio→Andante), mesmo
  // conteúdo. ≥ 80% na última (Andante): libera e avança para o próximo nível.
  private endRound(): void {
    if (this.roundOver) return
    this.roundOver = true
    const accuracy = this.roundDone > 0 ? this.roundHits / this.roundDone : 0
    const gate = levelByNumber(this.level).masteryGate
    if (accuracy < gate.minAccuracy) {
      this.triggerGameOver()
      return
    }
    if (this.tempoStage < 2) {
      this.onSpeedUp?.({
        level: this.level,
        music: this.music,
        nextTempoName: tempoById(TEMPO_STAGES[this.tempoStage + 1]).name,
      })
    } else {
      unlockLevel(Math.min(LEVELS.length, this.level + 1))
      this.onLevelComplete?.({ level: this.level, music: this.music, accuracy })
    }
  }

  // Perde 1 vida; ao zerar, dispara o Game Over (congela em update()).
  private loseLife(): void {
    this.lives = Math.max(0, this.lives - 1)
    if (this.lives === 0) this.triggerGameOver()
  }

  // Fim de jogo: zerou vidas OU não atingiu 80% de acerto na cota (mesmo
  // tratamento — sem tela separada). Reaproveita a tela de Game Over: Retry
  // mantém nível/velocidade atuais (ver retryLevel), Home volta ao menu.
  private triggerGameOver(): void {
    this.gameOver = true
    clearProgress() // o jogo acabou: não há mais o que "continuar" pelo menu
    this.onGameOver?.() // o main exibe a tela de game over
  }

  // Alterna entre as 3 alternativas de som de erro e toca um preview, mostrando
  // qual está ativa. Temporário, para escolhermos uma.
  private cycleMissSound(): void {
    const order: MissSound[] = ["buzz", "sadTrombone", "thud"]
    const next = order[(order.indexOf(this.audio.missSound) + 1) % order.length]
    this.audio.missSound = next
    this.audio.playMiss()
    this.toast = `Erro: ${MISS_LABELS[next]}`
    this.toastLife = 1.8
  }

  private buildButtons(): void {
    this.controls.innerHTML = ""

    const label = document.createElement("div")
    label.className = "controls-label"
    const fill = document.createElement("div")
    fill.className = "controls-fill"
    label.appendChild(fill)
    this.progressFillEl = fill
    const text = document.createElement("span")
    text.className = "controls-label-text"
    text.textContent = "Trombone Slide Position"
    label.appendChild(text)
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
    this.hitXValue = Math.max(
      110,
      hitXForKey(this.ctx, this.cssW, this.cssH, Math.abs(this.keySig), this.rangeMin, this.rangeMax),
    )
  }

  private spawn(): void {
    // Entre fragmentos, cada sorteio tem chance (1 - proceduralWeight) de começar
    // um fragmento de melodia do nível; uma vez iniciado, toca até o fim antes do
    // próximo sorteio. Os fragmentos CIRCULAM sem repetir (melodyCycle) até
    // esgotar e reembaralhar — a fase (agora mais longa) acaba expondo todas as
    // melodias do nível, não só a sorteada por acaso. Sem melodySources ou puro
    // azar → procedural.
    if (this.melodyQueue.length === 0 && this.melodyIds.length > 0 && Math.random() >= this.proceduralWeight) {
      if (this.melodyCycle.length === 0) this.melodyCycle = shuffledIds(this.melodyIds)
      const frag = MELODIES[this.melodyCycle.shift()!]
      if (frag) this.melodyQueue = [...frag.notes]
    }

    const fromMelody = this.melodyQueue.length > 0
    // Figura rítmica: da melodia em execução, ou sorteada do nível (peso puxa p/
    // semínima); evita duas pausas procedurais seguidas (silêncio longo estranho).
    let fig: RhythmFigure
    let degree = -1
    if (fromMelody) {
      const next = this.melodyQueue.shift()!
      fig = RHYTHMS[next.rhythm]
      degree = next.degree
    } else {
      fig = pickRhythm(this.rhythmPool)
      if (fig.isRest && this.lastWasRest) fig = pickRhythm(this.rhythmPool)
    }
    this.lastWasRest = fig.isRest
    // A próxima nota nasce após a duração desta — o espaçamento na pauta espelha a
    // figura, seja ela procedural ou da melodia.
    this.nextSpawnIn = this.beatMs * fig.beats

    if (fig.isRest) {
      // Pausa: sem altura nem posição de vara (D3 só p/ ter um midi seguro; o render
      // desenha o glifo na linha do meio e ignora a altura).
      this.notes.push({ midi: 50, x: this.cssW + 30, positions: [], rhythm: fig.id })
      return
    }

    const pool = this.pool
    // Grau da melodia mapeia direto no notePool (índice = grau da escala, 0 =
    // tônica — ver melodies.ts); sem melodia, sorteia evitando repetir a última.
    let midi: number
    if (fromMelody) {
      midi = pool[degree] ?? pool[0]
    } else {
      midi = pool[Math.floor(Math.random() * pool.length)]
      while (pool.length > 1 && midi === this.lastMidi) midi = pool[Math.floor(Math.random() * pool.length)]
    }
    this.lastMidi = midi
    this.notes.push({
      midi,
      x: this.cssW + 30,
      // A nota é desenhada na linha natural (midi), mas a armadura define a altura
      // soante — e, portanto, a posição de vara correta.
      positions: validPositionsForMidi(soundingMidi(midi, this.keySig)),
      rhythm: fig.id,
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
    if (this.gameOver || this.roundOver) {
      // Congela o jogo; só deixa partículas/flash assentarem sob o overlay (game
      // over ou fim de fase).
      this.particles.update(s)
      this.flash *= Math.pow(0.88, s)
      this.shake *= Math.pow(0.82, s)
      return
    }

    this.spawnAcc += dt
    if (this.spawnAcc >= this.nextSpawnIn) {
      this.spawnAcc = 0
      this.spawn() // spawn() define o próximo nextSpawnIn pela figura sorteada
    }

    const dx = this.speed * (dt / 1000)
    for (const note of this.notes) note.x -= dx

    // Nota que chega na linha sem ser acertada: resolve e some ali mesmo. A pausa
    // cruza em silêncio — é o comportamento correto (não tocar), sem perder vida.
    for (const note of [...this.notes]) {
      if (note.x > this.hitX) continue
      if (RHYTHMS[note.rhythm].isRest) this.remove(note)
      else this.resolveMiss(note, false)
    }

    this.particles.update(s)

    for (const label of this.labels) label.life -= dt / 1000
    this.labels = this.labels.filter((l) => l.life > 0)

    this.flash *= Math.pow(0.88, s)
    this.shake *= Math.pow(0.82, s)
    if (this.toastLife > 0) this.toastLife -= dt / 1000
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
      ctx.fillText(label.text, label.x - 14, label.y)
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
      lives: this.lives,
      hitX: this.hitX,
      flash: this.flash,
      tempoName: this.tempo.name,
      tempoColor: this.tempo.color,
      fifths: this.keySig,
      level: this.level,
      music: this.music,
      minMidi: this.rangeMin,
      maxMidi: this.rangeMax,
    })
    this.particles.draw(ctx)
    this.drawLabels()
    this.drawToast()
    ctx.restore()
  }

  // Aviso temporário (centro/inferior) ao alternar o som de erro com a tecla `m`.
  private drawToast(): void {
    if (this.toastLife <= 0) return
    const ctx = this.ctx
    const cx = this.cssW / 2
    const cy = this.cssH - 24
    ctx.save()
    ctx.globalAlpha = Math.min(1, this.toastLife / 0.4)
    ctx.font = `600 15px -apple-system, system-ui, sans-serif`
    ctx.textAlign = "center"
    ctx.textBaseline = "middle"
    // Pílula escura por trás para o texto ler sobre a pauta branca.
    const padX = 14
    const w = ctx.measureText(this.toast).width + padX * 2
    ctx.fillStyle = "rgba(15,18,28,0.9)"
    ctx.beginPath()
    ctx.roundRect(cx - w / 2, cy - 15, w, 30, 15)
    ctx.fill()
    ctx.fillStyle = theme.accent
    ctx.fillText(this.toast, cx, cy)
    ctx.restore()
  }
}
