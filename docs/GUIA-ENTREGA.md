# Cafeteria Sensorial: Sistema Especialista para Web

Tema aprovado pelo professor, conforme confirmação do aluno nesta conversa. Entrega prevista no enunciado: 20/11/2026. Trabalho individual de Marcílio Pereira Aguiar.

## Executar

Preserve seu `.env` e o volume de dados. Novas configurações opcionais estão em `.env.example`; os padrões já permitem executar o cache. Não execute `docker compose down -v`, pois apaga os volumes.

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8005/health
```

Abra http://localhost:8080. O primeiro carregamento do modelo de embeddings pode demorar e precisa de acesso ao Hugging Face. A interface mostra o estado do cache. Se ele falhar, o chat continua com Gemini, mas isso NÃO comprova o requisito de cache: resolva o carregamento antes da demonstração. Pesos e vetores ficam no volume `specialist_data`; bancos antigos permanecem em `postgres_data`.

## O especialista

`chat/conhecimento/cafe.json` contém orientações pedagógicas e referências verificáveis; `chat/knowledge.py` estabelece escopo, perguntas complementares, distinção entre hipótese e certeza e uso de ferramentas para dados atuais. Os dados iniciais dos serviços são fictícios e não constituem validação de qualidade do café.

As seis ferramentas MCP originais consultam catálogo, métodos e degustações. O modelo pode responder conceitos sem chamar ferramentas, mas recebe instrução explícita de consultá-las quando a pergunta depende dos registros. Essa escolha deve ser verificada nos casos do julgador.

As degustações aceitam, opcionalmente, `parametros.cafe_g`, `parametros.agua_g` e `parametros.bebida_g`. Os registros antigos continuam válidos com esses campos nulos. Ausência de massa não autoriza presumir a proporção usada. Para espresso, massa da bebida e água de preparo têm significados distintos.

## Demonstrar o cache

1. Aguarde `cache.state=ready` no healthcheck.
2. Em **Nova conversa**, pergunte “O que significa proporção entre café e água?”. A primeira resposta deve vir do especialista.
3. Use **Nova conversa** e repita a pergunta ou uma paráfrase. A interface identifica uma resposta recuperada do cache quando a distância for aceita.
4. Pergunte por um grão cadastrado ou um ranking: a resposta deve consultar MCP e não deve ser armazenada nesse cache.

O cache usa SentenceTransformers e ChromaDB com distância de cosseno. O limiar inicial é 0,20, seguindo o exemplo da aula; não representa uma probabilidade de acerto e precisa ser calibrado com paráfrases e perguntas diferentes. Perguntas com histórico, números, negações e referências a registros/contexto são excluídas conservadoramente. Somente respostas sem execução de ferramentas podem ser gravadas. Há isolamento por modelo e versão da base, TTL padrão de 24 horas e retorno ao LLM quando o cache falha. Isso reduz riscos, sem garantir equivalência semântica perfeita.

O cliente mantém até 12 mensagens; **Nova conversa** limpa somente o contexto da conversa, não apaga o cache persistente. Acertos do cache não gastam a cota de geração. O limite de perguntas aplica-se às solicitações novas ao modelo.

## Avaliação LLM-as-a-Judge

O julgador usa a API do chat completo, com `use_cache=false`, e recebe resposta e evidências das ferramentas. A base de 12 casos inclui proporção, diagnóstico incompleto, catálogo, médias, métodos, dados ausentes, ID inexistente, escopo, tentativa de invenção, cálculo e distinção de espresso. Dois controles com respostas erradas precisam ser rejeitados antes de avaliar o especialista.

```bash
# Executa todos os casos; pode levar vários minutos e consumir cota da API.
docker compose exec -T chat python julgamento.py

# Ensaio curto; não substitui a avaliação completa.
docker compose exec -T chat python julgamento.py --limit 3 --output /app/data/avaliacao/ensaio.json

