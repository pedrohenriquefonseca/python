# Input e posições de vara

## Decisão de input

O jogador **não fala** o nome da nota — ele aperta o botão da **posição de vara
(1–7)** correspondente à nota mostrada. A resposta é física, alinhada ao gesto
real do instrumento.

Vantagens:
- Sem latência de reconhecimento de voz → janelas de acerto podem ser apertadas e
  a velocidade volta a ser um eixo de dificuldade limpo desde cedo.
- Correção trivial e orientada a dados: cada nota carrega uma lista
  `validPositions`; acerto = posição tocada ∈ `validPositions`.
- Telemetria rica: além de certo/errado e tempo de reação, registra-se *qual
  posição errada* foi tocada (ouro para os hints — ver `04-backlog.md`).

## Layout (paisagem)

Duas faixas horizontais:

- **Metade superior:** pentagrama em clave de fá; notas correndo da direita para
  a esquerda em direção a uma linha de acerto fixa.
- **Quadrante inferior:** fileira de 7 botões grandes (1→7), dispostos como a vara
  se estendendo da esquerda (1ª, recolhida) para a direita (7ª, estendida),
  reforçando o mapa mental do movimento físico.

## Posições alternativas (faz parte do core)

Aceitar alternativas **não é tarefa para depois** — sem isso o jogo pune leitura
correta. Cada nota guarda `validPositions` = [principal, ...alternativas]; acerto
se a posição tocada está na lista.

A posição **principal** vem de `reference/slide_positions.py` (validada). Esse
arquivo dá **apenas a principal** (fundamental mais grave da série). As
**alternativas** (partais mais agudos) precisam ser adicionadas. Principais já
conhecidas e alternativas clássicas a validar:

| Nota | Principal (validada) | Alternativa(s) — a validar |
|---|---|---|
| mi (E3) | 2 | 7 |
| fá (F3) | 1 | 6 |
| sib (Bb3) | 1 | 5 |
| dó central (C4) | 3 | 6 |
| fá (F4) | 1 | 6 |

> Atenção: a principal de C4 é a **3ª** posição (partial 5 do Láb), não a 6ª —
> conferir sempre contra `slide_positions.py`, que é a fonte validada.

## Configurações

- **Trombone com transpositor (F-attachment / válvula em Fá):** muda as posições
  graves. Tratar como **config separada** (modo "trombone com transpositor"); a
  tabela padrão assume trombone tenor reto.
- A *escolha* da alternativa importa para legato/passagens rápidas na vida real,
  mas para um jogo de leitura aceitar qualquer alternativa válida é o correto.
