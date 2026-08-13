# Backlog — análise de ofensores do report semanal

Contexto: o report aponta atraso total do projeto (ex.: 6 dias) mas lista ofensores
que somam bem menos (ex.: 1 dia). O atraso tem duas origens — tarefa que **esticou**
e tarefa que só foi **empurrada** — e o report lista apenas quem esticou. O número só
fecha quando a caminhada pela rede de dependências alcança todas as tarefas que
esticaram. Hoje ela morre antes.

Medido em 13/08/26 sobre os 16 snapshots em `data/tasks_*.json`.

---

## 1. Ignorar a coerência de datas em tarefa já iniciada  — CÓDIGO

**Onde:** `comparador/rede.py:72`, função `_respeitado()`.

Hoje um vínculo FS é descartado quando a sucessora começa antes do fim da
predecessora. Isso só faz sentido em tarefa **não iniciada**, onde a data ainda é
plano. Depois que a tarefa começou, a data é fato e o vínculo continua válido como
trilha de causa.

Evidência: das 223 ligações FS incoerentes nos 16 cronogramas, **223 têm a sucessora
com pct > 0**. Nenhuma exceção. Sobreposição mediana de 38 dias (p90 = 105), então
afrouxar por tolerância não resolve — a condição tem que ser o início real.

**Correção:** pular a verificação de data quando a sucessora tem `pct > 0`.
**Efeito:** zera a coluna "FS ruim" do relatório de cronogramas (144 tarefas).

## 2. Atravessar tarefa-resumo na caminhada  — CÓDIGO (rede de segurança)

**Onde:** `comparador/rede.py`, `empurrador()`.

Quando a predecessora é uma tarefa-resumo, ela não tem delta (resumos são excluídos
de propósito em `comparador.py:184`, senão contariam duas vezes) e a caminhada para.
Foi o que aconteceu no Pirajuçara: dos 6 dias de atraso, 5 entraram por
`Projeto Legal` (resumo) e ficaram sem dono.

**Correção:** quando a predecessora for resumo, resolver para o filho que determina o
término dele e seguir — análogo ao salto que já existe sobre marcos (`rede.py:114`).
O resumo continua fora da lista de ofensores, servindo só de conduíte.

**Nota:** a correção dos cronogramas (item 3) elimina esse caso na origem. Este item
vale como rede de segurança durante a transição, já que os 10 cronogramas não ficam
prontos no mesmo dia e o report continua saindo enquanto isso.

## 3. Higiene dos cronogramas  — MS PROJECT

Ver `CORRECOES_CRONOGRAMAS.md` para a lista por projeto.

- Nenhum resumo como predecessora ou sucessora — criar tarefas de término de etapa.
- **Término de etapa com duração ZERO.** Com duração 1 dia vira elo comum: entra na
  cadeia e, quando esticar, aparece como ofensor no lugar da tarefa real. Marco o
  código atravessa (`rede.py:114`) e nunca lista como ofensor (`comparador.py:166`).
- A regra é **toda tarefa-folha**, não "toda tarefa de nível 4". O código não olha
  nível: folha é a tarefa cuja próxima na lista tem nível menor ou igual
  (`rede.folhas()`). Há folhas em nível 1, 2 e 3 em quase todos os projetos — o BM
  Prodemge tem 64 folhas em nível 3 e só 10 em nível 4.

**Efeito colateral esperado:** o primeiro report de cada cronograma corrigido sai
pior. As tarefas novas não existem na base gravada do report anterior, ficam sem
delta e podem matar a caminhada como o resumo mata hoje. É um report por projeto, e
o aviso "N tarefa(s) inserida(s)" vai disparar junto.

## 4. Data de tarefa só deve mudar por vínculo  — PROCESSO

O resíduo que nenhuma das correções acima resolve. Se a tarefa é arrastada na mão ou
tem restrição de data fixa, ela anda sem que nada antes dela ande — e não existe
causa a apontar na rede.

Comprovado no Palhano, que já está com os vínculos corrigidos (zero resumo em
vínculo) e mesmo assim explicou só 3 dos 8 dias: a cadeia morre no marco
`Recebimento do Relatório de Sondagem`, que andou 6 dias enquanto sua única
predecessora não se moveu.

---

## Feito nesta sessão (13/08/26)

- Barra de progresso no botão Atualizar, com andamento real vindo do fetcher.
- Bloco `📌 RESUMO` do report reescrito em 4 linhas, com o percentual de variação
  sobre a Linha de Base.
- Cabeçalhos do comparativo em emoji + caixa alta (`🤔 O QUE MUDOU…`,
  `🚨PRINCIPAIS OFENSORES`), no padrão das demais seções — o report é lido como
  texto puro, e `##`/`**` apareciam crus.
- Corrigido cabeçalho de seção grudado no primeiro item quando a seção está vazia.
