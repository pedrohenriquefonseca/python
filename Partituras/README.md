# Partituras — posições de vara do trombone

App de Mac que recebe um PDF de partitura de trombone (clave de fá, sem
anotações) e escreve, acima de cada nota, o número da **posição da vara**
correspondente — do jeito que um trombonista que não lê partitura usa para
tocar.

## O que o app faz

Dado o PDF de uma partitura limpa, ele gera um novo PDF idêntico ao original
com os números das posições (1 a 7) escritos acima do pentagrama:

- **Alinhamento horizontal:** cada número fica exatamente em cima da cabeça da
  sua nota.
- **Altura vertical relativa:** notas mais graves ficam mais próximas do
  pentagrama; notas mais agudas ficam mais altas. A altura acompanha o contorno
  da melodia (é relativa às notas vizinhas, não absoluta).
- **Sem sobreposição:** os números nunca cobrem marcas de ensaio, letras de
  parte, as próprias notas nem o pentagrama.

## Pipeline

1. **OMR** — reconhece cada nota e sua altura (pitch) a partir do PDF.
   Engine: [Audiveris](https://github.com/Audiveris/audiveris), que exporta
   MusicXML preservando as coordenadas originais de cada símbolo.
2. **Tabela** — converte cada pitch no número da posição de vara
   (`src/slide_positions.py`). Faixa coberta: E2–C5.
3. **Layout** — calcula a posição (x, y) de cada número, com a altura relativa
   e o desvio para evitar colisões.
4. **Overlay** — escreve os números sobre o PDF original, preservando todo o
   restante.

## Estrutura

```
src/
  slide_positions.py   # tabela nota -> posição de vara (validada)
```

## Status

- [x] Tabela de posições de vara (E2–C5), com autoteste
- [ ] Integração OMR (Audiveris) → MusicXML com coordenadas
- [ ] Cálculo de layout (x alinhado, y relativo, anticolisão)
- [ ] Overlay no PDF original
- [ ] App de Mac (interface: escolher PDF → gerar PDF anotado)
