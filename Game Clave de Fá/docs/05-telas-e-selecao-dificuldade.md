# Telas iniciais e seleção de dificuldade

## Tela inicial

Duas opções:

- **Continuar** — retoma a partida salva exatamente onde parou: o nível e o
  **estado de domínio por nota** (a telemetria que alimenta hints e mapa de calor).
  Mostra um resumo (ex.: "nível 4 · pauta completa · 68% dominado").
- **Novo jogo** — leva à seleção de dificuldade e começa do zero.

## Save slot único (decisão 16/jun/2026)

O jogo guarda o progresso de **um jogo só**. Iniciar um novo jogo **sobrescreve /
apaga** o progresso do jogo em andamento.

> Implicação de UX: quando já existe um jogo salvo, "novo jogo" deve pedir
> **confirmação** ("isto vai apagar seu progresso atual") antes de zerar.

## Dificuldades sempre destravadas (decisão 16/jun/2026)

Seleção **totalmente livre** dos 10 níveis, sempre — nada fica bloqueado. Para não
deixar o iniciante se perder, destacar um nível **"recomendado"** calculado pelo
desempenho (apenas orienta, não trava). Opcional: teste de nível de ~30s na
primeira vez para posicionar o recomendado.

## Critério de divisão

As dificuldades são cortadas pela **competência de leitura dominante** em cada
etapa, na ordem natural de aprendizado: **notas → ritmo → tonalidade**. Dentro de
cada bloco os outros eixos ficam calmos, então o jogador enfrenta uma dificuldade
nova por vez. (Os ~10 níveis aqui são os marcos da tela; o currículo fino que o
jogo percorre sozinho está em `01-conceito-e-progressao.md`.)

## Tabela das 10 dificuldades

| # | Nível | Fase | O que passa a ler | Tom | Música |
|---|---|---|---|---|---|
| 1 | primeiras notas | notas | dó ré mi, só semínimas | Dó M | Hot Cross Buns |
| 2 | pentacorde | notas | + fá sol, + mínima | Dó M | Hino à Alegria |
| 3 | hexacorde | notas | + lá, + colcheia | Dó M | Brilha Brilha |
| 4 | pauta completa | notas | pauta inteira + 1ªs supl., + pausas | Dó M | Joy to the World |
| 5 | ritmo pontuado | ritmo | célula longa-curta (ponto) | Dó M | Noite Feliz |
| 6 | subdivisão | ritmo | semicolcheias, andamento maior | Dó M | When the Saints |
| 7 | síncope | ritmo | contratempo e ligaduras | Dó M | tema de samba/choro simples |
| 8 | acidentes | tonalidade | sustenidos/bemóis de passagem | Dó M + alteração | — |
| 9 | armaduras | tonalidade | armaduras maiores (1–4 acidentes) | Sol, Fá, Ré, Sib… | repertório transposto |
| 10 | tons e escalas | tonalidade | todas maiores/menores + cromático | todas | livre |

## A rever (conversa posterior)

- **Armaduras de clave distribuídas desde o início.** A tabela acima concentra
  toda a tonalidade no fim (níveis 8–10). A decisão é **rever isso**: introduzir
  armaduras **progressivamente ao longo do jogo, desde cedo**, em vez de uma
  categoria isolada no nível 9. Repensar como os acidentes/armaduras se intercalam
  com as fases de notas e ritmo. Os níveis 8–10 desta tabela são provisórios.
