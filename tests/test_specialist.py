import json
import time
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from fastapi.testclient import TestClient
import pytest

import main
from julgamento import Verdict, evaluate
from semantic_cache import SemanticCache, eligible


@pytest.mark.parametrize("question,history", [
    ("Qual a proporção do grão 1?", []),
    ("Qual a melhor média de degustações?", []),
    ("Como ajustar a moagem?", [{"role":"user", "content":"Usei grão 1"}]),
    ("E essa acidez?", []),
    ("A temperatura não afeta o preparo?", []),
    ("Qual o preço do café com acidez?", []),
])
def test_contextual_or_mutable_questions_bypass_cache(question, history):
    assert not eligible(question, history)


def test_independent_concept_can_use_cache():
    assert eligible("O que significa proporção entre café e água?", [])


def fake_cache(distance=0.1, age=0):
    cache = SemanticCache(path="unused", ttl=60)
    cache.state = "ready"
    cache.model = SimpleNamespace(encode=lambda *args, **kwargs: SimpleNamespace(tolist=lambda: [1., 0.]))
    cache.collection = SimpleNamespace(
        count=lambda: 1,
        query=lambda **kwargs: {"distances":[[distance]], "metadatas":[[
            {"answer":"Uma relação de massas.", "created_at":time.time() - age}]]})
    return cache


@pytest.mark.parametrize("distance,age,hit", [(0.1,0,True),(0.3,0,False),(0.1,61,False),(float('nan'),0,False)])
def test_cache_rejects_distant_expired_and_invalid_results(distance, age, hit):
    assert bool(fake_cache(distance, age).lookup("Explique proporção", "modelo")) == hit


def test_cache_miss_does_not_break_when_storage_fails():
    cache = fake_cache()
    cache.collection.query = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("offline"))
    assert cache.lookup("Explique proporção", "modelo") is None


def test_cache_hit_skips_mcp_llm_and_rate_limit(monkeypatch):
    monkeypatch.setattr(main.semantic_cache, "lookup", lambda *args: {"answer":"Resposta armazenada", "distance":0.05})
    model_call = AsyncMock(side_effect=AssertionError("Não deveria chamar o modelo"))
    monkeypatch.setattr(main, "run_chat", model_call)
    main._request_log.extend([time.monotonic()] * main._RATE_LIMIT)
    with TestClient(main.app) as client:
        result = client.post("/chat", json={"message":"O que é proporção no café?"})
    assert result.status_code == 200
    assert result.json()["cache"]["hit"] is True
    model_call.assert_not_awaited()


@pytest.mark.parametrize("tools,history,use_cache,stored", [
    ([], [], True, True),
    (["metodos_listar"], [], True, False),
    ([], [{"role":"user","content":"Meu café"}], True, False),
    ([], [], False, False),
])
def test_only_independent_tool_free_answers_are_stored(monkeypatch, tools, history, use_cache, stored):
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    monkeypatch.setattr(main.semantic_cache, "lookup", lambda *args: None)
    store = Mock()
    monkeypatch.setattr(main.semantic_cache, "store", store)

    @asynccontextmanager
    async def session():
        yield None

    monkeypatch.setattr(main, "mcp_session", session)
    monkeypatch.setattr(main, "run_chat", AsyncMock(return_value={"answer":"Uma relação de massas.", "tools_used":tools, "evidence":[]}))
    with TestClient(main.app) as client:
        response = client.post("/chat", json={"message":"Explique proporção no preparo de café", "history":history, "use_cache":use_cache})
    assert response.status_code == 200
    assert store.called is stored


def verdict_payload(verdict="ATENDE", correction=True):
    return {"veredicto":verdict,"correcao":correction,"fundamentacao":True,"clareza":True,
            "tratamento_incerteza":True,"respeito_escopo":True,"justificativa":"Critérios avaliados."}


def test_judge_cannot_accept_negative_or_malformed_verdict():
    from pydantic import ValidationError
    assert Verdict.model_validate(verdict_payload()).veredicto == "ATENDE"
    assert Verdict.model_validate(verdict_payload("NÃO ATENDE", False)).veredicto == "NÃO ATENDE"
    for payload in (verdict_payload("NÃO ATENDE"), verdict_payload("ATENDE", False),
                    verdict_payload("talvez"), {**verdict_payload(),"correcao":"true"}):
        with pytest.raises(ValidationError):
            Verdict.model_validate(payload)


async def test_failed_judge_control_prevents_false_success(monkeypatch, tmp_path):
    import julgamento
    monkeypatch.setenv("GEMINI_API_KEY", "not-a-real-key")
    monkeypatch.setattr(julgamento, "judge", AsyncMock(return_value=Verdict.model_validate(verdict_payload())))
    args = SimpleNamespace(cases=str(tmp_path / "cases.json"),limit=None,model="test",
                           output=str(tmp_path / "report.json"),interval=0,chat_url="unused")
    (tmp_path / "cases.json").write_text(json.dumps([{"id":"1","pergunta":"x","criterios":"y"}]))
    assert await evaluate(args) == 1
    report = json.loads((tmp_path / "report.json").read_text())
    assert report["status"] == "incomplete"
    assert report["summary"]["pass_rate"] == 0


def test_real_chroma_persistence_and_model_isolation(tmp_path):
    chromadb = pytest.importorskip("chromadb")
    cache = fake_cache()
    cache.collection = chromadb.PersistentClient(path=str(tmp_path)).get_or_create_collection(
        "cache_test", embedding_function=None, configuration={"hnsw":{"space":"cosine"}})
    assert cache.store("Explique proporção", "Resposta modelo A", "A")
    assert cache.lookup("Explique a proporção", "A")["answer"] == "Resposta modelo A"
    assert cache.lookup("Explique a proporção", "B") is None


async def test_judge_wire_schema_is_compatible_and_negative_verdict_is_preserved():
    import httpx
    from google import genai
    from google.genai import types
    from julgamento import judge

    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200,json={"candidates":[{"content":{"role":"model","parts":[
            {"text":json.dumps(verdict_payload("NÃO ATENDE",False))}]},"finishReason":"STOP"}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        async with genai.Client(api_key="not-real",http_options=types.HttpOptions(httpx_async_client=http)).aio as client:
            verdict = await judge(client,"test-model",{"pergunta":"O que é proporção?","criterios":"Correção"},"Um pássaro.",[])
    assert verdict.veredicto == "NÃO ATENDE"
    schema = requests[0]["generationConfig"]["responseSchema"]
    assert "additionalProperties" not in schema
    assert "additional_properties" not in schema
    assert schema["properties"]["veredicto"]["enum"] == ["ATENDE","NÃO ATENDE"]
