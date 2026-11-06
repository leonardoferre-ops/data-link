from datalink.config.ambiente import (
    caminho_do_banco,
    deve_semear_exemplo,
    diretorio_bruto,
    limite_sql_segundos,
    url_da_api,
)


def test_url_padrao_e_sem_barra_final(monkeypatch) -> None:
    monkeypatch.delenv("BANCO_URL", raising=False)
    assert url_da_api() == "http://127.0.0.1:8741"
    monkeypatch.setenv("BANCO_URL", "http://127.0.0.1:9000/")
    assert url_da_api() == "http://127.0.0.1:9000"


def test_semeadura_e_limite_sql(monkeypatch) -> None:
    monkeypatch.setenv("BANCO_SEM_EXEMPLO", "1")
    assert deve_semear_exemplo() is False
    monkeypatch.setenv("BANCO_SEM_EXEMPLO", "0")
    assert deve_semear_exemplo() is True
    monkeypatch.delenv("BANCO_SQL_SEGUNDOS", raising=False)
    assert limite_sql_segundos() == 2.0
    monkeypatch.setenv("BANCO_SQL_SEGUNDOS", "4.5")
    assert limite_sql_segundos() == 4.5


def test_caminho_cria_diretorio_e_bruto_aponta_para_o_cwd(
    monkeypatch, tmp_path
) -> None:
    destino = tmp_path / "pasta" / "x.db"
    monkeypatch.setenv("BANCO_CAMINHO", str(destino))
    assert caminho_do_banco() == destino.resolve()
    assert destino.parent.is_dir()
    monkeypatch.chdir(tmp_path)
    assert diretorio_bruto() == (tmp_path / "dados" / "bruto").resolve()
