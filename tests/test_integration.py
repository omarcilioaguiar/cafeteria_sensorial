"""Testes HTTP/MCP reais. Os POSTs criados aqui são removidos no teardown por ID."""
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from google.genai import types
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from bridge import run_chat

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[1]
SERVICES = [("graos-service", "graos", int(os.getenv("GRAOS_PORT", "8001"))),
            ("metodo-service", "metodos", int(os.getenv("METODO_PORT", "8002"))),
            ("degustacao-service", "degustacoes", int(os.getenv("DEGUSTACAO_PORT", "8003")))]
MCP_URL = os.getenv("MCP_TEST_URL", "http://127.0.0.1:8004/mcp")


@pytest.fixture
def created():
    records = []
    yield records
    # Somente IDs criados pelo próprio teste; não limpa seeds nem dados do usuário.
    for service, record_id in records:
        subprocess.run(["docker", "compose", "exec", "-T", service, "python", "-c",
                        "import sys; from common.database import connection; "
                        "ctx=connection(); conn=ctx.__enter__(); "
                        "conn.execute('DELETE FROM registros WHERE id = %s', (int(sys.argv[1]),)); "
                        "ctx.__exit__(None,None,None)", str(record_id)], cwd=ROOT, check=True)


@pytest.mark.parametrize("service,path,port", SERVICES)
def test_rest_crud_contract(service, path, port, created):
    with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=5) as client:
        assert client.get("/health").status_code == 200
        response = client.get(f"/{path}")
        assert response.status_code == 200 and len(response.json()) > 0
        seed = json.loads((ROOT / service / "seed.json").read_text())[0]
        response = client.post(f"/{path}", json=seed)
        assert response.status_code == 201, response.text
        record = response.json()
        created.append((service, record["id"]))
        assert response.headers["location"] == f"/{path}/{record['id']}"
        assert client.get(response.headers["location"]).json() == record
        assert client.get(f"/{path}/999999999").status_code == 404
        assert client.get(f"/{path}/-1").status_code == 422
        assert client.post(f"/{path}", json={}).status_code == 422
        assert client.post(f"/{path}", json={**seed, "id":42}).status_code == 422


def test_filters_and_validation():
    with httpx.Client(timeout=5) as client:
        grains = client.get(f"http://127.0.0.1:{SERVICES[0][2]}/graos", params={"regiao":"Chapada Diamantina", "processo":"natural"}).json()
        assert grains and all(g["origem"]["regiao"] == "Chapada Diamantina" and g["processo"] == "natural" for g in grains)
        methods = client.get(f"http://127.0.0.1:{SERVICES[1][2]}/metodos", params={"moagem":"grossa"}).json()
        assert methods and all(m["moagem"] == "grossa" for m in methods)
        base = f"http://127.0.0.1:{SERVICES[2][2]}"
        tastings = client.get(base + "/degustacoes", params={"grao_id":1}).json()
        assert tastings and all(t["grao_id"] == 1 for t in tastings)
        assert client.get(base + "/graos/1/degustacoes").json() == tastings
        invalid = json.loads((ROOT / "degustacao-service/seed.json").read_text())[0]
        invalid["avaliacao"]["acidez"] = 6
        assert client.post(base + "/degustacoes", json=invalid).status_code == 422
        invalid["avaliacao"]["acidez"] = 4
        invalid["nota_final"] = 11
        assert client.post(base + "/degustacoes", json=invalid).status_code == 422


async def test_six_mcp_tools_reach_real_endpoints():
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
            assert names == {f"{domain}_{action}" for domain in ["graos", "metodos", "degustacoes"] for action in ["listar", "obter"]}
            for name in sorted(names):
                result = await session.call_tool(name, {"id":1} if name.endswith("obter") else {})
                assert not result.isError, result
                assert json.loads(result.content[0].text)["data"]
            assert (await session.call_tool("graos_obter", {"id":999999999})).isError
            assert (await session.call_tool("graos_obter", {"id":-1})).isError


async def test_chat_bridge_with_real_mcp_and_simulated_model():
    calls = [types.Part(function_call=types.FunctionCall(name=f"{domain}_listar", args={}, id=f"call_{domain}")) for domain in ["graos", "metodos", "degustacoes"]]
    model = SimpleNamespace(models=SimpleNamespace(generate_content=AsyncMock(side_effect=[
        types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role="model", parts=calls))]),
        types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role="model", parts=[types.Part.from_text(text="Dados consultados nos três serviços.")]))]),
    ])))
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await run_chat(model, session, "Compare os cafés.", [], "simulated-model")
    assert len(result["tools_used"]) == 3
    outputs = [part.function_response for content in model.models.generate_content.call_args.kwargs["contents"] for part in content.parts if part.function_response]
    assert len(outputs) == 3
    assert all(item.response["is_error"] is False for item in outputs)


def test_client_proxy_and_chat_tool_discovery():
    base = os.getenv("CLIENT_TEST_URL", "http://127.0.0.1:8080")
    with httpx.Client(timeout=15) as client:
        assert client.get(base).status_code == 200
        for _, path, _ in SERVICES:
            response = client.get(f"{base}/api/{path}/{path}")
            assert response.status_code == 200 and isinstance(response.json(), list)
        assert len(client.get(base + "/api/chat/tools").json()["tools"]) == 6
