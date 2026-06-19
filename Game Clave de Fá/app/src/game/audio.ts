// Áudio do jogo via Web Audio API (sem dependências).
//
// - playNote: som da nota acertada, com timbre de metal (sopro) e a DURAÇÃO do
//   valor da nota — hoje todas são semínimas, então 1 tempo = 60/bpm segundos.
// - playMiss: som de erro. Há 3 alternativas para escolher (ver MissSound); troque
//   `missSound` para auditar cada uma.

export type MissSound = "buzz" | "sadTrombone" | "thud"

export const MISS_LABELS: Record<MissSound, string> = {
  buzz: "Buzz grave (dissonante)",
  sadTrombone: "Trombone triste (wah-wah)",
  thud: "Toque suave",
}

const A4 = 440
const midiToFreq = (midi: number): number => A4 * Math.pow(2, (midi - 69) / 12)

export class Audio {
  private ctx: AudioContext | null = null
  private master: GainNode | null = null

  // Alternativa de som de erro ativa.
  missSound: MissSound = "buzz"

  // Cria/retoma o contexto. Deve ser chamado a partir de um gesto do usuário
  // (press), senão o navegador mantém o áudio suspenso.
  private ensure(): AudioContext {
    if (!this.ctx) {
      const Ctor = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      this.ctx = new Ctor()
      this.master = this.ctx.createGain()
      this.master.gain.value = 0.45
      this.master.connect(this.ctx.destination)
    }
    if (this.ctx.state === "suspended") void this.ctx.resume()
    return this.ctx
  }

  // Nota acertada: timbre de trombone. Espectro harmônico de metal (PeriodicWave)
  // em dois osciladores levemente desafinados (calor), formante de brass (~520 Hz),
  // vibrato sutil que entra depois do ataque e envelope de "tonguing". `dur` é a
  // duração indicada (1 tempo = 60/bpm).
  playNote(midi: number, dur: number): void {
    const ctx = this.ensure()
    const now = ctx.currentTime
    const freq = midiToFreq(midi)
    const wave = this.tromboneWave(ctx)

    // Dois osciladores ±4 cents: a leve batida de afinação dá vida/corpo.
    const osc1 = ctx.createOscillator()
    osc1.setPeriodicWave(wave)
    osc1.frequency.value = freq
    osc1.detune.value = -4
    const osc2 = ctx.createOscillator()
    osc2.setPeriodicWave(wave)
    osc2.frequency.value = freq
    osc2.detune.value = 4

    // Vibrato suave (~5,2 Hz) que cresce após o ataque — não no transiente inicial.
    const lfo = ctx.createOscillator()
    lfo.type = "sine"
    lfo.frequency.value = 5.2
    const lfoGain = ctx.createGain()
    lfoGain.gain.setValueAtTime(0, now)
    lfoGain.gain.linearRampToValueAtTime(freq * 0.006, now + Math.min(0.3, dur * 0.5))
    lfo.connect(lfoGain)
    lfoGain.connect(osc1.detune)
    lfoGain.connect(osc2.detune)

    // Formante do trombone: realce suave em ~480 Hz (sem nasalidade exagerada).
    const formant = ctx.createBiquadFilter()
    formant.type = "peaking"
    formant.frequency.value = 480
    formant.Q.value = 0.9
    formant.gain.value = 3

    // Bloom de brilho contido: abre um pouco no ataque e recua no sustain, com teto
    // baixo para um som quente e arredondado (não metálico).
    const lp = ctx.createBiquadFilter()
    lp.type = "lowpass"
    lp.Q.value = 0.5
    lp.frequency.setValueAtTime(Math.min(freq * 2.5, 800), now)
    lp.frequency.linearRampToValueAtTime(Math.min(freq * 5, 2800), now + 0.09)
    lp.frequency.linearRampToValueAtTime(Math.min(freq * 3.5, 2000), now + dur)

    // Envelope: ataque de tonguing (~40 ms), pequeno settle e release curto.
    const env = ctx.createGain()
    const attack = 0.04
    const release = Math.min(0.13, dur * 0.4)
    const sustainEnd = now + Math.max(0.08, dur - release)
    env.gain.setValueAtTime(0.0001, now)
    env.gain.exponentialRampToValueAtTime(0.5, now + attack)
    env.gain.linearRampToValueAtTime(0.42, now + attack + 0.07) // assenta após o "blat"
    env.gain.setValueAtTime(0.42, sustainEnd)
    env.gain.exponentialRampToValueAtTime(0.001, sustainEnd + release)

    osc1.connect(formant)
    osc2.connect(formant)
    formant.connect(lp).connect(env).connect(this.master!)

    const stop = sustainEnd + release + 0.03
    osc1.start(now)
    osc2.start(now)
    lfo.start(now)
    osc1.stop(stop)
    osc2.stop(stop)
    lfo.stop(stop)
  }

  // Espectro harmônico de trombone (mf, registro médio): fundamental forte e queda
  // gradual dos parciais. Memoizado por contexto.
  private tromboneWaveCache: PeriodicWave | null = null
  private tromboneWave(ctx: AudioContext): PeriodicWave {
    if (this.tromboneWaveCache) return this.tromboneWaveCache
    // Rolloff acentuado dos agudos: fundamental dominante, poucos parciais altos —
    // som quente e redondo, sem o "zumbido" metálico das serras.
    const amps = [0, 1.0, 0.68, 0.4, 0.22, 0.12, 0.07, 0.04, 0.02]
    const real = new Float32Array(new ArrayBuffer(amps.length * 4))
    const imag = new Float32Array(new ArrayBuffer(amps.length * 4))
    amps.forEach((a, i) => (imag[i] = a))
    this.tromboneWaveCache = ctx.createPeriodicWave(real, imag)
    return this.tromboneWaveCache
  }

