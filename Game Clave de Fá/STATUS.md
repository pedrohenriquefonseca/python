# Estado atual — Game Clave de Fá

Atualizado em 19/jun/2026.

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
  removido (19/jun). Faixa de cabeçalho reservada (HEADER_H) para os textos não
  invadirem a pauta.
- **Vidas / Game Over (19/jun):** começa com **10 vidas**; cada erro de nota
  (posição errada OU nota que passa) tira 1; **cada mudança de fase reenche**;
  zerou → **Game Over** (overlay mínimo "Toque para recomeçar" → reinicia no nível
  1). A *tela* completa de Game Over ainda é pendência.

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
- **Capacitor:** `app/capacitor.config.ts` (appId `com.clavedefa.app` — trocar
  antes de publicar), `webDir: dist`. Plataforma iOS via **Swift Package Manager**
  (Capacitor 8, sem CocoaPods). `ios/`/`android/` são **gitignored** — regenerados
  por máquina.

### Gerar e abrir o app iOS (num Mac com Xcode)

```
cd "Game Clave de Fá/app"
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

### Telas e fluxo do jogo (pendências — 19/jun)

- **Tela inicial do jogo** (continuar / novo jogo + seleção de dificuldade — `docs/01`).
- **Tutorial antes de cada início de jogo** (relembrar controles e objetivo a cada
  partida; backlog em `docs/02`).
- **Tela de Game Over** completa (resultado da partida + reiniciar / voltar ao
  início). *Já existe um overlay mínimo funcional; falta a tela de verdade.*

### Conteúdo e mecânicas

- **Estrutura de dados dos 12 níveis** (notePool/rhythmPool/key/tempos/
  melodySources/masteryGate), conforme o esboço em `docs/03`. É a fundação do
  resto.
- Expandir o pool de notas além de C3–A3 (hoje fixo) seguindo a progressão.
- **Armaduras** no render (desenhar a armadura na pauta e recolorir as notas).
- Preencher os **temas pendentes** (níveis 7 e 10) em `docs/04`.
- Usar **posições alternativas** no julgamento (stub em `slidePositions.ts`).

## A reconciliar / decisões em aberto

- Tornar o `HEADER_H` proporcional à altura (hoje é px fixo) para o preview
  reduzido bater com o aparelho real (`app/src/game/render.ts`).
- Clave via glifo de fonte: se em algum aparelho aparecer "tofu", trocar por
  desenho vetorial (aí os 2 pontos ficam fixos em `fLineY ± lineGap/2`).
</content>
