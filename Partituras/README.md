# Partituras — posições de vara do trombone

App de Mac que recebe um PDF de partitura de trombone (clave de fá, sem
anotações) e escreve, acima de cada nota, o número da **posição da vara**
(1 a 7) — do jeito que um trombonista que não lê partitura usa para tocar.

Funciona com PDFs vetoriais gerados por software de notação (MuseScore etc.).

## Como funciona

Nada de OCR: leitura **geométrica** do vetor do PDF.

1. **Extração** (`src/extract.py`)
   - Linhas da pauta: traços horizontais largos; sistemas = grupos de 5 linhas
     com espaçamento uniforme (linhas espúrias são descartadas).
   - Cabeças de nota, claves e acidentes: glyphs SMuFL (qualquer fonte musical
     — MScore, Leland, Bravura...). A altura usa `origin` do glyph, não o
     centro do bbox (pegadinha: o bbox é a caixa do *em* da fonte).
   - Pitch: posição vertical contada em degraus diatônicos a partir da linha
     do Fá + armadura de clave + acidentes ocasionais (valem até a barra de
     compasso, no mesmo grau).
   - Ligaduras de prolongamento (mesma altura, inclusive através da quebra de
     linha): a nota de continuação não recebe número.
2. **Tabela** (`src/slide_positions.py`) — nota → posição de vara (E2–C5),
   indexada por MIDI (enarmonia automática), validada por autoteste.
3. **Layout e escrita** (`src/annotate.py`)
   - X: número centrado na cabeça da nota.
   - Y: contorno relativo — nota mais aguda fica mais alta; mesma nota
     próxima fica nivelada. Garantido por construção (erosão dupla com
     variação limitada) e conferido por um verificador final: layout com
     inversão é rejeitado, nunca vira PDF.
   - Anticolisão por mapa de tinta rasterizado: hastes, feixes, ligaduras,
     marcas de ensaio [A]/[B], voltas, tercinas e os próprios números.
   - Tamanho da fonte: o maior em que tudo cabe; um sistema ou número
     específico pode ceder até 15% para não derrubar a página (regra do
     usuário). Largura de tinta real por glyph (o "1" é estreito).

## Uso

**App de Mac** (`src/app.py`, empacotado em `~/Applications/Posições Trombone.app`):
janela minimalista — solte o PDF (ou clique para escolher) e o app salva
"`<nome original> - posições.pdf`" na mesma pasta do arquivo. Erros aparecem
na lista e num alerta (ex.: PDF escaneado em vez de vetorial).

**Linha de comando:**

```bash
python3 src/annotate.py "Partitura.pdf" "Partitura - posições.pdf"
```

Dependências: `pymupdf`, `numpy`, `pyobjc-framework-Cocoa` (Python 3.13).

## Status

- [x] Motor completo, validado em 4 partituras reais (Folhas Secas, Amigo
      Velho, Chorinho de Gafieira, Bole Bole)
- [x] App de Mac (soltar e pronto)
