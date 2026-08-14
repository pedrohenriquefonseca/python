# Backlog — análise de ofensores do report semanal

Contexto: o report aponta atraso total do projeto (ex.: 6 dias) mas lista ofensores
que somam bem menos (ex.: 1 dia). O atraso tem duas origens — tarefa que **esticou**
e tarefa que só foi **empurrada** — e o report lista apenas quem esticou. O número só
fecha quando a caminhada pela rede de dependências alcança todas as tarefas que
esticaram. Hoje ela morre antes.

Medido em 13/08/26 sobre os 16 snapshots em `data/tasks_*.json`.

---

## 1. Higiene dos cronogramas  — MS PROJECT

Ver `CORRECOES_CRONOGRAMAS.md` no commit dff371a para a lista por projeto.

- Nenhum resumo como predecessora ou sucessora — criar tarefas de término de etapa.
- **Término de etapa com duração ZERO.** Com duração 1 dia vira elo comum: entra na
  cadeia e, quando esticar, aparece como ofensor no lugar da tarefa real. Marco o
  código atravessa (`rede.py:173`) e nunca lista como ofensor (`rede.py:225`).
- A regra é **toda tarefa de trabalho**, não "toda tarefa de nível 4". O código não
  olha nível: trabalho é a tarefa que não tem filhas (`rede.folhas()`). Há tarefas
  de trabalho em nível 1, 2 e 3 em quase todos os projetos — o BM Prodemge tem 64
  em nível 3 e só 10 em nível 4.

**Efeito colateral esperado:** o primeiro report de cada cronograma corrigido sai
pior. As tarefas novas não existem na base gravada do report anterior, ficam sem
delta e podem matar a caminhada como o resumo mata hoje. É um report por projeto, e
o aviso "N tarefa(s) inserida(s)" vai disparar junto.

## 2. Data de tarefa só deve mudar por vínculo  — PROCESSO

O resíduo que nenhuma das correções acima resolve. Se a tarefa é arrastada na mão ou
tem restrição de data fixa, ela anda sem que nada antes dela ande — e não existe
causa a apontar na rede.

Comprovado no Palhano, que já está com os vínculos corrigidos (zero resumo em
vínculo) e mesmo assim explicou só 3 dos 8 dias: a cadeia morre no marco
`Recebimento do Relatório de Sondagem`, que andou 6 dias enquanto sua única
predecessora não se moveu.

---

## Feito em 14/08/26 — as duas correções de código

**Coerência de datas só em tarefa não iniciada** (`comparador/rede.py`,
`_respeitado()`). Depois que a tarefa começou, a data é fato e o vínculo continua
valendo como trilha de causa. Isso devolveu à análise as 223 ligações FS que
eram descartadas sem motivo.

**Caminhada atravessa tarefa-resumo** (`comparador/rede.py`, `_condutora()`).
Quando o vínculo aponta para um resumo, a caminhada segue pela filha que termina
junto com ele — a que de fato manda no término. Resultado no Pirajuçara, o caso
que originou tudo: a cadeia foi de 2 para 3 elos e os ofensores passaram a somar
**6 de 6 dias**, contra 1 de 6 antes. A tarefa que ficava sem dono
(`Projeto Legal > Arquitetura > Projeto Legal > Análise`, +5 dias) agora sai
nomeada no report.

O resíduo previsto continua: o Palhano explica 3 dos 8 dias, porque lá a tarefa
andou sem que nenhuma predecessora andasse — é o item 2 acima, que nenhuma
mudança de código resolve.

## Feito em 13/08/26

- Barra de progresso no botão Atualizar, com andamento real vindo do fetcher.
- Bloco `📌 RESUMO` do report reescrito em 4 linhas, com o percentual de variação
  sobre a Linha de Base.
- Cabeçalhos do comparativo em emoji + caixa alta (`🤔 O QUE MUDOU…`,
  `🚨PRINCIPAIS OFENSORES`), no padrão das demais seções — o report é lido como
  texto puro, e `##`/`**` apareciam crus.
- Corrigido cabeçalho de seção grudado no primeiro item quando a seção está vazia.