# Extrair relatório completo para a entrega.
mkdir -p artifacts/avaliacao
docker compose cp chat:/app/data/avaliacao/resultado.json artifacts/avaliacao/resultado.json
```

`JUDGE_MODEL` é configurável independentemente de `GEMINI_MODEL`. Preferir modelos distintos quando a conta permitir e registrar exatamente os modelos usados. O intervalo padrão de 31 segundos respeita o limite local de duas requisições por minuto. O script também tenta novamente em HTTP 429; cotas externas podem impedir a conclusão.

O JSON registra critérios, justificativas, ferramentas, evidências, tempos e erros. Um veredicto só é válido se for exatamente `ATENDE` ou `NÃO ATENDE` e coerente com os cinco critérios. Saídas inválidas, erros de API e controles aprovados indevidamente não são contados como sucesso. O denominador inclui todos os casos planejados. Código de saída: 0 quando todos passam, 1 para reprovação/incompletude, 2 para erro de configuração inicial.

O juiz automático é uma avaliação limitada e pode errar. Revise os casos e justificativas manualmente; não apresente uma execução simulada ou parcial como resultado completo. Não altere os critérios apenas para melhorar a taxa de aprovação.

## Testes e evidências

```bash
.venv/bin/python -m pytest -q
RUN_INTEGRATION=1 .venv/bin/python -m pytest -q
.venv/bin/python scripts/check_browser.py --resilience
```

Os testes unitários usam modelos simulados e não provam qualidade das respostas reais. O teste de persistência Chroma é pulado quando a biblioteca não está instalada; pode ser executado no contêiner do chat ou em ambiente com as dependências. O documento `VALIDACAO-ESPECIALISTA.md` deve distinguir execução real, simulação e pendências.

## Capítulo

`docs/capitulo_cafeteria/cafeteria.tex` é o capítulo integrável ao livro. `main.tex` permite compilação isolada com a geometria do modelo. `referencias.bib` contém as referências do capítulo. Ao integrar ao livro, mescle essas referências ao arquivo bibliográfico compartilhado e ajuste o caminho do `input`, preservando as seções do exemplo.

O capítulo inclui os links públicos e foi compilado com Biber em quatro páginas, incluindo as referências.

## Vídeo, Zenodo e entrega

Grave um vídeo de no máximo oito minutos: tema e problema (0:00–0:45); inicialização e arquitetura (0:45–1:30); consulta aos registros por MCP (1:30–2:30); orientação com dados ausentes e ajuste justificado (2:30–4:00); primeira resposta e recuperação por cache (4:00–5:00); execução do julgador e leitura de resultados (5:00–7:00); limites e reprodutibilidade (7:00–8:00).

Execute a avaliação antes de gravar; no vídeo mostre seu acionamento e o relatório, identificando a execução correspondente. Publique no Zenodo o código-fonte e o vídeo, conforme o enunciado e o exemplo. Revise os arquivos antes de publicar: exclua `.env`, chaves, ambientes virtuais, bancos/volumes e logs privados. Não declare links como publicados enquanto não existirem.

Depois da publicação, adicione os links reais à seção Reproducibilidade e Reuso, gere e confira o PDF final, e envie ao professor a pasta do capítulo com `.tex`, bibliografia e quaisquer imagens usadas. A gravação e publicação dependem de conclusão pelo aluno; não são feitas automaticamente pelo projeto.

## Verificações adicionais e configuração local

Neste ambiente, as APIs usam as portas externas 8101, 8102 e 8103. Cliente, MCP e chat mantêm 8080, 8004 e 8005. Os verificadores leem as portas do `.env`.

```bash
docker compose exec -T chat python check_cache.py
.venv/bin/python scripts/check_specialist.py
.venv/bin/python scripts/package_submission.py
```

Para uma demonstração curta no vídeo, use `docker compose exec -T chat python julgamento.py --limit 1 --output /app/data/avaliacao/demonstracao.json` e apresente separadamente o relatório completo, identificando quais resultados pertencem a cada execução. A demonstração curta não substitui a avaliação completa. Os resultados desta execução estão em `docs/VALIDACAO-ESPECIALISTA.md`.
