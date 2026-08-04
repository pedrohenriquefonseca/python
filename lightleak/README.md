# lightleak

Efeitos analógicos generativos para fotos `.jpg`. Nenhum resultado se repete: cada
aplicação é sorteada a partir de uma semente, e a mesma semente sempre reproduz o
mesmo efeito.

Recursos planejados:

1. **Vazamento de luz (light leak)** — implementado
2. **Halação (halation)** — implementado
3. Poeira e arranhados — a fazer
4. Bordas de filme analógico, com e sem data — a fazer

## Como funciona o vazamento de luz

O efeito não é textura sobreposta. É um modelo do fenômeno, calibrado contra
vinte fotografias reais com vazamento.

**Composição em luz linear.** No filme a luz parasita não se mistura com a
imagem: ela *soma exposição* no negativo. O pipeline decodifica sRGB → linear,
compõe e recodifica. Daí saem de graça o preto levantado, o contraste local
derrubado e o estouro para branco.

A composição é `1 - (1 - base)·exp(-add)`, forma de Beer–Lambert: aditiva no
regime das sombras (onde o efeito importa), saturando suave em 1 no núcleo, sem
corte duro. Ela dá três garantias que um ombro compressivo não dá — efeito
desligado devolve a imagem bit-a-bit, branco puro na entrada continua branco, e
nada escurece sozinho. Um ombro com assíntota em 1 falhava justamente nisso:
qualquer curva compressiva que passe pelo joelho com derivada 1 fica abaixo da
identidade daí em diante, e o branco da entrada saía cinza.

**Por que quase todo leak é uma coluna vertical.** O caso clássico não é a tampa
traseira — é o feltro da boca do cartucho. A luz entra ali e caminha *entre as
camadas enroladas* do filme, velando uma faixa que atravessa a largura da fita, o
que num quadro deitado aparece como banda vertical de altura inteira. Ela para
numa frente irregular, onde as camadas se encostam: por isso a borda é rasgada e
dura, tipo papel queimado, e não um degradê suave. Nas vinte referências, 15 são
exatamente isso.

**Cor é corante, não RGB.** Um vazamento tem a cor de *quais camadas do filme* a
luz sensibilizou — por isso a parametrização é amarelo, ciano e magenta, as três
camadas, mais o branco como quarto polo (as três por igual: só luminosidade).
Cada polo dá um ganho e um expoente por canal, e a soma é
`L_c = amp · ganho_c · f^p_c`. O canal fraco leva expoente alto: some na franja e
só volta no núcleo, que por isso satura em branco. A rampa corante → branco cai
daí sozinha; não existe parâmetro de "cor do núcleo".

**As oito paletas.** São as sete combinações não-vazias dos três corantes mais o
branco puro. Numa receita de várias fontes, uma paleta de dois polos distribui os
polos entre as bandas — `amarelo-ciano` põe amarelo numa lateral e ciano na
outra — e às vezes mistura os dois numa mesma banda. Corante absolutamente puro
não existe no filme, então cada fonte leva 6% de contaminação das outras camadas;
sem isso o resultado vira chapa de cor. O branco é a exceção: contaminá-lo seria
introduzir justamente a dominante que ele não deve ter.

Com `palette = "permutar"`, a semente escolhe a combinação por `seed % 8`. Se a
UI incrementar a semente a cada Generate, oito toques passam pelas oito sem
repetir.

**Duas calibrações que custaram caro.** Os expoentes dos canais *fortes* de cada
polo precisam ficar perto de 1: abaixo disso o canal decai devagar demais e
transborda para fora da banda, tingindo o quadro inteiro — a franja colorida vem
da *distância* entre os expoentes, não de um expoente baixo. E `amp` (o valor do
platô, em luz linear com
branco = 1,0) tem de acompanhar a dureza da frente: amp 16 numa frente dura é um
platô limpo com franja de fogo; a mesma amplitude numa frente difusa lava tudo.

**Irregularidade estrutural.** As duas frentes de uma banda têm ruído fractal
independente — as bordas de um leak real não são espelhadas nem correlacionadas,
uma pode ser dura e a outra difusa. As estrias variam através da banda e
persistem ao longo dela, porque são o rastro do filme enrolado.

### Primitivas

| primitiva | o que modela |
|---|---|
| `band` | coluna com duas frentes independentes, platô estourado e estrias |
| `bloom` | brilho difuso ancorado numa borda ou canto (fresta larga, luz oblíqua) |
| `wash` | véu direcional amplo — luz difusa de início ou fim de rolo |

