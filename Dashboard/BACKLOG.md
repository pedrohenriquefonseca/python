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

## Feito em 17/09/26 — o e-mail do Report Fornecedores virou imagem

A tela tinha régua de meses com barras coloridas por fornecedor; o e-mail parava
numa coluna de texto com "Em andamento · 42%". Levar o gantt para lá custou duas
tentativas, e a primeira foi um beco.

**O que não deu certo: gantt em HTML.** A régua foi desenhada com o único recurso
que o Word parecia respeitar — célula com `bgcolor` e largura em pixel —, pintada
pixel a pixel num vetor e comprimida em células, com as três tiras de cada
entrega compartilhando os mesmos cortes para ele não brigar por duas larguras na
mesma coluna. Fechava na régua, fechava num renderizador em PIL feito para
conferir. Colado de verdade no Outlook, o Word ignorou a largura das células,
espremeu a coluna dos documentos a um terço e quebrou cada código no hífen. Não
há CSS que o convença: ele remonta a tabela com as regras dele, e conferir por
parser ou por desenho próprio não substitui colar no alvo.

**O que ficou: uma imagem.** `report_fornecedores/imagem.py` desenha o relatório
do fornecedor em PIL e o botão põe o PNG no clipboard. O Word não redesenha um
PNG — cola o que recebeu e, no máximo, reduz para caber na página.

Livre do Word, o desenho voltou a ser o da tela, e melhor:

- a grade dos meses e o fio de hoje são duas linhas contínuas do cabeçalho ao
  rodapé, em vez de um pedaço por linha que precisava casar com a altura do texto
  ao lado para não se partir;
- uma entrega é uma linha: a coluna de documentos mostra os códigos que couberem
  e conta os outros num +N;
- o gantt é só meses, todos da mesma largura: a área visível — do fio que o
  separa da tabela até a margem direita da imagem — se divide em n partes iguais
  e não sobra coluna vazia em ponta nenhuma. Foram três passadas até acertar, e
  as três só apareciam ao cotar o desenho: reservar um valor fixo nas pontas
  deixava o vazio maior que os meses; dividir em n+2 partes media só a coluna da
  régua, sem os 6 px do fio e sem a margem, dando pontas de 48 e 58 contra 42; e
  desenhar divisa só entre meses fazia a primeira faixa visível valer sobra mais
  mês;
- toda barra escreve as duas datas, em dd/mm: início à esquerda, término à
  direita; a ponta sem espaço junta as duas do lado que tem ("27/08 – 23/09").
  Escritas por cima do fio de hoje, num respiro branco (18/09/26 — antes a data
  sem espaço sumia, em 17% das barras a de início e 28% a de término);
- a barra é o período da etapa e só. O trecho escuro do percentual executado saiu,
  e com ele o fio vermelho que marcava atraso: percentual de execução é conversa
  de dentro de casa, e mandado ao fornecedor vira discussão sobre o número em vez
  da data que ele tem de cumprir;
- hoje é uma etiqueta em pé no alto do fio, branco sobre o mesmo vermelho, em
  9 px — menor que isso a suavização junta as letras. Em pé porque deitada
  cobriria dois meses da régua; no alto porque ali não tapa barra nenhuma. PIL
  não escreve na vertical: o texto é desenhado deitado numa tira, girado 270° e
  colado, com a caixa saindo da métrica real do texto e não do corpo da fonte;
- sem nota de rodapé: quem recebe a mensagem lê um gantt, não a legenda de um, e
  o parágrafo que explicava a régua tomava três linhas ao pé de toda mensagem.

O tamanho levou duas correções depois do primeiro desenho. A imagem saía com
2200 px, e o Outlook encolhe para a largura do corpo qualquer imagem maior que
ela — encolher um desenho de texto é o mesmo que apagá-lo. E os documentos iam
todos, quebrados em quantas linhas fossem precisas, o que empurrava uma
disciplina para seis ou oito linhas e afastava a barra da data que ela desenha.

