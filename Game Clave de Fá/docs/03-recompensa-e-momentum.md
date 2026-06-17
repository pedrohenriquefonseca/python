# Recompensa e momentum

Protótipo jogável da sensação: `prototypes/momentum-demo.html`.

## Combo, multiplicador e cor

O **combo** (acertos seguidos) aciona tudo: multiplicador de pontos, cor da
interface e intensidade da explosão. Quebrou o combo (erro), a cor drena e um
flash vermelho marca a perda — é essa queda que dá peso ao que foi construído.

A cor não fica só no HUD: as **notas que chegam adotam a cor do tier atual**,
então a tela inteira "pega fogo" junto. É isso que ilustra o "gabaritar tudo".

Tiers iniciais (re-tunáveis — limiares, número de tiers e paleta):

| Combo | Tier | Cor | Multiplicador |
|---|---|---|---|
| 0 | frio | cinza `#888780` | ×1 |
| 1–4 | aquecendo | teal `#1D9E75` | ×1 |
| 5–9 | na zona | azul `#378ADD` | ×2 |
| 10–19 | quente | coral `#D85A30` | ×3 |
| 20+ | pegando fogo | dourado `#EF9F27` | ×4 |

## Animação de acerto

Ao atingir a linha de acerto, a nota **explode em partículas** + anel que expande
e some (estilo Guitar Hero). Cor = tier atual; quanto mais quente o combo, mais
partículas. Erro: a nota passa da linha, fica cinza e desvanece; flash vermelho
leve e tremor curto de tela.

## Três decisões aceitas (16/jun/2026)

1. **Áudio escalonado.** Cada acerto sobe um degrau de um arpejo/timbre; a cada
   tier novo entra uma camada (percussão, harmonia). O som carrega metade do
   momentum num jogo de ritmo.
2. **Payoff de "leitura perfeita".** Passar o exercício sem nenhum erro dispara um
   selo dourado + fanfarra (full combo). É o que faz querer repetir para gabaritar.
3. **Erro suave e instrutivo (jogo educativo, não arcade).** O erro é celebrado
   com *menos* estardalhaço que o acerto. Ao errar, o jogo mostra de leve a posição
   correta (gancho do sistema de hints — ver `04-backlog.md`). Punição dura demais
   afasta o iniciante.

## Sinergia com o backlog

A telemetria que alimenta o combo (acerto/erro/tempo por nota) é a **mesma** que
abastece o mapa de calor e os drills adaptativos. A cor que aqui significa
"momentum" pode ser reaproveitada no mapa de calor como escala (dourado/verde nas
notas dominadas, vermelho nas fracas) — mesma linguagem visual nos dois lugares.