## Como funciona a halação

A luz atravessa as três camadas de emulsão, chega à base transparente e reflete
na interface base/ar de volta para dentro da emulsão. Como a reflexão acontece a
uma distância — a espessura da base —, o retorno reaparece **deslocado**: um halo
em volta das altas-luzes, não em cima delas.

**Por que vermelho.** A camada sensível ao vermelho é a mais distante da lente,
ou seja, a encostada na base. A luz que volta bate nela primeiro e com menos
atenuação, tanto da emulsão quanto do que restou da camada antihalo. Do percurso
de ida e volta é praticamente só o vermelho que sobrevive. E quanto mais longe
lateralmente a luz anda dentro da base, mais material atravessa — por isso a
cauda larga é *mais* vermelha que o núcleo, que ainda puxa laranja. O modelo dá
uma cor própria a cada oitava em vez de tingir o halo inteiro de um vermelho só.

**A amplitude vem da reflexão interna total, não de Fresnel.** A conta ingênua —
Fresnel em incidência normal numa base de poliéster (n≈1,65) — dá só ~6%, e com
ela o halo fica invisível. Ela é a conta errada: a luz que chega à base já foi
espalhada pela emulsão e incide numa distribuição ampla de ângulos, e tudo além
do ângulo crítico (~37°) sofre reflexão interna *total*. Para uma distribuição
difusa a fração que escapa é 1/n² ≈ 0,37 — ou seja, ~63% volta inteira. Daí a
ordem de 20% depois de descontar absorção e o que resta da camada antihalo.

O raio, por sua vez, é fração fixa do quadro e não de pixels: na película mede
dezenas de micrômetros, então escanear em mais dpi não aumenta o halo.

**Halação tem raio mínimo.** A luz volta deslocada pelo dobro da espessura da
base e não menos: numa base de ~125 µm sobre um quadro de 36 mm, ~0,6% da
largura. Sem esse piso a pirâmide começa em 1 px, as oitavas minúsculas ficam com
metade do peso e o resultado vira um contorno duro em volta da alta-luz em vez de
um brilho. Foi o erro que mais custou aqui — junto com descobrir que reamostrar
mips com bicúbica gera *ringing* (lóbulos negativos) em ampliações grandes, o que
punha uma borda escura em volta do halo. O borrão é gaussiano de verdade, por
três box blurs com soma acumulada.

A fonte é quadrática e com termo de recuperação de especular: halação é fenômeno
de ponto de luz — um céu claro quase não halata — e o JPEG cortou em 1,0 um
especular que na cena era muito mais brilhante.

Diferente do vazamento, **a halação não tem nada de aleatório**: é uma resposta
às altas-luzes da própria imagem. Duas fotos dão halos diferentes porque as
altas-luzes estão em lugares diferentes, não porque houve sorteio. Por isso o
controle é um slider só.

```bash
python3 cli.py foto.jpg --effect halation --intensity 1.5 -o out/halacao.jpg
python3 cli.py foto.jpg --effect halation --sweep 4      # comparar intensidades
```

| slider | faixa | efeito |
|---|---|---|
| `intensity` | 0 – 3 | multiplica a fração de luz devolvida pela base |

**Onde a conservação de energia falha.** O borrão conserva energia, então um
ponto de luz se espalha e some enquanto uma área clara grande atravessa quase
intacta — medido, o pico do halo variava **120x** entre fotos. Isso só estaria
certo se soubéssemos o brilho real da cena, e não sabemos: o JPEG cortou toda
alta-luz em 1,0, então um neon que era mil vezes o entorno chega aqui valendo o
mesmo que um muro branco. É exatamente por isso que um ponto de luz nas
referências tem halo enorme e o modelo ingênuo não produzia nenhum.

`normalize=True` (padrão) ancora no pico do *brilho já borrado*: o halo fica com
força fixa em relação à sua própria fonte, seja ela ponto de luz ou parede, e a
variação entre fotos cai de 120x para ~1,05x. Um piso impede que uma foto sem
alta-luz nenhuma seja amplificada até inventar halação onde não há.
`normalize=False` devolve a conservação de energia pura.

## Uso

```bash
python3 cli.py foto.jpg --preset fogo-na-borda --seed 7 -o out/foto.jpg
```

Os 20 presets lado a lado sobre a sua foto:

```bash
python3 cli.py foto.jpg --gallery -o out/gallery.jpg
```

