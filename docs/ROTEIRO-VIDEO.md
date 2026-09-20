# Roteiro de demonstração — até 7 minutos

Prepare a chave Gemini no `.env`, confirme `docker compose ps` e deixe os dados originais para que os resultados abaixo coincidam. Não mostre a chave na gravação. Abra o cliente e os três Swagger em abas separadas.

| Tempo | O que mostrar e explicar |
|---|---|
| 0:00–0:40 | Tema: cafeteria de cafés especiais. Grãos descrevem a origem, métodos descrevem preparo e degustações registram experiências com grão e método. |
| 0:40–1:30 | Estrutura de diretórios e diagrama do README. Um Dockerfile e contêiner para cada API. PostgreSQL com três bancos e usuários; degustações só guardam referências. |
| 1:30–2:10 | `docker compose up -d --build` e `docker compose ps`. Sete contêineres e portas. Mostrar o cliente em `localhost:8080`. Deixar as imagens prontas antes evita gastar o vídeo baixando dependências. |
| 2:10–3:10 | Três painéis, filtros e detalhes. Abrir Swagger e demonstrar um POST usando exemplo. Explicar `201`, `404` e `422`; mostrar dados retornados por uma consulta. |
| 3:10–4:20 | `docker compose stop graos-service`. Sem recarregar, observar indisponibilidade de grãos e continuidade de métodos/degustações. `docker compose start graos-service`; mostrar recuperação automática. |
| 4:20–5:10 | Abrir `mcp/server.py` e os módulos de ferramentas. Mostrar `curl localhost:8005/tools` ou `scripts/check_mcp.py`. Explicar duas rotas reais por domínio, descobertas por MCP. |
| 5:10–6:35 | No chat: “Mostre os detalhes do grão 1, método 1 e degustação 1”; depois “Qual grão tem a melhor média?”. Mostrar as ferramentas usadas e confrontar a resposta com dados reais: grão 1, média 9,3 e duas degustações no seed original. |
| 6:35–6:55 | Explicar timeout/retry, persistência e variável de ambiente para a chave. Mostrar os testes concluídos e encerrar. |

O modelo pode escolher ferramentas diferentes dependendo da pergunta. Faça uma consulta de listagem e outra por ID para evidenciar os dois endpoints de cada domínio. Caso tenha adicionado degustações, a média poderá mudar corretamente. Ensaiar o fluxo antes ajuda a respeitar o limite.
