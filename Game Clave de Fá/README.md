# Game Clave de Fá

Jogo para iPhone que ensina **trombonistas** a ler partitura em **clave de fá**, no
estilo Guitar Hero: as notas correm pelo pentagrama e o jogador aperta o botão
da **posição de vara (1–7)** correspondente.

> Status: fatia jogável inicial em [`app/`](app/) (web · Vite + TypeScript + Canvas).
> Veja [`STATUS.md`](STATUS.md) para o estado atual e como continuar.

## Estrutura

| Pasta / arquivo | O que é |
|---|---|
| [`docs/01-conceito-e-progressao.md`](docs/01-conceito-e-progressao.md) | Conceito do jogo + sistema de dificuldade multi-eixo + currículo |
| [`docs/02-input-e-posicoes-vara.md`](docs/02-input-e-posicoes-vara.md) | Input (botões da vara), layout em paisagem, posições alternativas |
| [`docs/03-recompensa-e-momentum.md`](docs/03-recompensa-e-momentum.md) | Combo, multiplicador, cores, explosão, áudio e payoff de "leitura perfeita" |
| [`docs/04-backlog.md`](docs/04-backlog.md) | A desenvolver depois: hints, drills adaptativos, mapa de calor |
| [`docs/05-telas-e-selecao-dificuldade.md`](docs/05-telas-e-selecao-dificuldade.md) | Tela inicial, seleção de dificuldade, save slot único, tabela dos 10 níveis |
| [`docs/06-identidade-visual.md`](docs/06-identidade-visual.md) | Tema claro + paleta escolhida (índigo moderno) e papéis de cor |
| [`docs/07-stack-e-arquitetura.md`](docs/07-stack-e-arquitetura.md) | Stack (Web + Capacitor), estrutura do código, recordes cross-platform |
| [`app/`](app/) | Código do jogo (Vite + TS + Canvas). Ver [`app/README.md`](app/README.md) |
| [`STATUS.md`](STATUS.md) | Estado atual + como continuar (inclusive noutro computador) |
| [`reference/slide_positions.py`](reference/slide_positions.py) | Tabela nota→posição de vara **validada** (copiada do projeto Partituras) |
| [`prototypes/momentum-demo.html`](prototypes/momentum-demo.html) | Protótipo jogável da sensação de momentum + explosão. Abrir no navegador |
| [`prototypes/mapa-notas-clave-fa.svg`](prototypes/mapa-notas-clave-fa.svg) | Mapa da ordem em que as notas são liberadas |

## Protótipos

Abrir `prototypes/momentum-demo.html` diretamente no navegador (sem dependências).

## Reaproveitamento

`reference/slide_positions.py` foi copiado de `../Partituras/src/slide_positions.py`
(motor já validado contra 4 partituras). Ele dá a posição **principal** de cada
nota; o jogo ainda precisa estender com as **posições alternativas** — ver
[`docs/02-input-e-posicoes-vara.md`](docs/02-input-e-posicoes-vara.md).
