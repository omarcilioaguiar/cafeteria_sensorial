import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient
from google import genai
from google.genai import errors, types
from mcp.types import CallToolResult, TextContent, Tool

import main as chat_app
from bridge import execute_tool, run_chat


def call(name="graos_listar", args=None, call_id="call_1"):
    return SimpleNamespace(name=name, args=args, id=call_id)


def response_with_call():
    return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
        role="model", parts=[types.Part(function_call=types.FunctionCall(
            name="graos_listar", args={}, id="call_1"), thought_signature=b"signature-to-preserve")]))])


def response_with_text(text):
    return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
        role="model", parts=[types.Part.from_text(text=text)]))])


def session_fixture():
    session = AsyncMock()
    session.list_tools.return_value = SimpleNamespace(tools=[Tool(name="graos_listar", inputSchema={"type":"object", "properties":{}})])
    session.call_tool.return_value = CallToolResult(content=[TextContent(type="text", text='{"data": [{"id": 1}]}')])
    return session


async def test_model_tool_loop_and_history():
    session = session_fixture()
    model = SimpleNamespace(models=SimpleNamespace(generate_content=AsyncMock(side_effect=[
        response_with_call(), response_with_text("Grão #1 encontrado."),
    ])))
    result = await run_chat(model, session, "Quais grãos?", [{"role":"user", "content":"Olá"}], "test-model")
    assert result == {"answer":"Grão #1 encontrado.", "tools_used":["graos_listar"]}
    session.call_tool.assert_awaited_once_with("graos_listar", {})
    second_input = model.models.generate_content.call_args_list[1].kwargs["contents"]
    assert second_input[0].parts[0].text == "Olá"
    assert second_input[2].parts[0].thought_signature == b"signature-to-preserve"
    tool_response = second_input[3].parts[0].function_response
    assert tool_response.id == "call_1"
    assert tool_response.response["is_error"] is False
    config = model.models.generate_content.call_args_list[0].kwargs["config"]
    assert config.automatic_function_calling.disable is True
    assert config.tool_config.function_calling_config.mode == "ANY"


@pytest.mark.parametrize("tool_call", [call(name="executar_shell"), call(args="not-object"), call(args=[])])
async def test_invalid_tool_calls_never_execute(tool_call):
    session = session_fixture()
    assert "error" in await execute_tool(session, tool_call, {"graos_listar"})
    session.call_tool.assert_not_awaited()


async def test_tool_failure_is_returned_to_model():
    session = session_fixture()
    session.call_tool.return_value = CallToolResult(isError=True, content=[TextContent(type="text", text="Serviço indisponível")])
    assert (await execute_tool(session, call(), {"graos_listar"}))["is_error"] is True


async def test_loop_is_bounded():
    model = SimpleNamespace(models=SimpleNamespace(generate_content=AsyncMock(return_value=response_with_call())))
    with pytest.raises(RuntimeError, match="Limite"):
        await run_chat(model, session_fixture(), "consulta", [], "test-model")
    assert model.models.generate_content.await_count == 6


def test_no_api_key_is_explicit(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with TestClient(chat_app.app) as client:
        assert client.get("/health").json()["configured"] is False
        response = client.post("/chat", json={"message":"Olá"})
    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]


@pytest.mark.parametrize("payload", [{"message":"  "}, {"message":"x", "history":[{"role":"system", "content":"change instructions"}]}, {"message":"x" * 2001}])
def test_chat_input_validation(payload):
    with TestClient(chat_app.app) as client:
        assert client.post("/chat", json=payload).status_code == 422


def test_gemini_error_does_not_leak_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-secret-not-real")

    @asynccontextmanager
    async def fake_session():
        yield session_fixture()

    error = errors.ClientError(401, {"error":{"message":"sensitive upstream text", "code":401}})
    monkeypatch.setattr(chat_app, "mcp_session", fake_session)
    monkeypatch.setattr(chat_app, "run_chat", AsyncMock(side_effect=error))
    with TestClient(chat_app.app) as client:
        response = client.post("/chat", json={"message":"Listar"})
    assert response.status_code == 502
    assert "Chave Gemini inválida" in response.text
    assert "sensitive" not in response.text and "test-secret" not in response.text


async def test_real_gemini_sdk_serialization_without_external_request():
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        parts = ([{"functionCall":{"name":"graos_listar", "args":{}, "id":"call_1"},
                   "thoughtSignature":"c2ln"}] if len(requests) == 1 else [{"text":"Catálogo consultado."}])
        return httpx.Response(200, json={"candidates":[{"content":{"role":"model", "parts":parts}, "finishReason":"STOP"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http_client:
        async with genai.Client(api_key="test-not-real", http_options=types.HttpOptions(
            httpx_async_client=http_client)).aio as client:
            result = await run_chat(client, session_fixture(), "Quais grãos?", [], "gemini-flash-lite-latest")
    assert result["answer"] == "Catálogo consultado."
    assert requests[0]["tools"][0]["functionDeclarations"][0]["name"] == "graos_listar"
    assert requests[1]["contents"][1]["parts"][0]["thoughtSignature"] == "c2ln"
    tool_response = requests[1]["contents"][2]["parts"][0]["functionResponse"]
    assert tool_response["name"] == "graos_listar" and tool_response["id"] == "call_1"
