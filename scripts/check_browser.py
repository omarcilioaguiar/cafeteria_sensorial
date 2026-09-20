"""Verifica navegador, filtros e queda/retorno real dos três serviços (opcional)."""
import argparse
import asyncio
import os
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


async def compose(*args):
    process = await asyncio.create_subprocess_exec("docker", "compose", *args, cwd=ROOT)
    if await process.wait():
        raise RuntimeError(f"Docker Compose falhou: {args}")


async def verify_mcp_failure(domain, down):
    async with streamablehttp_client(os.getenv("MCP_TEST_URL", "http://127.0.0.1:8004/mcp")) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for name in ["graos", "metodos", "degustacoes"]:
                result = await session.call_tool(f"{name}_listar", {})
                assert result.isError == (name == domain and down), (name, result)


async def main(resilience):
    (ROOT / "artifacts").mkdir(exist_ok=True)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width":1440, "height":1000}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto(os.getenv("CLIENT_TEST_URL", "http://127.0.0.1:8080"))
        await expect(page.locator('.status.online')).to_have_count(3, timeout=20000)
        await page.locator('#filtro-graos').select_option('honey')
        await expect(page.locator('#panel-graos .card')).to_have_count(1, timeout=12000)
        await expect(page.locator('#panel-graos h4')).to_have_text('Mantiqueira Doce')
        await page.locator('#panel-graos .detail-button').click()
        await expect(page.locator('#detail-content')).to_contain_text('Bourbon amarelo')
        await page.locator('#close-detail').click()
        await page.locator('#filtro-graos').select_option('')
        await expect(page.locator('#panel-graos .card')).to_have_count(3, timeout=12000)
        await page.screenshot(path=str(ROOT / 'artifacts/desktop.png'), full_page=True)
        print('OK: três painéis, filtros e consulta por ID no navegador.', flush=True)
        if resilience:
            for domain, service in [('graos','graos-service'),('metodos','metodo-service'),('degustacoes','degustacao-service')]:
                count = await page.locator(f'#panel-{domain} .card').count()
                try:
                    await compose('stop', service)
                    await expect(page.locator(f'#panel-{domain} .status')).to_have_class('status offline', timeout=20000)
                    await expect(page.locator('.status.online')).to_have_count(2)
                    await expect(page.locator(f'#panel-{domain} .card')).to_have_count(count)
                    await expect(page.locator(f'#panel-{domain} .freshness')).to_contain_text('Dados anteriores')
                    await verify_mcp_failure(domain, True)
                    if domain == 'graos':
                        await page.screenshot(path=str(ROOT / 'artifacts/service-offline.png'), full_page=True)
                    print(f'OK: {service} parado; outros painéis e ferramentas MCP disponíveis.', flush=True)
                finally:
                    await compose('start', service)
                await expect(page.locator('.status.online')).to_have_count(3, timeout=25000)
                await expect(page.locator(f'#panel-{domain} .card')).to_have_count(count)
                await verify_mcp_failure(domain, False)
                print(f'OK: {service} recuperado automaticamente, sem recarregar a página.', flush=True)
        # Sem chave, a UI deve explicar a configuração e continuar consultando APIs.
        response = await page.request.get(os.getenv("CLIENT_TEST_URL", "http://127.0.0.1:8080") + '/api/chat/health')
        if not (await response.json())['configured']:
            await page.locator('#question').fill('Quais grãos estão disponíveis?')
            await page.locator('#chat-form button').click()
            await expect(page.locator('.error-message')).to_contain_text('GEMINI_API_KEY')
            await expect(page.locator('.status.online')).to_have_count(3)
        await page.set_viewport_size({'width':390,'height':844})
        await page.screenshot(path=str(ROOT / 'artifacts/mobile.png'), full_page=True)
        assert await page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Overflow horizontal no celular'
        assert not errors, errors
        await browser.close()
        print('OK: layout móvel, tratamento de chat sem chave e nenhum erro JavaScript.', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resilience', action='store_true', help='Para e reinicia cada API criada por este Compose.')
    asyncio.run(main(parser.parse_args().resilience))