As oito paletas de corante sobre a mesma geometria:

```bash
python3 cli.py foto.jpg --palettes --preset espectro-vertical -o out/paletas.jpg
```

Variações do sorteio livre, sem preset:

```bash
python3 cli.py foto.jpg --sheet 12 --seed 100 -o out/sheet.jpg
```

### Presets

Cada um vem de uma fotografia de referência e descreve a *estrutura* observada —
geometria, dureza das frentes, faixa de amplitude e tom — não valores congelados.
Todo campo pode ser um par `(mín, máx)` sorteado a cada `Generate`, então o preset
guarda o caráter da referência e nunca repete o mesmo quadro.

| preset | caráter |
|---|---|
| `noturno-cruz` | barra amarela estreita e incandescente sobre cena noturna magenta |
| `borda-rasgada` | terço esquerdo estourado em creme, fronteira rasgada vermelha |
| `arco-diagonal` | feixes diagonais sobrepostos em laranja, vermelho e amarelo |
| `coluna-e-ceu` | coluna estriada à esquerda e véu vermelho cobrindo o céu |
| `faixa-fria` | quadro inteiro em âmbar com uma banda ciano atravessando |
| `fogo-na-borda` | branco absoluto até uma linha de fogo fina e serrilhada |
| `cortina-estrada` | colunas verticais difusas descendo do céu, salmão e pálidas |
| `bruma-dourada` | bruma dourada difusa vinda do alto, sem fronteira visível |
| `coluna-laranja` | coluna laranja densa e muito estriada sobre cena escura |
| `inundacao-diagonal` | inundação laranja saturada em diagonal, com o céu preservado |
| `ambar-total` | âmbar cobrindo tudo, contraste derrubado, núcleo claro no alto |
| `lateral-queimada` | lateral direita queimada, franja vermelha e estrias |
| `vermelho-solido` | vermelho puro e saturado, fronteira horizontal, núcleo amarelo |
| `cortina-tripla` | três colunas paralelas difusas em laranja quente |
| `ambar-leitoso` | coluna âmbar leitosa e larga; o quadro inteiro fica enevoado |
| `bandas-laterais` | bandas amarelas difusas nas duas laterais, centro limpo |
| `faixa-fria-forte` | como a faixa fria, com a banda ciano dominando o quadro |
| `duas-bordas` | borda laranja de um lado, esverdeada do outro, centro limpo |
| `borda-suave` | borda esquerda avermelhada, fronteira larga e ondulada |
| `espectro-vertical` | banda quente numa lateral, centro intacto, banda fria na outra |

### Controles

O preset define os defaults dos sliders; qualquer slider passado explicitamente
vence. Eles escalam a estrutura observada em vez de substituí-la.

| slider | faixa | efeito |
|---|---|---|
| `intensity` | 0 – 2 | amplitude global |
| `palette` | 8 opções | `branco`, `amarelo`, `ciano`, `magenta`, os três pares, `tricromia`; `auto` mantém a cor da referência e `permutar` cicla as oito |
| `chroma` | 0 – 1 | 0 dá vazamento branco, 1 o corante cheio |
| `spread` | 0,3 – 2 | largura das bandas e alcance |
| `softness` | 0,3 – 2 | maciez das frentes |
| `complexity` | 0 – 2 | quantidade de fontes (só no sorteio livre) |
| `texture` | 0 – 2 | raggedness das frentes e estrias |
| `veil` | 0 – 1 | névoa global de flare interno |
| `grain` | 0 – 1 | granulado dentro do vazamento |

### API

```python
from filmfx import apply, preset_params, preset_recipe
from filmfx.imaging import load_rgb, save_rgb

p = preset_params("fogo-na-borda")   # defaults dos sliders desse preset
p.seed, p.intensity = 42, 1.2
p.palette = "ciano-magenta"          # 'auto' mantém a cor da referência
recipe = preset_recipe("fogo-na-borda", p)   # "Generate" — sorteia a variação
save_rgb(apply(load_rgb("foto.jpg"), p, recipe), "out.jpg")
```

`recipe.to_dict()` é JSON puro: dá para salvar, versionar e reaplicar exatamente
o mesmo vazamento depois. Mudar um slider sem re-sortear mantém a composição e
altera só aquele parâmetro.

Desempenho: ~3,4 s para 12 MP, ~0,3 s numa prévia de 0,5 MP.

## Instalação

```bash
pip install -r requirements.txt
```
