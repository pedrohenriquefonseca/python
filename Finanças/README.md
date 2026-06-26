# Finanças — Analisador de gastos e orçamentos

Portal web (Flask + SQLite) para acompanhar **orçamentos mensais por categoria**
em tempo hábil, a partir de extratos **OFX** da conta corrente e do cartão.

## Estado atual (v0)
- ✅ Importação de OFX (conta e cartão) e de fatura XLSX do cartão (Itaú), sem duplicar lançamentos reimportados
- ✅ Categorização automática por regras + correção manual que vira regra
- ✅ Orçamentos mensais por categoria com barra de progresso ("ritmo do mês", teto em 80% da trilha) e **projeção de ritmo**
- ✅ Dashboard redesenhado em grade modular densa: sidebar escura, card de patrimônio líquido, composição do patrimônio (barra empilhada: bens/investimentos/bancos), gráfico de fluxo mensal (receita x gasto x orçado) e evolução patrimonial em linha
- ✅ Bens (imóveis, veículos etc.) e transferências entre contas no lançamento
- 🔜 (futuro) Integração Open Finance via agregador (Pluggy) para tempo real

## Como rodar

```powershell
cd "C:\Apps Python\Repos\Python\Finanças"
pip install -r requirements.txt      # só Flask
python seed.py                       # opcional: dados de exemplo p/ visualizar
python app.py                        # abre em http://127.0.0.1:5005
```

Para começar do zero (sem exemplo), apague `financas.db` e rode `python app.py`.

## Fluxo de uso
1. **Contas** → cadastre sua conta corrente e o cartão.
2. **Importar** → suba o extrato OFX (conta/cartão) ou a fatura XLSX do cartão (Itaú).
3. **Orçamentos** → defina o teto mensal de cada categoria.
4. **Lançamentos** → ajuste categorias erradas (marque "regra" para o app aprender), registre transferências entre contas e bens.
5. **Dashboard** → acompanhe patrimônio líquido, composição do patrimônio, consumo do orçamento e a projeção de fim de mês.

## Arquivos
| Arquivo | Papel |
|---|---|
| `app.py` | Rotas Flask e lógica de orçamento/ritmo/patrimônio |
| `db.py` | Schema e conexão SQLite |
| `ofx_import.py` | Parser de OFX (1.x SGML e 2.x XML) |
| `xls_import.py` | Parser de fatura XLSX do cartão (Itaú) |
| `categorizer.py` | Categorização por regras |
| `seed.py` | Dados de exemplo |

## Notas para retomar em outra máquina
- `financas.db` é versionado no repo (dados reais ficam no próprio banco). Os arquivos `financas.db.bak-*` são backups locais pontuais e **não** devem ser commitados.
- Design do dashboard é decisão fechada: sidebar escura, card de patrimônio líquido, seção "Bens", gráfico de fluxo de 3 linhas (receita/gasto/orçado) e ícones por categoria (`CATEGORY_ICONS` em `app.py`).
- Categorias com ícone já mapeado: Moradia, Transporte, Alimentação, Mercado, Saúde, Lazer, Assinaturas, Salário, Outros, Cuidados Pessoais, Compras, Juros e Impostos, Transferência. Categoria nova sem ícone cai no ícone genérico.
