import pytest
from fastapi.testclient import TestClient

from app.main import criar_aplicacao


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setenv("BANCO_CAMINHO", str(tmp_path / "teste.db"))
    monkeypatch.setenv("BANCO_SEM_EXEMPLO", "1")
    app = criar_aplicacao()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def cliente_exemplo(tmp_path, monkeypatch):
    monkeypatch.setenv("BANCO_CAMINHO", str(tmp_path / "exemplo.db"))
    monkeypatch.delenv("BANCO_SEM_EXEMPLO", raising=False)
    app = criar_aplicacao()
    with TestClient(app) as test_client:
        yield test_client
