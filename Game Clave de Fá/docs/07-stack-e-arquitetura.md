# Stack e arquitetura

Decisão (16/jun/2026): **Web + Capacitor**. O jogo é feito em HTML5 Canvas +
TypeScript (build com Vite) e empacotado para iOS e Android com Capacitor. Um
código só para os dois sistemas; testa no navegador no dia a dia; Xcode (iOS) e
Android Studio/SDK (Android) só entram na hora de empacotar.

## Por quê
- Reaproveita o protótipo de momentum (já em Canvas).
- Um código para iOS + Android (+ web).
- Iteração instantânea no navegador, sem instalar Xcode.
- Domínio dos pilares: gráficos (Canvas/WebGL), som (Web Audio API), háptico
  (plugin nativo `@capacitor/haptics`). Válvula de escape: plugin nativo
  (Swift/Kotlin) só onde precisar (ex.: latência de áudio mais justa).

## Estrutura
`app/` é o projeto web (Vite). Ver `app/README.md` para rodar/empacotar.
- `src/theme.ts` — paleta índigo (fonte única; vira CSS vars)
- `src/data/slidePositions.ts` — porte validado do Partituras (nota→vara + alternativas)
- `src/game/Game.ts` — loop, estado, input dos 7 botões + teclado
- `src/game/render.ts` — pauta, clave, notas, HUD
- `src/game/particles.ts` — explosão de acerto
- `src/game/combo.ts` — tiers de momentum
- `src/style.css` — layout paisagem (pauta em cima, 7 botões embaixo)

## Recordes mundiais cross-platform (revisão do backlog)
Com Android no escopo, o ranking mundial **não** pode depender do Game Center
(só iOS). Recordes unificados pedem um **backend compartilhado** (ex.: Firebase
ou Supabase). Game Center pode entrar como extra só no iOS.
