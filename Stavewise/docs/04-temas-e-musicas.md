# Temas e músicas

O repertório que dá musicalidade ao jogo e o motor que o serve. A curva que esses
temas acompanham está em [`03-progressao-de-dificuldade.md`](03-progressao-de-dificuldade.md).

## Motor de musicalidade

Manter uma **biblioteca de fragmentos famosos** etiquetados por (notas usadas,
figuras usadas, tom, âmbito). O gerador só serve fragmentos que cabem nos eixos já
liberados; como tudo começa em Dó maior posicionado em dó³–lá³, basta
**transpor** cada tema para que ele caia nas notas desbloqueadas.

Cada fragmento na biblioteca deve carregar metadados como:

```json
{
  "id": "ode_to_joy",
  "nome": "Hino à Alegria",
  "notas": ["E3","F3","G3"],
  "ritmos": ["quarter","half"],
  "tomOriginal": "C-major",
  "ambitoSemitons": 5
}
```

## Repertório por nível

Mapa de quais temas entram em cada um dos 12 níveis (ver tabela em
[`03-progressao-de-dificuldade.md`](03-progressao-de-dificuldade.md)):

| # | Notas / armadura | Música-recompensa |
|---|---|---|
| 1 | dó³ ré³ mi³ · Dó M | Hot Cross Buns, Mary Had a Little Lamb |
| 2 | + fá³ sol³ · Dó M | Hino à Alegria, Frère Jacques, refrão de Jingle Bells |
| 3 | + lá³ (hexacorde) · Dó M | Brilha Brilha Estrelinha, London Bridge |
| 4 | + si³ · Dó M | London Bridge, Mary (variações) |
| 5 | dó³–si³ · **Fá M** | tema conhecido transposto para Fá |
| 6 | dó³–si³ · **Si♭ M** | Noite Feliz |
| 7 | + dó⁴ ré⁴ · Si♭ M | *(a definir — tema que use a 2ª oitava)* |
| 8 | + mi⁴ fá⁴ sol⁴ · Si♭ M | When the Saints Go Marching In |
| 9 | dó³–sol⁴ · **Mi♭ M** | tema transposto para Mi♭ |
| 10 | dó³–sol⁴ · Mi♭ M | *(a definir — samba/choro simples, com síncope)* |
| 11 | dó³–sol⁴ · **Lá♭ M** | tema transposto para Lá♭ |
| 12 | dó³–sol⁴ · revisão 0–4♭ | livre |

## Truque pedagógico: a mesma música cresce com o jogador

**A mesma música reaparece em níveis mais altos com fidelidade rítmica e tonal
crescente** — primeiro só semínimas, depois ritmo autêntico, depois (quando a
armadura permitir) o tom mais próximo do original. Reforça o reconhecimento e dá
sensação de progresso. Ex.: Brilha Brilha entra simplificada no nível 3 e volta
com ritmo autêntico mais à frente.

## Pendências

- **Nível 7 sem tema definido** — achar uma melodia conhecida que explore dó⁴–ré⁴
  (segunda oitava) em Si♭ M.
- **Nível 10** — escolher um tema de samba/choro simples que ensine síncope e
  ligadura.
- Decidir os temas concretos transpostos para Fá (n5), Mi♭ (n9) e Lá♭ (n11).
</content>
