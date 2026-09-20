"""Inspeciona e chama as seis ferramentas reais, sem precisar de chave Gemini."""
import asyncio
import os

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def main():
    async with streamablehttp_client(os.getenv("MCP_TEST_URL", "http://127.0.0.1:8004/mcp")) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for tool in (await session.list_tools()).tools:
                args = {"id":1} if tool.name.endswith("_obter") else {}
                result = await session.call_tool(tool.name, args)
                print(f"\n{tool.name}: {'ERRO' if result.isError else 'OK'}")
                for content in result.content:
                    if content.type == "text":
                        print(content.text)


if __name__ == "__main__":
    asyncio.run(main())
