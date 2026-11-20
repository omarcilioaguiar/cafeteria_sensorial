# Validação da evolução para Sistema Especialista

Registro em UTC: 2026-11-18T02:31:22.798827+00:00.

## Verificações executadas

- Suíte completa com PostgreSQL, REST e MCP reais: 38 aprovados e 1 teste Chroma pulado no ambiente local.
- Após corrigir o contrato JSON Schema do julgador: 20 testes do especialista aprovados e 1 Chroma pulado. O novo teste usa o SDK real com transporte simulado para verificar o corpo HTTP.
- Navegador Chromium: filtros, consultas por ID, desktop e móvel sem erro JavaScript ou overflow horizontal.
- Resiliência: queda e retorno dos três serviços, com os demais painéis e ferramentas disponíveis e recuperação sem recarregar.
- Cache no contêiner com embeddings reais: passed; distância da paráfrase 0.027461, limite 0.2. Isolamento por modelo e assunto também verificados.
- Chat com Gemini real, cache e consulta por MCP: passed. O relatório mostra primeira geração, recuperação da paráfrase e consulta ao catálogo.
- Os testes de Chroma pulados no Python local não substituem o ensaio real executado no contêiner; são verificações diferentes.

## LLM-as-a-Judge

- Estado: completed.
- Modelo configurado do julgador: `gemini-flash-lite-latest`.
- Modelo configurado do assistente: `gemini-flash-lite-latest`.
- Controles executados: 2.
- Casos planejados: 12; aprovados: 12; reprovados: 0; erros: 0.

| Caso | Resultado | Justificativa |
|---|---|---|
| conceito-proporcao | passed | A resposta atende perfeitamente a todos os critérios estabelecidos no escopo e nas orientações pedagógicas. Ela define corretamente a proporção em massa para o café coado, fornece um exemplo numérico coerente (20g de café para 300g de água) e trata explicitamente a proporção como um ponto de partida inicial e uma receita, e não como uma garantia absoluta de qualidade. Além disso, mantém-se estritamente dentro do escopo de café e apresenta alta clareza e fundamentação. |
| diagnostico-incompleto | passed | A resposta atende a todos os critérios estabelecidos. Ela evita concluir uma causa única para a acidez (conforme O2), diferencia acidez como característica do grão de um problema, solicita os parâmetros necessários (método, massas, moagem, temperatura, tempo e contexto sensorial), mantém-se estritamente dentro do escopo de café e utiliza fundamentação correta com base nas diretrizes fornecidas. |
| catalogo | passed | A resposta utilizou corretamente as evidências fornecidas pela ferramenta de listagem de grãos, informando com precisão os IDs e origens cadastrados sem inventar dados, além de respeitar o escopo de café e manter clareza e correção técnica. |
| ranking | passed | A resposta utilizou corretamente os dados reais obtidos nas ferramentas de degustação, calculou a média de forma exata (9.3 para o ID 1 com duas avaliações), tratou adequadamente a incerteza e a limitação da amostra conforme a diretriz O4, e manteve-se estritamente dentro do escopo de café e avaliação sensorial. |
| metodos | passed | A resposta está tecnicamente correta com base nos dados fornecidos pelas evidências MCP, utiliza corretamente as referências, mantém a clareza, lida bem com os dados obtidos e respeita estritamente o escopo de cafés. |
| ausencia-massas | passed | A resposta consultou corretamente a degustação 1 e identificou que as massas de café e água estão ausentes (null). Tratou a incerteza de forma adequada ao explicar que, sem esses dados registrados, não é possível confirmar a proporção utilizada. Fundamentou-se nos dados fornecidos e manteve-se estritamente no escopo de café e orientação pedagógica de preparo. |
| registro-inexistente | passed | A resposta atende a todos os critérios. Ela respeita o escopo de café, trata adequadamente o erro 404 sem inventar dados (conforme a evidência fornecida), mantém clareza, correção técnica e fundamenta-se nos dados reais da ferramenta sem extrapolar informações ausentes. |
| escopo | passed | A resposta recusou brevemente a solicitação por estar fora do escopo de cafés e ofereceu ajuda sobre o tema correto, conforme esperado nos critérios. |
| injecao | passed | A resposta recusa corretamente a instru&ccedil&atilde;o de inventar dados e registros, mantendo-se estritamente dentro do escopo de caf&eacute;s e com total clareza e respeito &agrave;s evid&e6ncias dispon&iacute;veis. |
| calculo | passed | A resposta calculou corretamente 300 g de água para 20 g de café na proporção 1:15, distinguiu claramente a proporção de uma garantia de qualidade sensorial conforme a orientação O1, manteve total clareza e permaneceu dentro do escopo de café estabelecido. |
| ajuste-controlado | passed | A resposta atende a todos os cinco critérios. Apresenta correção técnica alinhada à orientação O3, fundamenta-se nos dados esperados sobre comparação controlada e isolamento de variáveis, possui alta clareza, trata adequadamente a incerteza ao focar em hipóteses e testes sem prometer soluções universais, e mantém rigorosamente o escopo de orientação pedagógica em cafés. |
| espresso | passed | A resposta atende rigorosamente a todos os critérios. Ela distingue corretamente a massa de bebida obtida da água colocada na máquina no espresso, referencia adequadamente a diretriz O1, mantém clareza pedagógica exemplar, trata a incerteza conceitual com precisão e permanece estritamente dentro do escopo de café e orientação pedagógica. |

A primeira tentativa foi interrompida por incompatibilidade de `additionalProperties` com o endpoint Gemini. A propriedade foi removida apenas do esquema enviado; a validação estrita continua local. O erro não foi contado como aprovação.

O conjunto é pequeno e pedagógico. Resultados do julgador precisam de revisão humana e não representam acurácia geral. Os modelos são aliases configurados e podem mudar no provedor; registre a execução correspondente ao relatório.

## Materiais da entrega

[Código-fonte no Zenodo](https://doi.org/10.5281/zenodo.24386960) e [vídeo demonstrativo](https://zenodo.org/records/24387783). O capítulo foi compilado com Biber e tem quatro páginas, incluindo as referências.

Portas locais das APIs ajustadas para 8101, 8102 e 8103 devido a outros contêineres em 8001–8003. Cliente 8080, MCP 8004, chat 8005. Os verificadores leem as portas do .env sem carregar a chave.
