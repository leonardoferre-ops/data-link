# Banco Local

API gratuita para montar um banco e consultar com Python. Os dados ficam num arquivo SQLite nesta máquina (`data/banco.db`). Não precisa de conta, chave nem serviço pago.

A coleção `livros` já vem carregada (literatura brasileira) para você testar filtro, ordenação e SQL.

## Subir a API

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8741
```

- Documentação interativa: http://127.0.0.1:8741/docs
- Saúde: http://127.0.0.1:8741/saude

A API não tem autenticação. Deixe ela só em `127.0.0.1`.

## Consultar com Python

```python
from cliente import Banco

with Banco("http://127.0.0.1:8741") as banco:
    resultado = banco.consultar(
        "livros",
        colunas=["titulo", "autor", "ano", "preco"],
        filtros=[
            {"coluna": "preco", "op": "menor", "valor": 40},
            {"coluna": "autor", "op": "contem", "valor": "Amado"},
        ],
        ordenar=[{"coluna": "ano", "direcao": "asc"}],
    )
    for livro in resultado["linhas"]:
        print(livro["titulo"], livro["preco"])
```

O script `exemplos/consultas.py` faz esse caminho completo: filtra a coleção de livros, agrega por autor e grava um contato.

```bash
python exemplos/consultas.py
```

SQL somente leitura, com parâmetros:

```python
banco.sql(
    "SELECT titulo, ano FROM livros WHERE autor = ? ORDER BY ano",
    ["Machado de Assis"],
)
```

`/sql` abre o arquivo em modo somente leitura. `INSERT`, `UPDATE`, `DELETE`, `DROP` e uma segunda frase separada por `;` são recusados.

## Gravar dados

```python
banco.criar_tabela(
    "contatos",
    [
        {"nome": "nome", "tipo": "texto", "obrigatorio": True},
        {"nome": "cidade", "tipo": "texto"},
        {"nome": "ativo", "tipo": "booleano", "obrigatorio": True},
    ],
)

banco.inserir("contatos", {"nome": "Lia Nunes", "cidade": "Salvador", "ativo": True})
banco.listar("contatos", cidade="Salvador")
banco.atualizar("contatos", 1, {"cidade": "Lauro de Freitas"})
banco.apagar("contatos", 1)
```

Tipos de coluna: `texto`, `inteiro`, `decimal`, `booleano`.

Toda tabela ganha `id` e `criado_em` (UTC). Nomes de tabela e coluna usam letras, números e `_`, até 48 caracteres.

## Filtros

| Operador | Uso |
| --- | --- |
| `igual`, `diferente` | comparação exata |
| `contem`, `comeca_com`, `termina_com` | texto; `%` e `_` são literais |
| `maior`, `menor`, `maior_igual`, `menor_igual` | número ou texto |
| `em` | lista de 1 a 100 valores |
| `nulo`, `nao_nulo` | sem valor |

`limite` vai de 1 a 500. A resposta traz `total` para paginar com `deslocamento`.

Na URL, parâmetros que não sejam `limite`, `deslocamento`, `ordenar` ou `direcao` viram filtro de igualdade:

```bash
curl "http://127.0.0.1:8741/tabelas/livros/linhas?genero=romance&limite=5&ordenar=ano"
```

## Rotas

| Método | Caminho | O que faz |
| --- | --- | --- |
| `GET` | `/tabelas` | lista as tabelas |
| `POST` | `/tabelas` | cria uma tabela |
| `DELETE` | `/tabelas/{nome}` | apaga a tabela |
| `POST` | `/tabelas/{nome}/linhas` | insere até 200 linhas |
| `GET` | `/tabelas/{nome}/linhas` | lista, com igualdade na query string |
| `PATCH` | `/tabelas/{nome}/linhas/{id}` | atualiza colunas |
| `DELETE` | `/tabelas/{nome}/linhas/{id}` | apaga a linha |
| `POST` | `/consulta` | filtros, colunas, ordem e página |
| `POST` | `/sql` | um `SELECT` parametrizado |

O arquivo do banco pode mudar com a variável `BANCO_CAMINHO`. `BANCO_SEM_EXEMPLO=1` sobe a API sem a coleção `livros`. `BANCO_URL` é o endereço que o cliente usa quando você não passa a URL no código.

## Testes

```bash
pytest
```
