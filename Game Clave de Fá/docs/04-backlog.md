# Backlog — a desenvolver depois

Itens registrados a pedido do usuário. Ordem natural de implementação anotada em
cada um.

1. **Layout horizontal** (core): pentagrama na metade superior, botões de posição
   de vara (1–7) no quadrante inferior, alcançáveis pelos polegares. Ver
   `02-input-e-posicoes-vara.md`.

2. **Aceitar posições alternativas** (core, não "depois"): lista `validPositions`
   por nota; acerto = posição tocada ∈ `validPositions`. Ver
   `02-input-e-posicoes-vara.md`.

3. **Hints** quando o jogador erra recorrentemente uma nota. *Fase: depois do core
   jogável + telemetria pronta.*

4. **Drills adaptativos:** gerar exercícios consecutivos focados na nota errada
   (repetição espaçada por nota). *Fase: depois do core + telemetria.*

5. **Mapa de calor** das notas mais erradas vs mais acertadas, para o jogador ver
   suas fraquezas. *Fase: depois do core + telemetria; é uma view sobre a
   telemetria acumulada.*

6. **Recordes de pontuação estilo fliperama:** placar de recorde **por nível**,
   **mundial** (online). Guardar a pontuação máxima por nível, exibir o recorde
   global e deixar o jogador entrar no ranking ao bater recorde (ex.: iniciais /
   nome). *Fase: depois do core jogável + pontuação estável; requer serviço online
   — candidato natural é o **Game Center** (leaderboards do iOS), ou backend
   próprio.*

## Telemetria comum (implementar cedo)

Os itens 3, 4 e 5 se apoiam na **mesma telemetria por nota**: acerto, tempo de
reação e *qual posição errada* foi tocada. Coletar isso já no loop principal
destrava os três de uma vez.

## Quando retomar

Trazer este backlog de volta quando o **loop principal do jogo estiver de pé**.
