from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.responses import JSONResponse

import tools_degustacoes
import tools_graos
import tools_metodos

mcp = FastMCP(
    "Cafeteria Sensorial",
    host="0.0.0.0",
    port=8000,
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["mcp:8000", "localhost:*", "127.0.0.1:*"],
        allowed_origins=["http://localhost:*", "http://127.0.0.1:*"],
    ),
)
tools_graos.register(mcp)
tools_metodos.register(mcp)
tools_degustacoes.register(mcp)


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "ok", "service": "mcp"})


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
