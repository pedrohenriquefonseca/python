# Temas e músicas

O repertório que dá musicalidade ao jogo e o motor que o serve. A curva que esses
temas acompanham está em [`03-progressao-de-dificuldade.md`](03-progressao-de-dificuldade.md).

## Motor de musicalidade (implementado 30/jun)

Biblioteca de fragmentos em `app/src/game/melodies.ts` (`MELODIES`). Cada fragmento
é escrito como **grau da escala** (índice no `notePool` do nível, 0 = tônica) em vez
de nota absoluta — como o `notePool` de cada nível é sempre um prefixo contínuo da
escala diatônica a partir de dó³ (`HEXACHORD`/`TO_B3`/`TO_D4`/`TO_G4` em
`levels.ts`), o grau `i` sempre cai na nota certa em qualquer nível cujo pool
alcance esse índice — **não há transposição explícita**: a armadura recolore o som
via `soundingMidi`, o fragmento é o mesmo em qualquer tom.

Cada fragmento é `{ id, name, notes: { degree, rhythm }[] }` — sem metadados
separados de (notas/ritmos/âmbito): eles são deriváveis da própria sequência.

`Game.spawn` (Game.ts) sorteia, entre um fragmento e outro, se inicia um novo (peso
`1 - proceduralWeight` do nível) ou sorteia nota+ritmo procedural; uma vez iniciado,
o fragmento toca até o fim antes do próximo sorteio. **Circulam sem repetir**
(`melodyCycle`, embaralhado por `shuffledIds` — 1/jul): em vez de sortear com
reposição (podendo repetir a mesma melodia várias vezes e nunca tocar outra), o
nível esgota todos os seus `melodySources` embaralhados antes de reembaralhar —
garante que a fase (agora mais longa, ver `docs/03` "Fase estendida") exponha
todas as músicas do nível.

## Repertório por nível

Mapa de quais temas entram em cada um dos 12 níveis (ver tabela em
[`03-progressao-de-dificuldade.md`](03-progressao-de-dificuldade.md)):

| # | Notas / armadura | Música-recompensa |
|---|---|---|
| 1 | dó³ ré³ mi³ · Dó M | Hot Cross Buns, Mary Had a Little Lamb |
| 2 | + fá³ sol³ · Dó M | Hino à Alegria, Frère Jacques, refrão de Jingle Bells |
| 3 | + lá³ (hexacorde) · Dó M | Brilha Brilha Estrelinha, London Bridge |
| 4 | + si³ · Dó M | London Bridge, Mary (variações) |
| 5 | dó³–si³ · **Fá M** | Flat Fanfare *(composto — sobe até si, o grau recolorido pela armadura)* |
| 6 | dó³–si³ · **Si♭ M** | Noite Feliz |
| 7 | + dó⁴ ré⁴ · Si♭ M | Octave Bridge *(composto — atravessa sol³–ré⁴, a novidade do nível)* |
| 8 | + mi⁴ fá⁴ sol⁴ · Si♭ M | When the Saints Go Marching In |
| 9 | dó³–sol⁴ · **Mi♭ M** | Bugle Call *(composto — arpejo de tônica com pausas, estilo corneta)* |
| 10 | dó³–sol⁴ · Mi♭ M | Choro Skip *(composto — pares pontuado+colcheia, a síncope do nível)* |
| 11 | dó³–sol⁴ · **Lá♭ M** | Sixteenth Flourish *(composto — floreio de semicolcheia no topo do âmbito)* |
| 12 | dó³–sol⁴ · revisão 0–4♭ | livre |

## Truque pedagógico: a mesma música cresce com o jogador

**A mesma música reaparece em níveis mais altos com fidelidade rítmica e tonal
crescente** — primeiro só semínimas, depois ritmo autêntico, depois (quando a
armadura permitir) o tom mais próximo do original. Reforça o reconhecimento e dá
sensação de progresso. Ex.: Brilha Brilha entra simplificada no nível 3 e volta
com ritmo autêntico mais à frente.

## Pendências

- Os temas dos níveis 5, 7, 9, 10 e 11 (antes "a definir") foram **compostos**
  (`melodies.ts`: `flat_fanfare`, `octave_bridge`, `bugle_call`, `choro_skip`,
  `sixteenth_flourish`) — não são melodias de domínio público conhecidas, mas peças
  curtas desenhadas para o eixo pedagógico do nível. Se surgir um tema real
  (folclórico/domínio público) que caiba melhor, é só trocar o fragmento em
  `MELODIES` e o `melodySources`/`music` do nível em `levels.ts`.
- **Ligadura** (mencionada na progressão do nível 10) ainda não tem suporte no
  motor de ritmo (`rhythm.ts`/`render.ts`) — hoje o nível 10 ensina só a síncope
  via pontuado+colcheia.
</content>
