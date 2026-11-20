"""Usa as portas locais do .env nos verificadores, sem carregar credenciais."""
import os
from pathlib import Path

from dotenv import dotenv_values


def configure_ports():
    values = dotenv_values(Path(__file__).resolve().parents[1] / ".env")
    for name, default in {"GRAOS_PORT":"8001", "METODO_PORT":"8002", "DEGUSTACAO_PORT":"8003",
                          "MCP_PORT":"8004", "CHAT_PORT":"8005", "CLIENT_PORT":"8080"}.items():
        os.environ.setdefault(name, values.get(name) or default)
    os.environ.setdefault("MCP_TEST_URL", f'http://127.0.0.1:{os.environ["MCP_PORT"]}/mcp')
    os.environ.setdefault("CLIENT_TEST_URL", f'http://127.0.0.1:{os.environ["CLIENT_PORT"]}')
    bypass = {part.strip() for part in os.getenv("NO_PROXY", "").split(",") if part.strip()}
    os.environ["NO_PROXY"] = ",".join(sorted(bypass | {"localhost", "127.0.0.1"}))
