import asyncio
import logging
import os
import time
from collections import deque
from typing import Literal

from fastapi import FastAPI, HTTPException
from google import genai
from google.genai import errors, types
import httpx
from pydantic import BaseModel, ConfigDict, Field

from bridge import mcp_session, run_chat

app = FastAPI(title="Chat da Cafeteria Sensorial", version="1.0.0")
logger = logging.getLogger(__name__)

# Rate limiter simples: máximo de requisições por janela de tempo.
# Protege a cota gratuita da API Gemini contra uso excessivo.
_RATE_WINDOW = int(os.getenv("CHAT_RATE_WINDOW", "60"))
_RATE_LIMIT = int(os.getenv("CHAT_RATE_LIMIT", "2"))
_request_log: deque[float] = deque()


def _check_rate_limit() -> None:
    now = time.monotonic()
    while _request_log and _request_log[0] < now - _RATE_WINDOW:
        _request_log.popleft()
    if len(_request_log) >= _RATE_LIMIT:
        raise HTTPException(
            429,
            f"Limite de {_RATE_LIMIT} perguntas por minuto atingido. "
            "Aguarde alguns instantes para preservar a cota da API.",
        )
    _request_log.append(now)



class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    message: str = Field(min_length=1, max_length=2000)
    history: list[Message] = Field(default_factory=list, max_length=12)


@app.get("/health")
async def health():
    return {"status": "ok", "provider": "gemini", "configured": bool(os.getenv("GEMINI_API_KEY", "").strip()),
            "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash")}


@app.get("/tools")
async def tools():
    try:
        async with asyncio.timeout(12):
            async with mcp_session() as session:
                return (await session.list_tools()).model_dump(mode="json")
    except Exception as exc:
        raise HTTPException(503, "Servidor MCP indisponível. Tente novamente.") from exc


@app.post("/chat")
async def chat(payload: ChatRequest):
    _check_rate_limit()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, "Configure GEMINI_API_KEY no .env e recrie o contêiner chat para habilitar a IA.")
    try:
        async with asyncio.timeout(75):
            async with genai.Client(api_key=key, http_options=types.HttpOptions(
                timeout=25000, retry_options=types.HttpRetryOptions(
                    attempts=4, initial_delay=2, max_delay=5, http_status_codes=[429, 503]
                )
            )).aio as client:
                failure = None
                async with mcp_session() as session:
                    # Captura antes de sair dos task groups do SDK MCP para preservar
                    # o tipo do erro Gemini (em vez de envolvê-lo em ExceptionGroup).
                    try:
                        result = await run_chat(client, session, payload.message,
                                                [message.model_dump() for message in payload.history],
                                                os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
                    except Exception as exc:
                        failure = exc
                if failure is not None:
                    raise failure
                return result
    except (TimeoutError, httpx.TimeoutException) as exc:
        raise HTTPException(504, "Tempo de resposta excedido. Tente novamente.") from exc
    except errors.APIError as exc:
        message = {400: "Gemini recusou a solicitação. Confira a chave, o modelo e os parâmetros.",
                   401: "Chave Gemini inválida. Confira o .env.",
                   403: "A conta não tem permissão para este modelo.",
                   404: "Modelo indisponível. Confira GEMINI_MODEL.",
                   429: "Cota da API Gemini atingida. Tente novamente mais tarde.",
                   503: "Gemini temporariamente indisponível (503). Tente novamente em alguns instantes."}.get(exc.code, "A API Gemini não pôde concluir a consulta.")
        raise HTTPException(502, message) from exc
    except httpx.RequestError as exc:
        raise HTTPException(502, "Não foi possível conectar ao Gemini.") from exc
    except Exception as exc:
        logger.warning("Falha no chat: %s", type(exc).__name__)
        raise HTTPException(503, "Não foi possível concluir a consulta MCP/IA. Tente novamente ou simplifique a pergunta.") from exc
