# Conceito e progressão de dificuldade

## Conceito

Jogo para iPhone, jogado na **horizontal**, que ensina trombonistas a ler
partitura em clave de fá. As notas vêm correndo pelo pentagrama (estilo Guitar
Hero) em direção a uma linha de acerto; ao chegar na linha, o jogador aperta o
botão da **posição de vara (1–7)** daquela nota.

A **progressão** é o coração do jogo: começa muito fácil (uma figura, poucas
notas) e fica progressivamente mais difícil. Os exercícios usam trechos de
**músicas mundialmente conhecidas** para ter musicalidade, não uma progressão
mecânica de notas.

## O modelo: dificuldade é um vetor de eixos independentes

Dificuldade não é uma linha só — são vários eixos independentes. O segredo da
curva é avançar **um eixo de cada vez**, congelando os outros, e liberar uma
música reconhecível como recompensa a cada passo.

| Eixo | Começa em | Caminha até | Princípio |
|---|---|---|---|
| Notas (âmbito) | dó ré mi (centro do pentagrama) | extensão toda + linhas suplementares | expandir do centro para fora |
| Figuras (duração) | só semínima | mínima → colcheia → pontuado → semicolcheia | uma nova de cada vez, depois misturar |
| Pausas | nenhuma | integradas ao ritmo | "silêncio = não apertar nada" |
| Velocidade | lento, janela de acerto generosa | rápido, janela curta | rampa contínua *dentro* de cada nível |
| Tonalidade | Dó maior (sem acidentes) | círculo das quintas → menores → cromático | acidente avulso antes de armadura |
| Saltos (intervalo) | graus conjuntos (vizinhos) | saltos crescentes | passo é mais fácil de ler |

## Eixo das notas — ordem de liberação

O centro do pentagrama de fá, subindo até a linha de cima, dá um **hexacorde de
Dó maior sem nenhuma linha suplementar** (C3–A3), que é exatamente onde mora a
maioria das melodias infantis famosas. Ver `prototypes/mapa-notas-clave-fa.svg`.

1. **dó ré mi** (C3 D3 E3) — centro
2. **+ fá sol** (F3 G3) — pentacorde
3. **+ lá** (A3) — hexacorde completo
4. **oitava grave** (sol lá si graves)
5. **linhas suplementares** (dó central C4, mi/fá graves)
6. depois: acidentes → armaduras → menores → cromático

## Motor de musicalidade

Manter uma **biblioteca de fragmentos famosos** etiquetados por (notas usadas,
figuras usadas, tom, âmbito). O gerador só serve fragmentos que cabem nos eixos
já liberados; como tudo começa em Dó maior posicionado em C3–A3, basta
**transpor** cada tema para que ele caia nas notas desbloqueadas.

| Notas liberadas | Desbloqueia |
|---|---|
| dó ré mi | Hot Cross Buns, Mary Had a Little Lamb |
| + fá sol (pentacorde) | Hino à Alegria, Frère Jacques, refrão de Jingle Bells |
| + lá (hexacorde) | Brilha Brilha Estrelinha, London Bridge |
| oitava grave / suplementares | Joy to the World, versões completas |

Truque pedagógico: **a mesma música reaparece em níveis mais altos com fidelidade
rítmica e tonal crescente** (primeiro só semínimas, depois ritmo autêntico, depois
tom original). Reforça o reconhecimento e dá sensação de progresso.

## Currículo de exemplo (primeiros níveis)

| Nível | Notas | Ritmo | Tom | BPM | Música |
|---|---|---|---|---|---|
| 1 | dó ré mi | semínima | Dó M | 50 | Hot Cross Buns |
| 2 | dó ré mi | + mínima | Dó M | 55 | Mary (finais segurados) |
| 3 | + fá sol | semínima | Dó M | 55 | Hino à Alegria (simplif.) |
| 4 | + fá sol | semínima+mínima | Dó M | 60 | Frère Jacques |
| 5 | + lá | semínima | Dó M | 60 | Brilha Brilha, London Bridge |
| 6 | dó–lá | + colcheia | Dó M | 60 | Brilha Brilha (autêntica) |
| 7 | dó–lá | mistura + ponto | Dó M | 70 | Hino à Alegria (autêntico) |
| 8 | dó–lá | + pausas | Dó M | 70 | Jingle Bells completo |
| 9 | + oitava grave | misturado | Dó M | 70 | âmbito ampliado |
| 10 | + suplementares | misturado | Dó M | 75 | Joy to the World |
| 11 | + fá♯ avulso | misturado | Dó M c/ alteração | 75 | nota de passagem |
| 12 | armadura Sol M | misturado | Sol M | 75 | repertório transposto |

## Arquitetura sugerida

Níveis como **dados, não código** — um gerador lê parâmetros e produz exercícios
infinitos:

```json
{
  "id": "n07",
  "notePool": ["C3","D3","E3","F3","G3","A3"],
  "rhythmPool": ["quarter","eighth","dotted-quarter"],
  "key": "C-major",
  "allowLedger": false,
  "tempoBPM": [65, 80],
  "hitWindowMs": 280,
  "melodySources": ["ode_to_joy"],
  "proceduralWeight": 0.3,
  "masteryGate": { "minAccuracy": 0.9, "maxReactionMs": 600 }
}
```

Dá para calcular um **escore escalar de dificuldade** por exercício a partir
desses eixos e ordenar/balancear a curva automaticamente.
