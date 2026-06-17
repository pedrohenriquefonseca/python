# Clave de Fá — app (web · Vite + TypeScript + Canvas)

Fatia jogável inicial: notas em Dó maior correm pela pauta; toque (ou tecle) a
posição de vara 1–7 quando a nota cruzar a linha de acerto. Combo, multiplicador
e explosão de partículas no acerto. Estruturado para empacotar com Capacitor.

## Rodar no navegador (Mac, sem instalar nada além disto)

```sh
cd "Game Clave de Fá/app"
npm install
npm run dev
```

Abre em `http://localhost:5173`. Teste com a janela em paisagem. As teclas **1–7**
funcionam além dos botões (cómodo no desktop).

## Build

```sh
npm run build   # type-check (tsc) + bundle do Vite em dist/
```

## Empacotar para iOS / Android (mais tarde)

```sh
npm i @capacitor/core @capacitor/cli
npx cap init "Clave de Fá" com.pedro.clavedefa --web-dir dist
npm i @capacitor/ios @capacitor/android @capacitor/haptics
npx cap add ios && npx cap add android
npm run build && npx cap sync
```

iOS precisa do Xcode; Android precisa do Android Studio/SDK. Háptico via
`@capacitor/haptics` (impacto/seleção, nativo nos dois).

## Mapa do código

- `src/theme.ts` — paleta índigo (fonte única; vira CSS vars)
- `src/data/slidePositions.ts` — porte validado do Partituras (nota→vara + alternativas)
- `src/game/Game.ts` — loop, estado, input dos 7 botões e teclado
- `src/game/render.ts` — desenho da pauta, clave, notas, HUD
- `src/game/particles.ts` — explosão de acerto
- `src/game/combo.ts` — tiers de momentum
- `src/style.css` — layout paisagem (pauta em cima, 7 botões embaixo)
