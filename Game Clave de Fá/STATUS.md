# Estado atual — Game Clave de Fá

Atualizado em 17/jun/2026.

## Onde estamos

- **Design e documentação** reorganizados em 4 tópicos:
  [`docs/01-design.md`](docs/01-design.md) (conceito, telas, identidade visual,
  stack), [`docs/02-jogabilidade.md`](docs/02-jogabilidade.md) (input, momentum,
  telemetria, backlog), [`docs/03-progressao-de-dificuldade.md`](docs/03-progressao-de-dificuldade.md)
  (os 12 níveis), [`docs/04-temas-e-musicas.md`](docs/04-temas-e-musicas.md)
  (repertório).
- Stack: **Web + Capacitor** (HTML5 Canvas + TypeScript + Vite).
- **Progressão fechada (17/jun):** 12 níveis na extensão **dó³–sol⁴**, **3
  andamentos** por exercício (Adagio 66 / Andante 92 / Allegro 126) e **armaduras
  com bemóis desde cedo** (Fá → Si♭ → Mi♭ → Lá♭; cada bemol recolore uma nota já
  conhecida). Tabela síntese em `docs/03`.
- **Linhas suplementares:** intervalo dó³–sol⁴ exige **3 acima** (sol⁴) e **0
  abaixo** (dó³ fica dentro da pauta). O layout aprovisiona exatamente isso
  (constantes `LEDGERS_ABOVE`/`LEDGERS_BELOW` em `app/src/game/render.ts`).

## Fatia jogável (`app/`) — o que já funciona

- Notas em Dó maior (C3–A3, pool em `Game.ts`) correndo pela pauta; 7 botões de
  posição de vara + teclas **1–7**. Resolve **na linha**: acerto = explosão +
  nome da nota (solfejo) à esquerda da linha; passagem sem acerto = puff + nome
  cinza.
- **Andamento** exibido no topo, centralizado e **color-coded** (Adagio teal /
  Andante âmbar / Allegro coral). Teclas de dev **q / w / e** trocam o andamento;
  a velocidade de rolagem e a cadência derivam do BPM. Padrão: Andante.
- **Clave de fá** desenhada com o glifo musical (U+1D122), calibrada para a linha
  do Fá cair exatamente entre os 2 pontos.
- **Pauta** com espaço para 3 linhas suplementares acima; hastes das notas acima
  da linha do meio apontam para baixo (notação correta).
- **HUD:** combo + multiplicador/tier (sem a barra, removida em 17/jun);
  pontuação + recorde à direita; faixa de cabeçalho reservada para os textos não
  invadirem a pauta branca.

## Como continuar em outro computador

1. `git clone` / `git pull` deste repositório.
2. Precisa de **Node.js + npm** instalados e no PATH. Conferir com
   `node --version`. (No Mac onde o projeto começou já existe; numa máquina nova,
   instalar o Node LTS.)
3. `cd "Game Clave de Fá/app" && npm install && npm run dev`
   → abre em `http://localhost:5173`. **Testar em paisagem** (o jogo é landscape);
   teclas 1–7 jogam, q/w/e trocam o andamento.
4. Abra o Claude Code na pasta `Game Clave de Fá`. Os `docs/` + este `STATUS.md`
   carregam todo o contexto (independem do histórico de chat, que é local por
   máquina).

> **Preview do Claude Code:** `.claude/launch.json` (versionado) sobe o dev server
> via `npm run dev --prefix app`. Se o preview reclamar de `npm` não encontrado,
> reinicie o editor para o Node entrar no PATH da sessão.
>
> **Nota Windows (jun/2026):** esta máquina não tinha Node; foi instalado o LTS
> via `winget install OpenJS.NodeJS.LTS`. `npm` não fica no PATH até reiniciar o
> shell — use `$env:Path = "$env:ProgramFiles\nodejs;$env:Path"` antes de
> `npm`/`npx` numa sessão nova, ou reinicie o terminal.

## Próximos passos sugeridos

- **Tela inicial** (continuar / novo jogo) e **seleção de dificuldade** (`docs/01`).
- **Estrutura de dados dos 12 níveis** (notePool/rhythmPool/key/tempos/
  melodySources/masteryGate), conforme o esboço em `docs/03`. É a fundação do
  resto.
- Expandir o pool de notas além de C3–A3 (hoje fixo) seguindo a progressão.
- **Armaduras** no render (desenhar a armadura na pauta e recolorir as notas).
- Preencher os **temas pendentes** (níveis 7 e 10) em `docs/04`.
- Usar **posições alternativas** no julgamento (stub em `slidePositions.ts`).
- **Áudio** (Web Audio API) e **háptico** (`@capacitor/haptics`).
- **Tutorial de primeira partida** (no backlog em `docs/02`).

## A reconciliar / decisões em aberto

- Tornar o `HEADER_H` proporcional à altura (hoje é px fixo) para o preview
  reduzido bater com o aparelho real (`app/src/game/render.ts`).
- Rampa de "heat" do combo vs. paleta índigo (`docs/01`).
- Clave via glifo de fonte: se em algum aparelho aparecer "tofu", trocar por
  desenho vetorial (aí os 2 pontos ficam fixos em `fLineY ± lineGap/2`).
</content>