  playMiss(): void {
    switch (this.missSound) {
      case "buzz":
        return this.missBuzz()
      case "sadTrombone":
        return this.missSadTrombone()
      case "thud":
        return this.missThud()
    }
  }

  // (1) Buzz grave: díade de serras a um semitom (D3 + Eb3) — "errou" áspero, com
  // cara de pedal/flubbed note do trombone. Curto e PUNCHY: ataque quase
  // instantâneo, queda rápida de tom (o soco), sub para corpo e saturação leve
  // para presença/grão.
  private missBuzz(): void {
    const ctx = this.ensure()
    const now = ctx.currentTime

    // Soft-clip para grão e presença.
    const shaper = ctx.createWaveShaper()
    shaper.curve = this.driveCurve()
    shaper.oversample = "2x"

    const filter = ctx.createBiquadFilter()
    filter.type = "lowpass"
    filter.Q.value = 6
    filter.frequency.setValueAtTime(2600, now) // abre no ataque
    filter.frequency.exponentialRampToValueAtTime(700, now + 0.16) // fecha rápido

    // Envelope seco: ataque ~instantâneo, decay curto.
    const env = ctx.createGain()
    env.gain.setValueAtTime(0.0001, now)
    env.gain.exponentialRampToValueAtTime(0.85, now + 0.005)
    env.gain.exponentialRampToValueAtTime(0.001, now + 0.19)

    shaper.connect(filter).connect(env).connect(this.master!)

    // Díade dissonante com queda rápida de tom -> punch percussivo.
    for (const f of [146.83, 155.56]) {
      const o = ctx.createOscillator()
      o.type = "sawtooth"
      o.frequency.setValueAtTime(f * 1.5, now)
      o.frequency.exponentialRampToValueAtTime(f, now + 0.035)
      o.connect(shaper)
      o.start(now)
      o.stop(now + 0.2)
    }

    // Sub limpo (bypassa a distorção) para o thump/corpo do soco.
    const sub = ctx.createOscillator()
    sub.type = "square"
    sub.frequency.value = 73.4 // D2
    const subGain = ctx.createGain()
    subGain.gain.value = 0.45
    sub.connect(subGain).connect(env)
    sub.start(now)
    sub.stop(now + 0.18)
  }

  // Curva de soft-clip (tanh-like) reaproveitada pelo buzz. Memoizada.
  private shaperCurve: Float32Array<ArrayBuffer> | null = null
  private driveCurve(): Float32Array<ArrayBuffer> {
    if (this.shaperCurve) return this.shaperCurve
    const n = 1024
    const curve = new Float32Array(new ArrayBuffer(n * 4))
    const k = 8 // quantidade de distorção
    for (let i = 0; i < n; i++) {
      const x = (i / (n - 1)) * 2 - 1
      curve[i] = ((1 + k) * x) / (1 + k * Math.abs(x))
    }
    this.shaperCurve = curve
    return curve
  }

  // (2) Trombone triste: o clássico "wah-wah-wah-waaah" descendente. Quatro notas
  // re-articuladas (Db4 C4 B3 Bb3), cada uma com um leve scoop de vara; a última
  // sustenta mais com vibrato.
  private missSadTrombone(): void {
    const ctx = this.ensure()
    const now = ctx.currentTime
    const base = midiToFreq(58) // Bb3

    const filter = ctx.createBiquadFilter()
    filter.type = "lowpass"
    filter.frequency.value = 1600
    filter.Q.value = 3
    filter.connect(this.master!)

    const semis = [3, 2, 1, 0] // Db4, C4, B3, Bb3
    const step = 0.2
    semis.forEach((s, i) => {
      const last = i === semis.length - 1
      const t = now + i * step
      const f = base * Math.pow(2, s / 12)
      const dur = last ? 0.5 : step * 0.95

      const o = ctx.createOscillator()
      o.type = "sawtooth"
      o.frequency.setValueAtTime(f * 1.04, t) // scoop de vara para a nota
      o.frequency.exponentialRampToValueAtTime(f, t + 0.05)

      const g = ctx.createGain()
      g.gain.setValueAtTime(0.0001, t)
      g.gain.exponentialRampToValueAtTime(0.5, t + 0.02)
      g.gain.setValueAtTime(0.45, t + dur * 0.6)
      g.gain.exponentialRampToValueAtTime(0.001, t + dur)
      o.connect(g).connect(filter)

      if (last) {
        const lfo = ctx.createOscillator()
        lfo.frequency.value = 6
        const lfoGain = ctx.createGain()
        lfoGain.gain.value = 4
        lfo.connect(lfoGain).connect(o.frequency)
        lfo.start(t)
        lfo.stop(t + dur + 0.03)
      }

      o.start(t)
      o.stop(t + dur + 0.03)
    })
  }

  // (3) Toque suave: "thunk" grave e curto que desce de tom, passa-baixa fechado —
  // um erro discreto, nada punitivo, bom para repetição.
  private missThud(): void {
    const ctx = this.ensure()
    const now = ctx.currentTime

    const o = ctx.createOscillator()
    o.type = "triangle"
    o.frequency.setValueAtTime(165, now)
    o.frequency.exponentialRampToValueAtTime(80, now + 0.16)

    const filter = ctx.createBiquadFilter()
    filter.type = "lowpass"
    filter.frequency.value = 420

    const g = ctx.createGain()
    g.gain.setValueAtTime(0.0001, now)
    g.gain.exponentialRampToValueAtTime(0.4, now + 0.01)
    g.gain.exponentialRampToValueAtTime(0.001, now + 0.2)

    o.connect(filter).connect(g).connect(this.master!)
    o.start(now)
    o.stop(now + 0.24)
  }
}
