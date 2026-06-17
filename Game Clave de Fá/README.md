# Game Clave de Fá

Jogo para iPhone que ensina **trombonistas** a ler partitura em **clave de fá**, no
estilo Guitar Hero: as notas correm pelo pentagrama e o jogador aperta o botão
da **posição de vara (1–7)** correspondente.

> Status: fatia jogável inicial em [`app/`](app/) (web · Vite + TypeScript + Canvas).
> Veja [`STATUS.md`](STATUS.md) para o estado atual e como continuar.

## Estrutura

| Pasta / arquivo | O que é |
|---|---|
| [`docs/01-design.md`](docs/01-design.md) | Conceito, telas/seleção de dificuldade, identidade visual (índigo) e stack/arquitetura |
| [`docs/02-jogabilidade.md`](docs/02-jogabilidade.md) | Input (posições de vara), layout paisagem, combo/momentum, telemetria e backlog (hints, drills, mapa de calor, recordes) |
| [`docs/03-progressao-de-dificuldade.md`](docs/03-progressao-de-dificuldade.md) | Os 12 níveis (dó³–sol⁴), eixos, 3 andamentos e armaduras com bemóis desde cedo |
| [`docs/04-temas-e-musicas.md`](docs/04-temas-e-musicas.md) | Motor de musicalidade, repertório por nível e pendências de temas |
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
[`docs/02-jogabilidade.md`](docs/02-jogabilidade.md).
