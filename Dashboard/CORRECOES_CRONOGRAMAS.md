# O que corrigir em cada cronograma

Levantado em 13/08/26 sobre os 16 snapshots em `data/tasks_*.json`.
Os números são de **tarefas**, não de vínculos.

| projeto | →resumo | resumo← | s/pred | s/suc | FS ruim | total |
|---|---|---|---|---|---|---|
| 0124-10 - Pirajuçara | 49 | 0 | 3 | 54 | 17 | **123** |
| 3923 - Complexo Esportivo Pompéia | 5 | 2 | 3 | 59 | 43 | **112** |
| 0124-09 - Vila Gilda | 26 | 0 | 2 | 33 | 16 | **77** |
| 0124-08 - Parque das Flores | 29 | 0 | 0 | 30 | 7 | **66** |
| 0124-06 - Brasilândia | 28 | 0 | 2 | 30 | 5 | **65** |
| 8223 - Escola Municipal Professor | 3 | 0 | 10 | 30 | 10 | **53** |
| 10525 - Cemitério Córrego do Feijão | 8 | 0 | 2 | 17 | 8 | **35** |
| 1426 - Protótipos | 11 | 0 | 1 | 15 | 2 | **29** |
| 3126 - Sede 2 | 0 | 0 | 1 | 3 | 15 | **19** |
| 9225 - MPPA Alves Ribeiro | 2 | 0 | 5 | 5 | 6 | **18** |
| 2525 - Requalificação Palhano | 0 | 0 | 0 | 0 | 11 | **11** |
| 1426 - Escolas | 0 | 0 | 1 | 7 | 0 | **8** |
| 12925 - Jardim Coreano | 0 | 0 | 0 | 2 | 1 | **3** |
| 0625 - Rota Roxa Inhotim | 0 | 0 | 0 | 1 | 2 | **3** |
| 1526 - BM Prodemge | 0 | 1 | 0 | 1 | 1 | **3** |
| **TOTAL** | **161** | **3** | **87** | **343** | **144** | **738** |

Fora da tabela: **Cronograma Macro Horizontes** (113 apontamentos) — é o consolidado,
não um cronograma de obra. Não vale corrigir.

## Legenda

- **→resumo** — tarefa cuja predecessora é uma tarefa-resumo. É o que quebra a busca
  do ofensor hoje. **Prioridade.**
- **resumo←** — tarefa-resumo que tem predecessora.
- **s/pred** — tarefa-folha sem predecessora (descontada a primeira do cronograma).
- **s/suc** — tarefa-folha sem sucessora que não termina junto com o projeto.
- **FS ruim** — vínculo FS em que a sucessora começa antes do fim da predecessora.
  **Não corrigir nos cronogramas:** as 223 ocorrências têm a sucessora já iniciada
  (pct > 0), ou seja, é início real legítimo. Sai por correção de código — item 1 do
  `BACKLOG.md`.

## Ordem sugerida

1. Os 161 de **→resumo**: são os que travam a caminhada e impedem o report de achar
  o ofensor. Concentrados em Pirajuçara, Parque das Flores, Brasilândia e Vila Gilda.
2. Os 343 de **s/suc**: pontas soltas; só atrapalham quando o atraso passa por elas.
3. **FS ruim** não entra — é código.

## Como refazer este levantamento

Os scripts de diagnóstico foram rodados fora do repositório (leem só os snapshots,
não escrevem nada). Para reproduzir: percorrer `data/tasks_*.json`, usar
`rede.folhas()` para separar folha de resumo e `rede._respeitado()` para achar os FS
incoerentes.
