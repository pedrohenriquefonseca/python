# Finanças — Analisador de gastos e orçamentos

Portal web (Flask + SQLite) para acompanhar **orçamentos mensais por categoria**
em tempo hábil, a partir de extratos **OFX** da conta corrente e do cartão.

## Estado atual (v0)
- ✅ Importação de OFX (conta e cartão), sem duplicar lançamentos reimportados
- ✅ Categorização automática por regras + correção manual que vira regra
- ✅ Orçamentos mensais por categoria com barra de progresso e **projeção de ritmo**
- ✅ Dashboard do mês: gasto, orçamento, entradas, alertas
- 🔜 Investimentos, bens e evolução patrimonial
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
2. **Importar OFX** → exporte o extrato no banco e suba o arquivo.
3. **Orçamentos** → defina o teto mensal de cada categoria.
4. **Lançamentos** → ajuste categorias erradas (marque "regra" para o app aprender).
5. **Dashboard** → acompanhe o consumo do orçamento e a projeção de fim de mês.

## Arquivos
| Arquivo | Papel |
|---|---|
| `app.py` | Rotas Flask e lógica de orçamento/ritmo |
| `db.py` | Schema e conexão SQLite |
| `ofx_import.py` | Parser de OFX (1.x SGML e 2.x XML) |
| `categorizer.py` | Categorização por regras |
| `seed.py` | Dados de exemplo |
