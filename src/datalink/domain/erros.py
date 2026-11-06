"""Erro de domínio convertido em resposta HTTP pela API."""


class ErroConsulta(Exception):  # noqa: N818  # nome de domínio já usado pela API
    """Falha de consulta com status HTTP e mensagem segura."""

    def __init__(self, status: int, mensagem: str) -> None:
        """Guarda o status e a mensagem exibidos ao cliente."""
        self.status = status
        self.mensagem = mensagem
        super().__init__(mensagem)
