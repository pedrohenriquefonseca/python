// Biblioteca de fragmentos melódicos (docs/04-temas-e-musicas.md). Cada fragmento
// é escrito como GRAU da escala do nível (índice no `notePool`, 0 = tônica), não
// como midi absoluto — como o `notePool` de cada nível é sempre um prefixo
// contínuo da escala diatônica a partir de dó³ (ver `levels.ts`: HEXACHORD, TO_B3,
// TO_D4, TO_G4), o grau `i` sempre aponta para a nota certa em qualquer nível cujo
// pool alcance esse índice. A armadura (bemóis) já recolore o som via
// `soundingMidi` — o fragmento não muda entre tons.
//
// Melodias 1–4/6/8 são as canções já citadas em `melodySources`; ritmo simplificado
// para caber no `rhythmPool` liberado no nível onde tocam (ver docs/04, "a mesma
// música cresce com o jogador" — versão rítmica plena fica para o futuro). Os temas
// dos níveis 5/7/9/10/11 (antes "a definir") são COMPOSTOS para este jogo — não são
// canções de domínio público — desenhados para destacar o eixo pedagógico do
// nível: o grau recolorido pela armadura (5), a nova oitava (7), o silêncio (9), a
// síncope (10) e a semicolcheia (11).

import type { RhythmId } from "./rhythm"

export interface MelodyNote {
  degree: number // índice no notePool do nível (grau da escala); -1 = pausa
  rhythm: RhythmId
}

export interface Melody {
  id: string
  name: string
  notes: MelodyNote[]
}

const beat = (rhythm: RhythmId) => (...degrees: number[]): MelodyNote[] =>
  degrees.map((degree) => ({ degree, rhythm }))
const quarter = beat("quarter")
const half = beat("half")
const eighth = beat("eighth")
const dotted = beat("dotted")
const sixteenth = beat("sixteenth")
const REST: MelodyNote = { degree: -1, rhythm: "rest" }

