# Registro de validação

Validação realizada com Docker Compose, PostgreSQL e os três serviços em execução.

| Verificação | Resultado |
|---|---|
| Build de Dockerfiles e inicialização pelo Compose | Sete contêineres iniciados |
| Seed em PostgreSQL | 3 grãos, 5 métodos, 4 degustações |
| Testes pytest | 19 aprovados: 18 na suíte e 1 teste adicional de serialização do SDK Gemini |
| REST real | Listagens, detalhes, POST 201 com Location, filtros, 404 e validação 422 |
| MCP real | Descoberta e execução das seis ferramentas, chamadas por ID e erros |
| Ponte chat → MCP → REST | Validada com MCP/REST reais e modelo simulado |
| SDK oficial Gemini | Serialização HTTP validada com transporte simulado, incluindo respostas de ferramentas e preservação de thought signatures |
| Chat sem chave | Retorna 503 com instrução de configuração; demais painéis continuam disponíveis |
| Queda e retorno de grãos | Painel indisponível, outros dois ativos, recuperação sem recarregar |
| Queda e retorno de métodos | Painel indisponível, outros dois ativos, recuperação sem recarregar |
| Queda e retorno de degustações | Painel indisponível, outros dois ativos, recuperação sem recarregar |
| MCP durante cada queda | Falha apenas no domínio parado; demais ferramentas funcionam |
| Navegador desktop e móvel | Filtros, detalhes e mensagem de chave ausente aprovados; sem overflow horizontal a 390 px e sem erros JavaScript |

Comandos reproduzíveis estão no README. Os testes de integração usam HTTP e MCP reais, com registros de teste removidos por ID no encerramento. O teste de navegador usa Chromium/Playwright e restaura cada API em um bloco `finally`.

**Validação com chave real:** a chave foi configurada e carregada no contêiner. O alias `gemini-flash-latest` retornava respostas vazias (somente "thinking" sem texto final). Após trocar o modelo padrão para `gemini-2.5-flash`, a conversa real foi validada com sucesso: o Gemini chamou as ferramentas MCP (`graos_listar`, `degustacoes_listar`), retornou dados corretos em português e calculou médias de notas por grão. Erros 503 intermitentes (alta demanda) e 429 (cota gratuita) são tratados com retries automáticos (3 tentativas com backoff de 1–2 s). Os testes de orquestração usam modelo simulado, mantendo reais o transporte MCP e as consultas REST.

Durante a validação visual, o script teve seu endereço de healthcheck corrigido e a decoração da xícara foi ajustada para não exceder a largura móvel. As capturas são geradas em `artifacts/desktop.png`, `artifacts/mobile.png` e `artifacts/service-offline.png`.
