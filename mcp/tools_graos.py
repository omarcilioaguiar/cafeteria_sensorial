from typing import Annotated, Literal

from pydantic import Field

from rest_client import get


def register(mcp):
    @mcp.tool()
    async def graos_listar(regiao: str | None = None, processo: Literal["natural", "lavado", "honey"] | None = None) -> dict:
        """Lista grãos, preços, estoque e notas declaradas. GET /graos; filtros opcionais exatos de região e processo."""
        return await get("graos", "/graos", regiao=regiao, processo=processo)

    @mcp.tool()
    async def graos_obter(id: Annotated[int, Field(gt=0)]) -> dict:
        """Consulta um grão pelo ID, incluindo origem e notas sensoriais. GET /graos/{id}."""
        return await get("graos", f"/graos/{id}")