export const MELODIES: Record<string, Melody> = {
  // --- Repertório conhecido (docs/04) ---------------------------------------
  hot_cross_buns: {
    id: "hot_cross_buns",
    name: "Hot Cross Buns",
    notes: quarter(2, 1, 0, 2, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 2, 1, 0),
  },
  mary_had_a_little_lamb: {
    id: "mary_had_a_little_lamb",
    name: "Mary Had a Little Lamb",
    // Versão pedagógica clássica de 3 notas (dó-ré-mi), sem sol.
    notes: quarter(2, 1, 0, 1, 2, 2, 2, 1, 1, 1, 2, 2, 2, 2, 1, 0, 1, 2, 2, 2, 2, 1, 1, 2, 1, 0),
  },
  ode_to_joy: {
    id: "ode_to_joy",
    name: "Ode to Joy",
    notes: [
      ...quarter(2, 2, 3, 4, 4, 3, 2, 1, 0, 0, 1, 2, 2),
      ...half(1),
      ...quarter(2, 2, 3, 4, 4, 3, 2, 1, 0, 0, 1, 2, 1),
      ...half(0),
    ],
  },
  frere_jacques: {
    id: "frere_jacques",
    name: "Frère Jacques",
    // Simplificado sem lá (fora do pool de dó³–sol³ do nível 2).
    notes: [
      ...quarter(0, 1, 2, 0, 0, 1, 2, 0),
      ...quarter(2, 3),
      ...half(4),
      ...quarter(2, 3),
      ...half(4),
      ...quarter(4, 4, 3, 2, 0),
      ...quarter(4, 4, 3, 2, 0),
      ...quarter(0, 4),
      ...half(0),
      ...quarter(0, 4),
      ...half(0),
    ],
  },
  jingle_bells_chorus: {
    id: "jingle_bells_chorus",
    name: "Jingle Bells",
    notes: [...quarter(2, 2, 2, 2, 2, 2, 2, 4, 0, 1), ...half(2)],
  },
  twinkle_twinkle: {
    id: "twinkle_twinkle",
    name: "Twinkle Twinkle Little Star",
    notes: [
      ...quarter(0, 0, 4, 4, 5, 5),
      ...half(4),
      ...quarter(3, 3, 2, 2, 1, 1),
      ...half(0),
    ],
  },
  london_bridge: {
    id: "london_bridge",
    name: "London Bridge",
    notes: [
      ...quarter(4, 3, 2, 3, 4, 4, 4, 3, 3, 3, 4, 1, 2, 3, 4, 3, 2, 3, 4, 4, 4, 4, 3, 2, 3, 4),
      ...half(0),
    ],
  },
  silent_night: {
    id: "silent_night",
    name: "Silent Night",
    notes: [
      ...dotted(2), ...eighth(3), ...quarter(2), ...half(0),
      ...dotted(2), ...eighth(3), ...quarter(2), ...half(0),
      ...half(4), ...quarter(4), ...quarter(2),
      ...half(3), ...quarter(3), ...quarter(1),
      ...dotted(2), ...eighth(3), ...quarter(4), ...quarter(5), ...eighth(4), ...eighth(3),
      ...dotted(2), ...eighth(3), ...quarter(2), ...half(0),
    ],
  },
  when_the_saints: {
    id: "when_the_saints",
    name: "When the Saints Go Marching In",
    notes: [
      ...quarter(0, 2, 3), ...half(4),
      ...quarter(0, 2, 3), ...half(4),
      ...quarter(0, 2, 3, 4, 2, 0),
      ...quarter(1), ...half(0),
    ],
  },

  // --- Temas compostos para os níveis antes "a definir" (docs/04) -----------
  flat_fanfare: {
    id: "flat_fanfare",
    name: "Flat Fanfare",
    // Nível 5 (Fá M): sobe até si (grau 6, o que a armadura recolore) e desce.
    notes: [
      ...quarter(0, 1, 2, 3),
      ...eighth(4, 5, 6, 5),
      ...quarter(4, 3, 2, 1),
      ...half(0),
    ],
  },
  octave_bridge: {
    id: "octave_bridge",
    name: "Octave Bridge",
    // Nível 7 (2ª oitava): atravessa a ponte sol³–ré⁴ (graus 4–8), a novidade do nível.
    notes: [
      ...quarter(4, 5, 6, 7),
      ...half(8),
      ...quarter(7, 6, 5),
      ...quarter(4, 3, 2, 1),
      ...half(0),
    ],
  },
  bugle_call: {
    id: "bugle_call",
    name: "Bugle Call",
    // Nível 9 (silêncio): arpejo de tônica subindo/descendo 2 oitavas, com pausas
    // no topo — estilo toque de corneta, temático para um trombone.
    notes: [
      ...quarter(0, 2, 4, 7, 9, 11),
      REST,
      ...quarter(11, 9, 7),
      REST,
      ...quarter(4, 2),
      ...half(0),
    ],
  },
  choro_skip: {
    id: "choro_skip",
    name: "Choro Skip",
    // Nível 10 (síncope): pares pontuado+colcheia (o "long-short" do choro/samba).
    notes: [
      ...dotted(0), ...eighth(1), ...quarter(2),
      ...dotted(4), ...eighth(3), ...quarter(2),
      ...dotted(1), ...eighth(0), REST,
      ...dotted(4), ...eighth(3), ...dotted(2), ...eighth(1), ...half(0),
    ],
  },
  sixteenth_flourish: {
    id: "sixteenth_flourish",
    name: "Sixteenth Flourish",
    // Nível 11 (semicolcheia): arpejo até o topo do âmbito com um floreio rápido.
    notes: [
      ...quarter(0, 2, 4, 7),
      ...sixteenth(8, 9, 10, 11),
      ...quarter(10, 9, 8),
      ...half(7),
      ...quarter(4, 3, 2, 1),
      ...half(0),
    ],
  },
}

// Sorteia um fragmento entre os ids liberados no nível (melodySources). null se
// nenhum id tiver dados na biblioteca (nível ainda 100% procedural).
export function pickMelody(ids: string[]): Melody | null {
  const available = ids.map((id) => MELODIES[id]).filter((m): m is Melody => m != null)
  if (available.length === 0) return null
  return available[Math.floor(Math.random() * available.length)]
}
