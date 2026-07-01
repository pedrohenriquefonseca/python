import { nameToMidi } from "../data/slidePositions"
import { keyName } from "../data/keys"
import type { TempoId } from "./tempo"
import { type RhythmId, rhythmPool } from "./rhythm"

export type { RhythmId }

// Os 12 níveis como DADOS — a fundação que o gerador de exercícios, o motor de
// ritmo e a porta de domínio (mastery gate) leem. Ver
// docs/03-progressao-de-dificuldade.md (curva, armaduras, ritmo) e
// docs/04-temas-e-musicas.md (repertório). Cada eixo (notas, figuras, armadura,
// andamento) avança um de cada vez; aqui ficam os parâmetros, não a lógica.
//
// O intervalo min..max do notePool é o que redimensiona a pauta: níveis 1–6 cabem
// nas 5 linhas (pauta compacta); a 2ª oitava (níveis 7+) abre linhas suplementares
// acima (allowLedger) e a pauta encolhe sozinha.

// Porta de domínio: critério simples (sem estrelas/recorde) para passar de uma
// velocidade para a próxima e, na última, liberar o próximo nível. Hoje uniforme
// conforme o esboço de docs/03; dá para afinar a curva por nível depois sem mexer
// em quem consome.
export interface MasteryGate {
  minAccuracy: number // fração 0..1 de notas certas exigida (80–100% passa)
}

export interface Level {
  n: number // número do nível (1-based)
  id: string // "n01".."n12"
  notePool: number[] // notas em jogo (MIDI)
  rhythmPool: RhythmId[] // figuras liberadas (acumulativo pela curva)
  keySig: number // armadura em quintas: 0=Dó, -1=Fá, -2=Si♭, -3=Mi♭, -4=Lá♭
  key: string // rótulo legível da tonalidade (derivado de keySig)
  allowLedger: boolean // permite linhas suplementares acima (2ª oitava)
  tempos: Record<TempoId, number> // BPM por andamento (ver tempo.ts)
  melodySources: string[] // ids de temas de docs/04; [] = ainda a definir
  proceduralWeight: number // 0..1 — fração de exercícios gerados vs. melodia servida
  masteryGate: MasteryGate // critério para dominar o nível (libera o próximo)
  music: string // rótulo curto do tema, exibido no HUD central
}

const pool = (...names: string[]): number[] => names.map(nameToMidi)

// Crescimento do âmbito ao longo da curva (docs/03, coluna "Notas").
const HEXACHORD = ["C3", "D3", "E3", "F3", "G3", "A3"] // níveis 1–3 (centro/pauta cheia)
const TO_B3 = [...HEXACHORD, "B3"] // dó³–si³ (níveis 4–6)
const TO_D4 = [...TO_B3, "C4", "D4"] // + 2ª oitava parcial (nível 7)
const TO_G4 = [...TO_B3, "C4", "D4", "E4", "F4", "G4"] // extensão completa (níveis 8+)

// Os 3 andamentos valem para todos os níveis (o andamento é eixo ortogonal: aperta
// cada nível, não avança o conteúdo). Mantido por nível porque o esboço o prevê e
// permite, no futuro, um nível com janela própria.
const TEMPOS: Record<TempoId, number> = { largo: 40, adagio: 66, andante: 92 }

// Critério de domínio padrão (esboço de docs/03). Uniforme por ora.
const GATE: MasteryGate = { minAccuracy: 0.8 }

interface LevelSpec {
  notes: string[]
  rhythmCount: number // quantas figuras da RHYTHM_ORDER estão liberadas
  keySig: number
  melodySources: string[]
  proceduralWeight: number
  music: string
}

const mk = (n: number, s: LevelSpec): Level => {
  const notePool = pool(...s.notes)
  return {
    n,
    id: `n${String(n).padStart(2, "0")}`,
    notePool,
    rhythmPool: rhythmPool(s.rhythmCount),
    keySig: s.keySig,
    key: keyName(s.keySig),
    allowLedger: notePool.some((m) => m >= 60), // dó⁴ (MIDI 60) e acima exigem suplementares
    tempos: TEMPOS,
    melodySources: s.melodySources,
    proceduralWeight: s.proceduralWeight,
    masteryGate: GATE,
    music: s.music,
  }
}

// Os 12 níveis (docs/03 tabela síntese + docs/04 repertório). melodySources
// referencia ids de `melodies.ts` (MELODIES); [] = nenhum fragmento ainda (nível
// 12, "free play", é só procedural de propósito).
export const LEVELS: Level[] = [
  mk(1, { notes: ["C3", "D3", "E3"], rhythmCount: 1, keySig: 0, music: "Hot Cross Buns", proceduralWeight: 0.3, melodySources: ["hot_cross_buns", "mary_had_a_little_lamb"] }),
  mk(2, { notes: ["C3", "D3", "E3", "F3", "G3"], rhythmCount: 2, keySig: 0, music: "Ode to Joy", proceduralWeight: 0.3, melodySources: ["ode_to_joy", "frere_jacques", "jingle_bells_chorus"] }),
  mk(3, { notes: HEXACHORD, rhythmCount: 3, keySig: 0, music: "Twinkle Twinkle", proceduralWeight: 0.3, melodySources: ["twinkle_twinkle", "london_bridge"] }),
  mk(4, { notes: TO_B3, rhythmCount: 3, keySig: 0, music: "London Bridge", proceduralWeight: 0.3, melodySources: ["london_bridge", "mary_had_a_little_lamb"] }),
  mk(5, { notes: TO_B3, rhythmCount: 3, keySig: -1, music: "Flat Fanfare", proceduralWeight: 0.5, melodySources: ["flat_fanfare"] }),
  mk(6, { notes: TO_B3, rhythmCount: 4, keySig: -2, music: "Silent Night", proceduralWeight: 0.3, melodySources: ["silent_night"] }),
  mk(7, { notes: TO_D4, rhythmCount: 4, keySig: -2, music: "Octave Bridge", proceduralWeight: 0.5, melodySources: ["octave_bridge"] }),
  mk(8, { notes: TO_G4, rhythmCount: 4, keySig: -2, music: "When the Saints", proceduralWeight: 0.3, melodySources: ["when_the_saints"] }),
  mk(9, { notes: TO_G4, rhythmCount: 5, keySig: -3, music: "Bugle Call", proceduralWeight: 0.5, melodySources: ["bugle_call"] }),
  mk(10, { notes: TO_G4, rhythmCount: 5, keySig: -3, music: "Choro Skip", proceduralWeight: 0.5, melodySources: ["choro_skip"] }),
  mk(11, { notes: TO_G4, rhythmCount: 6, keySig: -4, music: "Sixteenth Flourish", proceduralWeight: 0.5, melodySources: ["sixteenth_flourish"] }),
  mk(12, { notes: TO_G4, rhythmCount: 6, keySig: 0, music: "Free play", proceduralWeight: 0.5, melodySources: [] }),
]

export function levelByNumber(n: number): Level {
  const i = Math.max(1, Math.min(LEVELS.length, n)) - 1
  return LEVELS[i]
}
