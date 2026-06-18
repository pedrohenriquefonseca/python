# Jogabilidade

Input, recompensa/momentum e os recursos de apoio (hints, drills, mapa de calor,
recordes). Protótipo jogável da sensação:
[`../prototypes/momentum-demo.html`](../prototypes/momentum-demo.html).

## Input por posição de vara

O jogador **não fala** o nome da nota — ele aperta o botão da **posição de vara
(1–7)** correspondente à nota mostrada. Resposta física, alinhada ao gesto real
do instrumento.

Vantagens:
- Sem latência de reconhecimento de voz → janelas de acerto podem ser apertadas e
  a velocidade vira eixo de dificuldade limpo desde cedo.
- Correção trivial e orientada a dados: cada nota carrega `validPositions`;
  acerto = posição tocada ∈ `validPositions`.
- Telemetria rica: além de certo/errado e tempo de reação, registra-se *qual
  posição errada* foi tocada (ouro para os hints).

### Layout (paisagem)

- **Metade superior:** pentagrama em clave de fá; notas correndo da direita para
  a esquerda em direção a uma linha de acerto fixa.
- **Quadrante inferior:** fileira de 7 botões grandes (1→7), dispostos como a vara
  se estendendo da esquerda (1ª, recolhida) para a direita (7ª, estendida),
  reforçando o mapa mental do movimento físico.

#### Linha de acerto e nome da nota (decisão 18/jun/2026)

- **Linha de acerto o mais à esquerda possível**, logo após a clave + armadura. A
  posição é **fixa**, reservando o espaço do **pior caso (armadura de 5
  acidentes)** — assim a memória muscular não muda de nível pra nível e a "pista"
  de leitura à direita fica máxima. Em níveis com armadura menor (ou sem), sobra
  um vão entre a armadura e a linha; é aceitável.
- **Nome da nota (solfejo) exibido abaixo da linha de acerto**, alinhado a ela.
  Aparece **na resolução**: colorido no acerto (cor do tier), cinza no erro —
  mesma lógica de hoje, só reposicionada para baixo da linha.

### Posições alternativas (faz parte do core)

Aceitar alternativas **não é tarefa para depois** — sem isso o jogo pune leitura
correta. Cada nota guarda `validPositions = [principal, ...alternativas]`; acerto
se a posição tocada está na lista.

A posição **principal** vem de [`../reference/slide_positions.py`](../reference/slide_positions.py)
(validada) — que dá **apenas a principal** (fundamental mais grave da série). As
**alternativas** (partais mais agudos) precisam ser adicionadas:

| Nota | Principal (validada) | Alternativa(s) — a validar |
|---|---|---|
| mi (E3) | 2 | 7 |
| fá (F3) | 1 | 6 |
| sib (Bb3) | 1 | 5 |
| dó central (C4) | 3 | 6 |
| fá (F4) | 1 | 6 |

> A principal de C4 é a **3ª** posição (partial 5 do Láb), não a 6ª — conferir
> sempre contra `slide_positions.py`, a fonte validada.

### Configurações

- **Trombone com transpositor (F-attachment / válvula em Fá):** muda as posições
  graves. Tratar como **config separada**; a tabela padrão assume trombone tenor
  reto.
- A *escolha* da alternativa importa para legato/passagens rápidas na vida real,
  mas para um jogo de leitura aceitar qualquer alternativa válida é o correto.

## Recompensa e momentum

O **combo** (acertos seguidos) aciona tudo: multiplicador de pontos, cor da
interface e intensidade da explosão. Quebrou o combo (erro), a cor drena e um
flash vermelho marca a perda — é essa queda que dá peso ao que foi construído.

A cor não fica só no HUD: as **notas que chegam adotam a cor do tier atual**,
então a tela inteira "pega fogo" junto. É isso que ilustra o "gabaritar tudo".

Tiers iniciais (re-tunáveis — limiares, número de tiers e paleta; ver a
reconciliação com a paleta em [`01-design.md`](01-design.md)):

| Combo | Tier | Cor | Multiplicador |
|---|---|---|---|
| 0 | frio | cinza `#888780` | ×1 |
| 1–4 | aquecendo | teal `#1D9E75` | ×1 |
| 5–9 | na zona | azul `#378ADD` | ×2 |
| 10–19 | quente | coral `#D85A30` | ×3 |
| 20+ | pegando fogo | dourado `#EF9F27` | ×4 |

### Animação de acerto

Ao atingir a linha, a nota **explode em partículas** + anel que expande e some
(estilo Guitar Hero). Cor = tier atual; quanto mais quente o combo, mais
partículas. Erro: a nota fica cinza e desvanece; flash vermelho leve e tremor
curto de tela.

### Três decisões aceitas (16/jun/2026)

1. **Áudio escalonado.** Cada acerto sobe um degrau de um arpejo/timbre; a cada
   tier novo entra uma camada (percussão, harmonia). O som carrega metade do
   momentum num jogo de ritmo.
2. **Payoff de "leitura perfeita".** Passar o exercício sem erro dispara selo
   dourado + fanfarra (full combo). É o que faz querer repetir para gabaritar.
3. **Erro suave e instrutivo (jogo educativo, não arcade).** O erro é celebrado
   com *menos* estardalhaço que o acerto. Ao errar, o jogo mostra de leve a
   posição correta (gancho dos hints). Punição dura demais afasta o iniciante.

## Telemetria (implementar cedo)

Hints, drills adaptativos e mapa de calor se apoiam na **mesma telemetria por
nota**: acerto, tempo de reação e *qual posição errada* foi tocada. Coletar isso
já no loop principal destrava os três de uma vez. A cor que aqui significa
"momentum" pode ser reaproveitada no mapa de calor como escala (dourado/verde nas
notas dominadas, vermelho nas fracas) — mesma linguagem visual.

## Backlog — depois do loop principal de pé

1. **Hints** quando o jogador erra recorrentemente uma nota.
2. **Drills adaptativos:** gerar exercícios consecutivos focados na nota errada
   (repetição espaçada por nota).
3. **Mapa de calor** das notas mais erradas vs mais acertadas, para o jogador ver
   suas fraquezas (view sobre a telemetria acumulada).
4. **Recordes estilo fliperama:** placar **por nível** e **mundial** (online).
   Guardar a máxima por nível, exibir o recorde global, deixar entrar no ranking
   ao bater recorde (iniciais/nome). Exige **backend compartilhado** (Firebase /
   Supabase) por causa do Android — ver [`01-design.md`](01-design.md).
5. **Tutorial de primeira partida:** explicação curta exibida **antes da primeira
   partida** do jogador, ensinando o conceito (notas correndo → apertar a posição
   de vara correspondente ao cruzar a linha de acerto). A pensar: formato
   (overlay interativo guiado vs. telas estáticas), se é pulável, e se reaparece
   ao destravar uma mecânica nova (pausas, armaduras, linhas suplementares).
   Mostrar uma vez e guardar flag de "já viu" no save.

Itens 1–3 dependem só da telemetria comum acima.