Ficou em 700 px fixos, com as colunas de texto constantes — documentos 240,
versão 52 ou 120, início 62, término 62 — e os 252 que sobram indo inteiros para
a régua. As fontes não encolhem: 11 px nos dados, 10 px nas notas, o piso abaixo
do qual a suavização come a letra.

A 700 px o gantt fica apertado, e vale saber por quê: as datas aparecem duas
vezes por linha, nas colunas INÍCIO/TÉRMINO e nas pontas da barra. Sobram 172 px
úteis de régua para quatro meses, e nos cronogramas que nomeiam a etapa por
extenso — 30 dos 50 fornecedores — a coluna da versão toma 120 px e a régua fica
com 104. Tirar as colunas INÍCIO/TÉRMINO devolveria 124 px sem perder informação
nenhuma.

A coluna Situação saiu: quem diz em que pé a etapa está é a própria barra — onde
ela cai em relação ao fio de hoje e quanto dela já saiu no tom escuro. A única
coisa que a barra não dizia sozinha era o atraso, e por isso etapa em curso com o
término vencido ganhou um fio vermelho deitado rente a ela, no lugar onde isso se
lê. A situação escrita continua na lista em texto, que vai no mesmo clipboard.

**O que se perde:** o que chega ao fornecedor não é mais texto — não dá para
copiar um código de dentro da imagem. Por isso o clipboard leva `image/png` e
`text/plain` no mesmo item: quem colar num campo sem formatação recebe a lista
escrita. O JSON da tela perdeu o HTML de cada fornecedor e ganhou esse texto: no
Sede 2 a resposta caiu de cerca de 1 MB para 71 KB.

A imagem é desenhada sob demanda, no clique, por
`GET /api/report-fornecedores/<id>/imagem/<indice>` — 162 KB no pior caso dos 12
snapshots (Horizontes no Sede 2, 41 linhas, 700x2449), altura média de 451 px,
com paleta de 128 cores, que corta o arquivo a 40% sem diferença visível. As 50
imagens saem em 2,3 s.

Sobrou de compartilhado em `report_fornecedores.py` a régua — escala do
fornecedor e conversão de data em pixel —, para a tela e a imagem lerem o
cronograma da mesma maneira.

## Feito em 17/09/26 — Report Fornecedores: triagem refeita

A regra antiga tirava do relatório o documento inteiro enquanto uma análise do
Cliente estivesse em curso. Na Revisão Quintino do Sede 2 isso apagava os dois
documentos de GEOMETRIA do André Baptista — a Análise 01 estava em 73% —, embora
a etapa `b` dele começasse em 21/09, no mesmo dia da etapa `a` de SINALIZAÇÃO,
que aparecia. Eram 34 documentos travados só nesse projeto.

A triagem inteira foi trocada:

- **Recorte por recurso.** Entra todo recurso que não seja o Cliente. O mapa de
  grupos do Cronograma de Alocação saiu da conta — não há mais "recurso sem
  grupo definido" nem o aviso correspondente na tela. Marco e tarefa inativa
  seguem fora: uma é data e não entrega, a outra o Project nem agenda.
- **Escolha por documento.** Com trabalho em andamento, vão todas as etapas em
  andamento **mais a etapa seguinte** — a que começa mais perto do término desse
  trabalho. Sem nada em andamento, vai só a próxima etapa, a que começa mais
  perto de hoje. Datas empatadas entram juntas, como antes.
- **Análise do Cliente deixou de travar o documento.** A etapa seguinte já tem
  data no cronograma, e é ela que o fornecedor precisa ver chegando.

`triagem.pais_na_mao_do_cliente` e `report_fornecedores._fornecedores_do_snapshot`
foram removidas, junto com a chave `desconhecidos` da resposta.

Efeito nos 12 snapshots: 465 → 780 documentos no total. Sede 2 sai de 309/81
linhas para 491/138; Palhano, de 150/39 para 178/50. Oito projetos que saíam
vazios — nenhum recurso classificado como `Fornecedores` — passaram a ter
relatório.

## Feito em 24/09/26 — ofensores pela rede inteira, não por uma trilha

