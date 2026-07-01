# Estado atual — Stavewise

Atualizado em 30/jun/2026.

## Onde estamos

- **Design e documentação** reorganizados em 4 tópicos:
  [`docs/01-design.md`](docs/01-design.md) (conceito, telas, identidade visual,
  stack), [`docs/02-jogabilidade.md`](docs/02-jogabilidade.md) (input, momentum,
  telemetria, backlog), [`docs/03-progressao-de-dificuldade.md`](docs/03-progressao-de-dificuldade.md)
  (os 12 níveis), [`docs/04-temas-e-musicas.md`](docs/04-temas-e-musicas.md)
  (repertório).
- Stack: **Web + Capacitor** (HTML5 Canvas + TypeScript + Vite). Plataforma **iOS
  já scaffolded** (Capacitor 8 / SPM) — ver seção "App nativo" abaixo.
- **Progressão fechada (17/jun):** 12 níveis na extensão **dó³–sol⁴**, **3
  andamentos** por exercício (Largo 40 / Adagio 66 / Andante 92) e **armaduras
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
- **Andamento** exibido no topo, centralizado e **color-coded** (Largo verde /
  Adagio teal / Andante âmbar). Teclas de dev **` / q / w** trocam o andamento;
  a velocidade de rolagem e a cadência derivam do BPM. Padrão: Andante (Largo no
  preview/dev).
- **Clave de fá** desenhada com o glifo musical (U+1D122), calibrada para a linha
  do Fá cair exatamente entre os 2 pontos.
- **Pauta** com espaço para 3 linhas suplementares acima; hastes das notas acima
  da linha do meio apontam para baixo (notação correta).
- **HUD (cabeçalho):** **nível + tom** à esquerda, **andamento** (color-coded) +
  música ao centro, **contador de vidas com coração vermelho** à direita. Combo
  removido (19/jun). Faixa de cabeçalho reservada (`headerH(h)`, proporcional —
  ver 30/jun abaixo) para os textos não invadirem a pauta.
- **Vidas / Game Over (19/jun):** começa com **10 vidas**; cada erro de nota
  (posição errada OU nota que passa) tira 1; **cada mudança de fase reenche**;
  zerou → **Game Over** (overlay mínimo "Toque para recomeçar" → reinicia no nível
  1). A tela completa de Game Over já existe (ver "Telas e fluxo" abaixo).

## App nativo (Capacitor) — adicionado 19/jun

> **Determinação:** o jogo roda como **app nativo** (foco iPhone), nunca em
> navegador pelo usuário final. O browser é só preview/dev. O código foi adequado
> a isso (abaixo).

- **Áudio (Web Audio API):** som de trombone na nota acertada, com a **duração
  indicada** (1 tempo = 60/bpm); 3 alternativas de som de erro (`buzz` ativo,
  cicláveis com `m` no DEV). Ver `app/src/game/audio.ts`.
- **Háptico (`@capacitor/haptics`):** impacto **leve** no acerto, **forte (Heavy)**
  no erro — Taptic Engine no app; cai para `navigator.vibrate` no preview. Ver
  `app/src/game/haptics.ts`.
- **Orientação:** trava em **paisagem** em runtime via
  `@capacitor/screen-orientation` (`app/src/game/orientation.ts`), sobrevivendo à
  regeneração do projeto nativo.
- **Adequações web→app:** atalhos de teclado cercados em `import.meta.env.DEV`
  (app de toque não tem teclado); CSS endurecido para WKWebView (sem callout de
  toque longo, sem bounce/overscroll, viewport fixa).
- **Capacitor:** `app/capacitor.config.ts` (appId `com.stavewise.app` — trocar
  antes de publicar), `webDir: dist`. Plataforma iOS via **Swift Package Manager**
  (Capacitor 8, sem CocoaPods). `ios/`/`android/` são **gitignored** — regenerados
  por máquina.

### Gerar e abrir o app iOS (num Mac com Xcode)

```
cd "Stavewise/app"
npm install
npm run ios:add   # build + cap add ios  (só na 1ª vez)
npm run ios       # build + cap sync + abre no Xcode
```

> Já testado neste repo: `npx cap add ios` + `cap doctor ios` = "iOS looking great".

### Pendências de on-device (verificar no iPhone)

- **Switch silencioso:** Web Audio em WKWebView pode ser mudo com o interruptor de
  silêncio. Se acontecer, configurar a `AVAudioSession` (categoria `playback`) —
  plugin nativo ou ajuste no projeto iOS.
- **Orientação no splash:** a trava é runtime (JS); para não piscar retrato no
  lançamento, fixar landscape-only no `Info.plist` (vive em `ios/`, gitignored).
- **Ícones/splash/assinatura:** ainda não configurados (vivem em `ios/`).

## Como continuar em outro computador

1. `git clone` / `git pull` deste repositório.
2. Precisa de **Node.js + npm** instalados e no PATH. Conferir com
   `node --version`. (No Mac onde o projeto começou já existe; numa máquina nova,
   instalar o Node LTS.)
3. `cd "Stavewise/app" && npm install && npm run dev`
   → abre em `http://localhost:5173`. **Testar em paisagem** (o jogo é landscape);
   teclas 1–7 jogam, q/w/e trocam o andamento.
4. Abra o Claude Code na pasta `Stavewise`. Os `docs/` + este `STATUS.md`
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

## Telas e fluxo do jogo — construído (21–22/jun)

As telas que eram pendência em 19/jun foram desenhadas e já estão no código
(`app/src/game/`):

