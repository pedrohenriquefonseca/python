# Estado atual — Game Clave de Fá

Atualizado em 16/jun/2026.

## Onde estamos
- Design definido (`docs/01`–`docs/06`): progressão, input por posição de vara,
  momentum/recompensa, telas e seleção de dificuldade, identidade visual.
- Stack escolhida: **Web + Capacitor** (`docs/07`).
- **Fatia jogável inicial pronta em `app/`** (Vite + TypeScript + Canvas):
  notas em Dó maior (C3–A3) correndo pela pauta, 7 botões de posição de vara
  (+ teclas 1–7), linha de acerto, combo/multiplicador/explosão de partículas,
  paleta índigo aplicada. Verificada no navegador.

## Como continuar (inclusive em outro computador)
1. `git clone` / `git pull` deste repositório.
2. `cd "Game Clave de Fá/app" && npm install && npm run dev`
   → abre em `http://localhost:5173` (testar em paisagem; teclas 1–7 funcionam).
3. Abra o Claude Code na pasta `Game Clave de Fá`. Os `docs/` e este `STATUS.md`
   carregam todo o contexto — eles não dependem do histórico de chat (que fica
   local em cada máquina).

## Próximos passos sugeridos
- Tela inicial (continuar / novo jogo) e seleção de dificuldade (`docs/05`).
- Estrutura de dados dos níveis (notePool/rhythmPool/tempo/melodySources).
- Usar posições alternativas no julgamento (já há stub em `slidePositions.ts`).
- Áudio (Web Audio API) e háptico (`@capacitor/haptics`).
- A rever: armaduras distribuídas desde cedo; reconciliar a rampa de "heat" do
  combo com a paleta (`docs/06`).