O 9225 atrasou 15 dias e o report apontou só o Concreto. Seis disciplinas
(Concreto, Climatização, Pavimentação, PCI, Detecção e Alarme, SPDA) correm em
ramos paralelos até o fim do projeto, e a `1a Emissão` de cada uma esticou 18
dias úteis. A correção de 16/09 não pegava: ela só olhava empates entre
predecessoras diretas de uma mesma sucessora, e a caminhada começava em UMA
folha final e subia só pela vencedora.

`rede.causa_do_prazo` foi reescrita como varredura: parte de todas as folhas
finais e sobe por todo vínculo que está empurrando. Isso também fecha os outros
buracos levantados no diagnóstico:

- vínculos SS, FF e SF (antes só FS fazia sentido);
- folga que absorve parte do atraso (antes o deslocamento tinha de casar em ±3 dias);
- resumo com várias filhas empatadas, e vínculo no resumo da sucessora;
- marco com várias predecessoras empatadas;
- tarefa incluída desde o último report (linha própria, com a duração);
- tarefa com duração não comparável no caminho (nomeada, sem número);
- corte em 3 ofensores retirado (`TOPO_OFENSORES` e `_topo` saíram).

Nos 12 projetos com base salva só o 9225 mudou: agora saem as seis
disciplinas. Os demais saem idênticos. Os 15 cenários sintéticos (um por caso)
passam.

## Feito em 16/09/26 — causas paralelas entram todas nos ofensores

O Edson Pisani atrasou 39 dias corridos e o report apontou UMA ofensora. Sete
disciplinas do `Atendimento a Comentários e Documentação` (Estabilidade de
Taludes, Estruturas de Concreto, Estruturas Metálicas, Hidrossanitário,
Elétricas e SPDA, CFTV, Cabeamento) começam no mesmo dia, esticaram os mesmos 25
dias úteis, terminam no mesmo dia e entram no mesmo `1o Ciclo`. Não há maior
entre elas: `empurrador` montava as sete como candidatas, ordenava por
deslocamento e ficava com a primeira da lista de predecessoras do Project
(`rede.py`, `candidatas[0]`). O report acusava uma disciplina e absolvia seis
idênticas.

Agora `empurrador` devolve, em `empates`, as candidatas que **terminam no mesmo
dia** da vencedora — é o término que fixa o início da sucessora, então elas são
responsáveis na mesma medida. Todas entram na cadeia e viram ofensoras; a
caminhada segue só pela vencedora, sem fanar a busca. Empate medido por data, não
por deslocamento: datas não precisam da tolerância de `TOL_DIAS`.

`TOPO_OFENSORES` continua 3, mas o corte não parte empate ao meio
(`comparador._topo`): estende enquanto o próximo tiver o mesmo aumento do último
que entrou. Com aumentos distintos o resultado é o de antes, três linhas. No
Edson Pisani saem as sete. Os outros 11 projetos da carteira não mudaram — o
Pompéia segue com uma ofensora, e os demais não tiveram aumento de prazo.

Fora do escopo por decisão: as sete linhas repetem "25 dias úteis" cada uma, e
somadas dariam 175 contra um atraso de 39. São paralelas, não sequenciais. O
report não avisa isso.

## Feito em 15/09/26 — restrição de data vira KPI da Análise de Saúde

Parte do item 2 que dá para medir: restrição de data aparece no snapshot
(`restricao`, `restricaoData`) e a Análise de Saúde aponta toda tarefa fora da
regra — só marco com Não Iniciar Antes De. Peso 20, limite 5%. Arrastar tarefa na
mão continua fora do alcance: não deixa marca no Project.

52 tarefas apontadas na carteira; Alves Ribeiro, Edson Pisani e Vila Gilda caem de
100 para 80. Detalhe em `PROJETO.txt`, seção 17.

## Feito em 11/09/26 — sai "Configurações" da barra lateral

O item ficava na seção Sistema sem tela nem ação por trás: clicar não levava a
lugar nenhum. Removido do `index.html`; nada mais o referenciava.

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
