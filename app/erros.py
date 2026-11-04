"""Erro de domínio convertido em resposta HTTP pela API."""


class ErroConsulta(Exception):
    def __init__(self, status: int, mensagem: str) -> None:
        self.status = status
        self.mensagem = mensagem
        super().__init__(mensagem)
