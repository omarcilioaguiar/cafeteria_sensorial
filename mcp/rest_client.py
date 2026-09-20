import os

import httpx
from mcp.server.fastmcp.exceptions import ToolError

URLS = {
    "graos": os.getenv("GRAOS_URL", "http://graos-service:8000"),
    "metodos": os.getenv("METODO_URL", "http://metodo-service:8000"),
    "degustacoes": os.getenv("DEGUSTACAO_URL", "http://degustacao-service:8000"),
}


async def get(service: str, path: str, **params) -> dict:
    """Cada ferramenta consulta REST; o MCP nunca acessa o PostgreSQL."""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0), trust_env=False) as client:
            response = await client.get(
                URLS[service] + path, params={key: value for key, value in params.items() if value is not None}
            )
        if response.status_code == 404:
            raise ToolError(f"{service}: registro não encontrado (404).")
        response.raise_for_status()
        return {"service": service, "data": response.json()}
    except httpx.HTTPStatusError as exc:
        raise ToolError(f"{service}: a API retornou HTTP {exc.response.status_code}.") from exc
    except (httpx.RequestError, ValueError) as exc:
        raise ToolError(f"{service}: serviço indisponível ou resposta inválida. Os outros serviços podem ser consultados.") from exc
