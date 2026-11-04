from cliente import Banco


def _criar_contatos(cliente):
    resposta = cliente.post(
        "/tabelas",
        json={
            "nome": "contatos",
            "colunas": [
                {"nome": "nome", "tipo": "texto", "obrigatorio": True},
                {"nome": "cidade", "tipo": "texto"},
                {"nome": "idade", "tipo": "inteiro"},
                {"nome": "ativo", "tipo": "booleano", "obrigatorio": True},
            ],
        },
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_saude_e_inicio(cliente):
    assert cliente.get("/saude").json()["status"] == "ok"
    corpo = cliente.get("/").json()
    assert corpo["docs"] == "/docs"


def test_cria_insere_filtra_e_atualiza(cliente):
    esquema = _criar_contatos(cliente)
    assert [coluna["nome"] for coluna in esquema["colunas"]][:2] == ["id", "criado_em"]

    criado = cliente.post(
        "/tabelas/contatos/linhas",
        json={
            "linhas": [
                {"nome": "Ana", "cidade": "Recife", "idade": 31, "ativo": True},
                {"nome": "100% real", "cidade": "Recife", "idade": 22, "ativo": False},
                {"nome": "Bia", "cidade": "Olinda", "idade": 40, "ativo": True},
            ]
        },
    )
    assert criado.status_code == 201, criado.text
    assert criado.json()["linhas"][0]["ativo"] is True

    repetida = cliente.post(
        "/tabelas",
        json={"nome": "contatos", "colunas": [{"nome": "nome", "tipo": "texto"}]},
    )
    assert repetida.status_code == 409

    consulta = cliente.post(
        "/consulta",
        json={
            "tabela": "contatos",
            "colunas": ["nome", "idade"],
            "filtros": [
                {"coluna": "cidade", "op": "igual", "valor": "Recife"},
                {"coluna": "idade", "op": "menor", "valor": 30},
            ],
            "ordenar": [{"coluna": "nome", "direcao": "asc"}],
        },
    )
    assert consulta.status_code == 200, consulta.text
    corpo = consulta.json()
    assert corpo["total"] == 1
    assert corpo["linhas"] == [{"nome": "100% real", "idade": 22}]

    contem = cliente.post(
        "/consulta",
        json={
            "tabela": "contatos",
            "filtros": [{"coluna": "nome", "op": "contem", "valor": "%"}],
        },
    )
    assert [linha["nome"] for linha in contem.json()["linhas"]] == ["100% real"]

    lista = cliente.get("/tabelas/contatos/linhas", params={"cidade": "Olinda", "ativo": "true"})
    assert lista.status_code == 200
    assert lista.json()["total"] == 1
    assert lista.json()["linhas"][0]["nome"] == "Bia"

    identificador = criado.json()["linhas"][2]["id"]
    editado = cliente.patch(
        f"/tabelas/contatos/linhas/{identificador}",
        json={"valores": {"cidade": "Paulista"}},
    )
    assert editado.status_code == 200
    assert editado.json()["cidade"] == "Paulista"

    assert cliente.delete(f"/tabelas/contatos/linhas/{identificador}").status_code == 204
    assert cliente.get(f"/tabelas/contatos/linhas/{identificador}").status_code == 404


def test_rejeita_escrita_sql_e_valor_injetado(cliente):
    _criar_contatos(cliente)
    cliente.post(
        "/tabelas/contatos/linhas",
        json={"linhas": [{"nome": "'; DROP TABLE contatos; --", "ativo": True}]},
    )
    ataque = cliente.post(
        "/sql",
        json={"sql": "DROP TABLE contatos"},
    )
    assert ataque.status_code == 400

    duplo = cliente.post(
        "/sql",
        json={"sql": "SELECT * FROM contatos; DROP TABLE contatos"},
    )
    assert duplo.status_code == 400

    leitura = cliente.post(
        "/sql",
        json={"sql": "SELECT nome FROM contatos WHERE nome = ?", "parametros": ["'; DROP TABLE contatos; --"]},
    )
    assert leitura.status_code == 200
    assert leitura.json()["linhas"][0]["nome"].startswith("'; DROP TABLE")
    assert cliente.get("/tabelas/contatos").status_code == 200

    troca = cliente.post("/sql", json={"sql": "SELECT replace('ab', 'a', 'c') AS texto"})
    assert troca.status_code == 200
    assert troca.json()["linhas"] == [{"texto": "cb"}]


def test_agregacao_e_exemplo(cliente_exemplo):
    resposta = cliente_exemplo.post(
        "/sql",
        json={
            "sql": "SELECT autor, COUNT(*) AS quantidade FROM livros GROUP BY autor ORDER BY quantidade DESC"
        },
    )
    assert resposta.status_code == 200, resposta.text
    quantidades = {linha["autor"]: linha["quantidade"] for linha in resposta.json()["linhas"]}
    assert quantidades["Machado de Assis"] == 2
    assert quantidades["Jorge Amado"] == 2

    baratos = cliente_exemplo.post(
        "/consulta",
        json={
            "tabela": "livros",
            "filtros": [{"coluna": "preco", "op": "menor_igual", "valor": 35}],
            "ordenar": [{"coluna": "preco", "direcao": "asc"}],
        },
    )
    titulos = [linha["titulo"] for linha in baratos.json()["linhas"]]
    assert titulos[0] == "O Quinze"


def test_nome_reservado_e_coluna_obrigatoria(cliente):
    ruim = cliente.post(
        "/tabelas",
        json={"nome": "sqlite_segredo", "colunas": [{"nome": "nome", "tipo": "texto"}]},
    )
    assert ruim.status_code == 422

    _criar_contatos(cliente)
    faltando = cliente.post("/tabelas/contatos/linhas", json={"linhas": [{"nome": "Sem flag"}]})
    assert faltando.status_code == 400
    assert cliente.delete("/tabelas/contatos").status_code == 204
    assert cliente.get("/tabelas/contatos").status_code == 404


def test_cliente_python(cliente):
    with Banco(cliente_http=cliente) as banco:
        banco.criar_tabela(
            "notas",
            [{"nome": "texto", "tipo": "texto", "obrigatorio": True}],
        )
        gravadas = banco.inserir("notas", {"texto": "primeira"})
        assert gravadas[0]["texto"] == "primeira"
        consulta = banco.consultar(
            "notas",
            filtros=[{"coluna": "texto", "op": "comeca_com", "valor": "pri"}],
        )
        assert consulta["total"] == 1
        banco.apagar("notas", gravadas[0]["id"])
