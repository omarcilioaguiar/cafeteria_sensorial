"""Verifica cache no chat e consulta MCP com Gemini real. Consome cota da API."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path

import httpx
from local_config import configure_ports

ROOT = Path(__file__).resolve().parents[1]


async def ask(client, url, question):
    for attempt in range(3):
        response = await client.post(url, json={"message":question,"history":[]})
        if response.status_code == 429 and attempt < 2:
            await asyncio.sleep(35)
            continue
        response.raise_for_status()
        return response.json()


async def check(base):
    report = {"created_at":datetime.now(timezone.utc).isoformat(),"status":"incomplete","responses":[]}
    try:
        async with httpx.AsyncClient(timeout=100,trust_env=False) as client:
            health = (await client.get(base + "/health")).json()
            if not health["configured"]:
                raise RuntimeError("GEMINI_API_KEY ausente no contêiner.")
            if health["cache"]["state"] != "ready":
                raise RuntimeError("O cache precisa estar pronto antes do ensaio.")
            report["health"] = health
            first = await ask(client,base + "/chat","O que significa proporção entre café e água?")
            report["responses"].append(first)
            second = await ask(client,base + "/chat","Explique a proporção entre café e água.")
            report["responses"].append(second)
            assert second["cache"]["hit"], "A paráfrase não foi atendida pelo cache. Investigue antes de demonstrar."
            assert first["answer"] == second["answer"]
            result = await ask(client,base + "/chat","Quais grãos estão cadastrados? Informe IDs e origens.")
            report["responses"].append(result)
            assert "graos_listar" in result["tools_used"]
            assert not result["cache"]["hit"]
            assert result["evidence"]
            report["status"] = "passed"
    except Exception as exc:
        report["error_type"] = type(exc).__name__
        # As únicas respostas HTTP vêm do próprio chat, que sanitiza mensagens de erro.
        if isinstance(exc,httpx.HTTPStatusError):
            report["http_status"] = exc.response.status_code
            try:
                report["detail"] = exc.response.json().get("detail")
            except ValueError:
                pass
        elif isinstance(exc,(AssertionError,RuntimeError)):
            report["detail"] = str(exc)
    target = ROOT / "artifacts" / "avaliacao" / "chat-smoke.json"
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({key:value for key,value in report.items() if key not in ("responses","health")},ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    configure_ports()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url",default=f'http://127.0.0.1:{os.environ["CHAT_PORT"]}')
    raise SystemExit(asyncio.run(check(parser.parse_args().base_url)))
