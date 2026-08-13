# Fontes das referências

## Molduras de filme

As doze máscaras em `borders/` saem de 18 referências reunidas em `refs/`. A
procedência aqui é bem pior que a do dano, e convém dizer com todas as letras.

**Doze das dezoito são preview de banco de imagem** — Adobe Stock, Shutterstock,
Dreamstime — e nelas a marca d'água é ladrilhada *por cima do rebate*, não só do
centro. Em arte chapada a marca sai por abertura morfológica (`despeckle` no
manifesto), porque o traço é fino e o letreiro não é; em textura fotográfica não
sai, e é justamente ali que a referência valia. As sobras de marca escritas fora
da moldura são descartadas por outro caminho: o extrator guarda só o maior
componente conexo, então texto solto no papel branco não entra.

**Nenhuma passa de 1043 px.** A máscara precisa servir foto de 12 MP, o que
significa ampliar de 3× a 6×. É por isso que existe o modo `sharp`, que
relimiariza a alfa depois de ampliar — funciona porque a arte é geométrica.
Referência fotográfica não tem essa saída e fica no limite do que dá.

Se o projeto for distribuído, este conjunto **não** pode ir junto como está: as
molduras derivadas de preview de banco são obra derivada de material licenciado.
O caminho é refazê-las de fonte livre — negativo escaneado próprio ou acervo em
domínio público — ou desenhar a geometria pela norma ISO 1007, que é pública. O
manifesto em `refs/borders.json` deixa a troca barata: muda a origem, roda o
extrator de novo, o resto do código não sabe a diferença.

## Fontes das referências de dano

As máscaras em `masks/` são extraídas de fotografias reais. As de alta resolução
vêm do Wikimedia Commons, escolhidas por três motivos: são scans em 3000–8000 px,
o dano é real, e a licença permite uso derivado.

Baixadas em `refs_hi/` por `tools/fetch_refs.py`.

| arquivo | origem | px | licença |
|---|---|---|---|
| `nb-gruppebilde.jpg` | Nasjonalbiblioteket (NO), "Gruppebilde … sterkt skadet" | 6597×4599 | domínio público |
| `fortepan-kavehaz.jpg` | Fortepan 2033, New York kávéház | 7000×4529 | CC BY-SA 3.0 |
| `fortepan-girl.jpg` | Fortepan 1999, retrato | 5651×3657 | CC BY-SA 3.0 |
| `fortepan-beach.jpg` | Fortepan 29088, praia | 4833×3060 | CC BY-SA 3.0 |
| `leguery.jpg` | Jules Charles le Guéry | 8012×7869 | domínio público |
| `wellcome-amoy.jpg` | Wellcome Collection V0037201 | 2911×2488 | CC BY 4.0 |
| `wallin-family.jpg` | Sofia Jansdotter Wallin family | 2413×3341 | domínio público |
| `dunesmobile.jpg` | Sleeping Bear Dunesmobile | 3072×2304 | domínio público |
| `navy-80g.jpg` | US Navy 80-G-27208, foto rasgada | 2179×2296 | domínio público |
| `trutat-foire.jpg` | Fonds Trutat, negativo de vidro quebrado | 4061×1562 | domínio público |
| `trutat-velo.jpg` | Fonds Trutat, Luchon 1896 | 3000×2116 | domínio público |
| `trutat-cafe.jpg` | Café de la Paix, Ax-les-Thermes | 2961×2131 | domínio público |
| `albi-archeveche.jpg` | Archevêché, Albi 1895 | 3025×2107 | domínio público |
| `nara-colorado.jpg` | NARA 518020, negativo trincado | 3000×1871 | domínio público |
| `oo-bloc.jpg` | Oo bloc erratique, Luchon | 3481×1827 | domínio público |
| `bhl-africa.jpg` | Biodiversity Heritage Library | 4094×2528 | domínio público |

**Atribuição.** Os quatro itens CC BY / CC BY-SA exigem crédito ao autor e, no
caso do SA, licença compartilhada em obra derivada. Uma máscara de dano extraída
é obra derivada. Se o projeto for distribuído, ou se credita, ou se refaz o
conjunto só com os itens de domínio público — sobram doze, o que ainda dá os
vinte filtros por recorte.

As 25 imagens originais em `refs/` ficaram fora deste conjunto: são de baixa
resolução, várias são duplicatas e duas têm marca d'água de banco de imagem.
Servem de referência visual, não de fonte de máscara.
