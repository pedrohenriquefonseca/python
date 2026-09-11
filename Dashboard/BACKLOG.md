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

## Feito em 11/09/26 — ofensores só quando o prazo aumenta

Regra do usuário: com a Previsão de Conclusão mantida ou reduzida em relação ao
report anterior, o report semanal não exibe PRINCIPAIS OFENSORES. Antes a seção
saía em qualquer desvio, inclusive de redução. A linha "A Previsão de Conclusão
mudou de X para Y, redução de N" continua no O QUE MUDOU. Condição em
`comparador.secao_semanal` (`saldo > 0`).

## Feito em 11/09/26 — descrição de uso nas férias

A Anotação de Férias guardava só datas e débitos; não havia onde dizer como o
período foi usado. Cada registro ganhou uma descrição livre (até 500
caracteres), preenchida no formulário ou depois, clicando na coluna Descrição do
histórico — assim os registros anteriores ao campo também podem ser descritos.
Datas e débitos seguem sem edição: para corrigir o período, remove-se o registro
e registra-se de novo. Rota nova: `POST /api/ferias/descrever`.

## Feito em 11/09/26 — e-mail do Report Fornecedores refeito para o Word

Colado no Outlook, o e-mail saía desmontado: cada iniciativa era uma tabela com
as colunas numa largura, títulos colados no cabeçalho, códigos quebrados no hífen
e cinzas que sumiam. A causa é o editor do Outlook, que é o Word e remonta o HTML
com as regras dele. Refeito como uma tabela só, com larguras fixas, fonte em cada
célula, faixa cinza por iniciativa, cabeçalho uma vez, um código por linha e um
resumo no topo. Conferido colando no Word via COM (Sede 2, Maira Crivellari, 74
documentos); as regras estão em PROJETO.txt, seção 18.

## Feito em 10/09/26 — Report Fornecedores no lugar de Entregas de Fornecedores

A aba antiga devolvia um texto em Markdown num modal, agrupado por
fornecedor › iniciativa › disciplina e incluindo a Horizontes. Virou tela, com
agrupamento fornecedor › **iniciativa** › **disciplina** › entregas, filtro de
situação e um botão por fornecedor que copia o relatório dele pronto para colar
no corpo de um e-mail do Outlook.

A triagem não mudou — saiu de `entregas/entregas.py` para
`report_fornecedores/triagem.py` sem alteração de regra. O que mudou foi o
recorte (só quem está em `Fornecedores` no grupos_recursos.json; a Horizontes
ficou de fora, porque o relatório é sobre terceiros) e a unidade da linha:
documentos da mesma disciplina que andam na mesma revisão e nas mesmas datas
viram uma linha só. Palhano: 149 documentos em 39 linhas. Sede 2: 306 em 81.

`entregas/`, a rota `POST /api/entregas` e a aba correspondente foram removidas.

## Feito em 18/08/26 — marco não é trabalho

Regra do usuário: tarefa de duração zero pode estar fora do 4º nível e pode não
ter recurso atribuído. O marco delimita o começo ou o fim de uma etapa, então o
lugar dele na EAP é o nível da etapa, e não existe a quem atribuí-lo.

`sem_recurso` já isentava marcos; `fora_nivel4` não. Passou a isentar. Sede 2,
Palhano e Edson Pisani foram a 100 — o que sobrava neles era só marco — e os 15
projetos subiram ou ficaram iguais. Nenhum peso ou limite mudou.

## Feito em 18/08/26 — lista de apontamentos na Saúde do Cronograma

A tela dizia quantas tarefas estão erradas em cada indicador e não dizia quais.
Achar as 49 dependências em resumo do Pirajuçara no meio de 221 linhas do Project
era trabalho manual, e o item 1 acima depende justamente disso.

`saude/saude.py` passou a devolver, junto de cada KPI, a lista das tarefas
apontadas — linha, caminho na EAP, motivo específico, datas e recurso. A tela do
projeto ganhou o card **Apontamentos**: cartão de KPI clicável abre a lista
filtrada por ele, abas trocam o indicador e o cabeçalho da tabela ordena.
Nenhuma nota, peso ou limite mudou.

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
