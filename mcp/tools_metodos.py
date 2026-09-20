from typing import Annotated, Literal

from pydantic import Field

from rest_client import get


def register(mcp):
    @mcp.tool()
    async def metodos_listar(moagem: Literal["fina", "média", "grossa"] | None = None) -> dict:
        """Lista métodos e parâmetros recomendados; filtra opcionalmente por moagem. GET /metodos."""
        return await get("metodos", "/metodos", moagem=moagem)

    @mcp.tool()
    async def metodos_obter(id: Annotated[int, Field(gt=0)]) -> dict:
        """Consulta proporção, moagem, temperatura e tempo de um método pelo ID. GET /metodos/{id}."""
        return await get("metodos", f"/metodos/{id}")
