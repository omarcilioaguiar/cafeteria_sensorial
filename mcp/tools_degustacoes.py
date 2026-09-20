from typing import Annotated

from pydantic import Field

from rest_client import get


def register(mcp):
    @mcp.tool()
    async def degustacoes_listar(grao_id: Annotated[int | None, Field(gt=0)] = None) -> dict:
        """Lista degustações, opcionalmente de um grão. GET /degustacoes. Para ranking, agrupe por grao_id e calcule a média de nota_final (0–10), informando quantidade e empates."""
        return await get("degustacoes", "/degustacoes", grao_id=grao_id)

    @mcp.tool()
    async def degustacoes_obter(id: Annotated[int, Field(gt=0)]) -> dict:
        """Consulta degustação pelo ID: parâmetros reais, acidez/corpo/doçura (1–5), nota final (0–10), comentário e data. GET /degustacoes/{id}."""
        return await get("degustacoes", f"/degustacoes/{id}")
