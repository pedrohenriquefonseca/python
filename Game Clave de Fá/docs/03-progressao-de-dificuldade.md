# Progressão de dificuldade

Define a curva dos **12 níveis** do jogo. O repertório que entra em cada nível
está em [`04-temas-e-musicas.md`](04-temas-e-musicas.md).

## Foco inicial: extensão principal do trombone (decisão 17/jun/2026)

A progressão se concentra na **extensão principal do trombone tenor**, de **dó³
(C3, MIDI 48) a sol⁴ (G4, MIDI 67)** — onde mora a maioria das melodias e o
instrumento é mais confortável. A pauta de fá vai do dó³ (2º espaço) ao lá³ (5ª
linha) sem linhas suplementares; si³ fica logo acima; dó⁴–sol⁴ usam linhas
suplementares acima.

## O modelo: dificuldade é um vetor de eixos

Dificuldade não é uma linha só — são eixos independentes. O segredo da curva é
avançar **um eixo de cada vez**, congelando os outros, e liberar uma música
reconhecível como recompensa a cada passo.

| Eixo | Começa em | Caminha até |
|---|---|---|
| Notas (âmbito) | dó ré mi (centro da pauta) | extensão completa dó³–sol⁴ |
| Figuras (duração) | só semínima | mínima → colcheia → pontuado → semicolcheia |
| Pausas | nenhuma | integradas ao ritmo |
| Tonalidade | Dó maior (sem acidentes) | armaduras com bemóis (Fá, Si♭, Mi♭, Lá♭) |
| Andamento | Adagio | Andante → Allegro (ver abaixo) |

## Andamento: eixo ortogonal (3 por exercício, decisão 17/jun/2026)

Cada exercício existe em **3 velocidades**. O **conteúdo** (notas/ritmo/armadura)
avança pela tabela de níveis; o **andamento** é o quanto se aperta cada nível.

| Andamento | BPM aprox. | Papel |
|---|---|---|
| Adagio | ~66 | nota nova estreia aqui, janela de acerto generosa — *passar libera o próximo nível* |
| Andante | ~92 | velocidade de leitura "real" |
| Allegro | ~126 | desafio de domínio — estrelas / recorde |

Efeito pedagógico: a nota nova sempre estreia devagar (Adagio) e só vira pressão
de velocidade depois (Andante/Allegro).

## Armaduras de clave desde cedo, privilegiando bemóis (decisão 17/jun/2026)

As armaduras entram **distribuídas ao longo do jogo**, não amontoadas no fim, e
são **bemóis** (idiomático do trombone de banda: Fá, Si♭, Mi♭, Lá♭). O truque:
cada bemol novo **recolore exatamente uma nota que o jogador já lê** — armadura
introduzida como eixo isolado, sem nota nova competindo.

| Armadura | Bemol que entra | Recolore (nota já conhecida) |
|---|---|---|
| Fá M (1♭) | si♭ | **si** |
| Si♭ M (2♭) | + mi♭ | **mi** |
| Mi♭ M (3♭) | + lá♭ | **lá** |
| Lá♭ M (4♭) | + ré♭ | **ré** |

Todas as notas recoloridas caem em posições válidas (si♭=1, mi♭=3, lá♭=3, ré♭=5).

## Tabela síntese dos 12 níveis

| # | Notas (extensão) | Ritmo novo | Armadura | Eixo que avança | Música |
|---|---|---|---|---|---|
| 1 | **dó³ ré³ mi³** | semínima | Dó M | base | Hot Cross Buns |
| 2 | + fá³ sol³ | + mínima | Dó M | notas | Hino à Alegria |
| 3 | + lá³ *(hexacorde, pauta cheia)* | + colcheia | Dó M | notas | Brilha Brilha |
| 4 | + si³ | consolida | Dó M | notas (si natural) | London Bridge |
| 5 | dó³–si³ | consolida | **Fá M (1♭)** | armadura → si♭ | tema em Fá |
| 6 | dó³–si³ | + pontuado | **Si♭ M (2♭)** | armadura → mi♭ | Noite Feliz |
| 7 | + dó⁴ ré⁴ *(linhas supl. acima)* | mistura | Si♭ M | notas (2ª oitava) | — |
| 8 | + mi⁴ fá⁴ **sol⁴** | mistura | Si♭ M | notas (extensão completa) | When the Saints |
| 9 | dó³–sol⁴ | + pausas | **Mi♭ M (3♭)** | armadura → lá♭ | tema em Mi♭ |
| 10 | dó³–sol⁴ | + síncope / ligadura | Mi♭ M | ritmo | samba/choro simples |
| 11 | dó³–sol⁴ | + semicolcheia | **Lá♭ M (4♭)** | armadura → ré♭ | tema em Lá♭ |
| 12 | dó³–sol⁴ | livre | revisão 0–4♭ | consolidação | livre |

## Por que nessa ordem

- **Níveis 1–4 (Dó M):** estabelecem leitura central + ritmo básico, subindo do
  centro da pauta (dó³) até logo acima dela (si³, ainda sem linha suplementar).
  Sem armadura ainda porque, antes de o si³ existir, um bemol não teria o que
  recolorir.
- **Si³ natural antes de Fá M, de propósito:** assim a *primeira armadura da
  vida* (nível 5) tem como único conceito novo "a armadura transforma si em si♭".
- **Bemóis no fluxo, não no fim:** Fá M já aparece no nível 5 e os demais bemóis
  se intercalam com a expansão de notas e ritmo.
- **A 2ª oitava (dó⁴–sol⁴) entra nos níveis 7–8**, depois que a armadura de 2
  bemóis está firme — aí as músicas ganham espaço para a extensão completa.

## Níveis como dados, não código

Um gerador lê parâmetros e produz exercícios infinitos. Esboço por nível:

```json
{
  "id": "n07",
  "notePool": ["C3","D3","E3","F3","G3","A3","B3","C4","D4"],
  "rhythmPool": ["quarter","half","eighth"],
  "key": "Bb-major",
  "allowLedger": true,
  "tempos": { "adagio": 66, "andante": 92, "allegro": 126 },
  "melodySources": ["..."],
  "proceduralWeight": 0.3,
  "masteryGate": { "minAccuracy": 0.9, "maxReactionMs": 600 }
}
```

Dá para calcular um **escore escalar de dificuldade** por exercício a partir dos
eixos e ordenar/balancear a curva automaticamente.
</content>
