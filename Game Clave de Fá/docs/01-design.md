# Design

Conceito, telas, identidade visual e stack. Para jogabilidade ver
[`02-jogabilidade.md`](02-jogabilidade.md); para a curva de dificuldade,
[`03-progressao-de-dificuldade.md`](03-progressao-de-dificuldade.md); para o
repertório, [`04-temas-e-musicas.md`](04-temas-e-musicas.md).

## Conceito

Jogo para iPhone, jogado na **horizontal**, que ensina **trombonistas** a ler
partitura em **clave de fá**. As notas correm pelo pentagrama (estilo Guitar
Hero) em direção a uma linha de acerto; ao chegar na linha, o jogador aperta o
botão da **posição de vara (1–7)** correspondente àquela nota.

A **progressão** é o coração do jogo: começa muito fácil (poucas notas, só
semínimas) e fica progressivamente mais difícil, usando trechos de **músicas
mundialmente conhecidas** para ter musicalidade em vez de uma sequência mecânica.

## Telas iniciais

- **Continuar** — retoma a partida salva onde parou: o nível e o **estado de
  domínio por nota** (a telemetria que alimenta hints e mapa de calor). Mostra um
  resumo (ex.: "nível 4 · pauta completa · 68% dominado").
- **Novo jogo** — leva à seleção de dificuldade e começa do zero.

### Save slot único (decisão 16/jun/2026)

O jogo guarda o progresso de **um jogo só**. Iniciar um novo jogo **sobrescreve /
apaga** o progresso em andamento.

> UX: quando já existe jogo salvo, "novo jogo" deve pedir **confirmação** ("isto
> vai apagar seu progresso atual") antes de zerar.

### Dificuldades sempre destravadas (decisão 16/jun/2026)

Seleção **totalmente livre** dos 12 níveis, sempre — nada bloqueado. Para não
deixar o iniciante se perder, destacar um nível **"recomendado"** calculado pelo
desempenho (apenas orienta, não trava). Opcional: teste de nível de ~30s na
primeira vez para posicionar o recomendado.

## Identidade visual

Tema **claro**, linhas modernas e elegantes. Paleta escolhida pelo usuário em
16/jun/2026 (a partir de 3 opções em mockup): **índigo moderno**.

| Token | Hex | Papel |
|---|---|---|
| `bg` | `#F5F6FB` | fundo da tela (claro levemente azulado, não branco clínico) |
| `panel` | `#FFFFFF` | superfícies: faixa da pauta, botões |
| `ink` | `#222633` | texto, pauta, clave, notas |
| `muted` | `#8A8FA0` | texto secundário, bordas, estados inativos |
| `accent` | `#5A5BE0` | primária (índigo): linha de acerto e botão da posição esperada |
| `accent2` | `#159E91` | momentum/combo (barra + multiplicador) — cor que "esquenta" |
| `btn` | `#EDEFF8` | face do botão de posição inativo |

Papéis: `accent` é a voz do jogo (linha de acerto + botão correto); `accent2` é o
momentum; pauta/clave/notas em `ink` sobre `panel` branco, para leitura limpa.

> **A reconciliar:** a rampa de "heat" do combo
> ([`02-jogabilidade.md`](02-jogabilidade.md): cinza → teal → azul → coral → ouro)
> foi definida antes da paleta. Harmonizar as duas (ex.: `accent2`/teal como
> degrau base, topo que converse com o índigo) ao detalhar áudio/momentum.

## Stack e arquitetura

Decisão (16/jun/2026): **Web + Capacitor**. HTML5 Canvas + TypeScript (build com
Vite), empacotado para iOS e Android com Capacitor. Um código só; testa no
navegador no dia a dia; Xcode (iOS) e Android Studio/SDK (Android) só entram na
hora de empacotar.

**Por quê:** reaproveita o protótipo de momentum (já em Canvas); um código para
iOS + Android + web; iteração instantânea no navegador; domínio dos pilares —
gráficos (Canvas/WebGL), som (Web Audio API), háptico (`@capacitor/haptics`).
Válvula de escape: plugin nativo (Swift/Kotlin) só onde precisar (ex.: latência
de áudio mais justa).

### Estrutura do código

`app/` é o projeto web (Vite). Ver [`../app/README.md`](../app/README.md) para
rodar/empacotar.

- `src/theme.ts` — paleta índigo (fonte única; vira CSS vars)
- `src/data/slidePositions.ts` — porte validado do Partituras (nota→vara + alternativas)
- `src/game/Game.ts` — loop, estado, input dos 7 botões + teclado
- `src/game/render.ts` — pauta, clave, notas, HUD
- `src/game/particles.ts` — explosão de acerto
- `src/game/combo.ts` — tiers de momentum
- `src/style.css` — layout paisagem (pauta em cima, 7 botões embaixo)

### Recordes mundiais cross-platform

Com Android no escopo, o ranking mundial **não** pode depender do Game Center (só
iOS). Recordes unificados pedem um **backend compartilhado** (ex.: Firebase ou
Supabase). Game Center pode entrar como extra só no iOS. (Ver o item de recordes
em [`02-jogabilidade.md`](02-jogabilidade.md).)
</content>
</invoke>