- **Splash** "Waveform" (equalizador neon) — `splash.ts`.
- **Tela inicial** (novo jogo / continuar) com waveform na home — `home.ts`.
- **Seleção de nível** — `levelSelect.ts`.
- **Tutorial** desenhado à mão (setas, títulos, botões e pauta) — `tutorial.ts`.
- **Tela de Game Over** discreta sobre a pauta esmaecida — `gameOver.ts`.
- **Tela de fim de fase** (estrelas, precisão, Next/Replay/Try again) — `levelComplete.ts` (30/jun).

## Conteúdo e mecânicas — feito

- **Estrutura de dados dos 12 níveis (30/jun):** `app/src/game/levels.ts` carrega
  o modelo completo do esboço de `docs/03` — `notePool`, `rhythmPool` (acumulativo
  pela curva), `keySig`/`key`, `allowLedger` (derivado), `tempos`, `melodySources`,
  `proceduralWeight` e `masteryGate`. É a fundação que o gerador de exercícios, o
  motor de ritmo e a porta de domínio vão ler. `melodySources` referencia ids da
  biblioteca de fragmentos (ver 30/jun abaixo) — todos os 12 níveis já têm tema.
- **Pool de notas por nível:** o `Game` carrega o `notePool` do nível (não é mais
  fixo em C3–A3); `[`/`]` (DEV) navegam os níveis e a pauta se redimensiona sozinha.
- **Armaduras no render (30/jun):** a armadura é desenhada na pauta (`render.ts`,
  `drawKeySignature`) e **as notas alteradas pela armadura são recoloridas** (teal)
  enquanto rolam, sinalizando o acidente antes da linha (cor `theme.altered`).
- **Motor de ritmo (30/jun):** o `Game` consome o `rhythmPool` do nível. Cada nota
  sorteia uma **figura** (`app/src/game/rhythm.ts`: tabela `RHYTHMS` com duração em
  tempos, flag de pausa e peso — semínima, mínima, colcheia, pontuado, pausa,
  semicolcheia) por peso (puxa p/ semínima). A **duração comanda 3 coisas**: o
  espaçamento na pauta (a próxima nota nasce após `beatMs × tempos`, então a mínima
  ocupa o dobro do espaço da semínima), a **duração do som** no acerto e o **desenho**
  da figura — cabeça aberta na mínima, bandeirolas na colcheia/semicolcheia, ponto
  no pontuado, glifo de pausa (`render.ts` `drawNote`/`drawRest`/`drawFlags`). A
  **pausa** é silêncio que rola: não se toca (transparente ao julgamento em `press`)
  e cruza a linha sem perder vida. Sem pausas seguidas (peso baixo + guarda).
- **Progressão de fase / porta de domínio (30/jun):** cada nível é uma fase de
  **20 notas** (com altura — pausas não contam; constante `LEVEL_QUOTA`). Ao
  resolver a cota, o `Game` avalia o `masteryGate`: **precisão ≥ `minAccuracy`**
  libera o próximo nível. **Estrelas (0–3):** 1 por dominar, +1 por precisão ≥ 0,95,
  +1 por reação média (|distância à linha| em ms) ≤ `maxReactionMs`. **Tela de fim de
  fase** (`levelComplete.ts`): "Level complete" com estrelas + *Next/Replay/Home*, ou
  "Almost!" + *Try again/Home* se não dominou. **Barra de progresso** fina na divisa
  cabeçalho/pauta (`render.ts`). **Persistência** (`storage.ts`): nível atual, maior
  **nível liberado** e **melhor estrela por nível** (compatível com saves antigos). O
  **level select** tranca os não liberados (🔒) e exibe as estrelas. O avanço agora
  acontece no jogo — as teclas `[`/`]` continuam só para DEV.
- **Biblioteca de fragmentos melódicos (30/jun):** `app/src/game/melodies.ts`
  (`MELODIES`) — cada fragmento é escrito como **grau da escala** (índice no
  `notePool`, não midi absoluto), então o mesmo fragmento serve qualquer nível cujo
  pool alcance aquele grau (a armadura recolore o som via `soundingMidi`, sem
  transposição explícita). `Game.spawn` sorteia, entre um fragmento e outro,
  começar um novo (peso `1 - proceduralWeight`) ou seguir procedural; iniciado, o
  fragmento toca até o fim. Repertório conhecido transcrito (Hot Cross Buns, Mary
  Had a Little Lamb, Ode to Joy, Frère Jacques, Jingle Bells, Twinkle Twinkle,
  London Bridge, Silent Night, When the Saints). Os 5 temas antes "a definir"
  (níveis 5, 7, 9, 10, 11) foram **compostos** para este jogo — não são canções de
  domínio público — visando o eixo pedagógico do nível (o grau recolorido pela
  armadura, a nova oitava, a pausa, a síncope, a semicolcheia); ver
  `docs/04-temas-e-musicas.md`. Verificado por script que todo grau cabe no pool e
  todo ritmo usado está no `rhythmPool` liberado do nível.
- **HEADER_H proporcional (30/jun):** `render.ts` — `headerH(h)` substitui a
  constante px fixa (18% da altura, com piso/teto), então o preview reduzido bate
  com o aparelho real.

## Próximos passos sugeridos

- **Posições alternativas** no julgamento (mapeadas em `slidePositions.ts`):
  **adiada por decisão** — por ora só a posição primária conta.
- **Ligadura** (fraseado do nível 10, ver docs/03) ainda sem suporte no motor de
  ritmo — hoje o nível 10 ensina só a síncope via pontuado+colcheia.

## A reconciliar / decisões em aberto

- Clave via glifo de fonte: se em algum aparelho aparecer "tofu", trocar por
  desenho vetorial (aí os 2 pontos ficam fixos em `fLineY ± lineGap/2`).
</content>
