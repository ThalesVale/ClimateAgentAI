# RF01 – Chat interativo via CMD com agente especialista em clima

| Campo        | Valor                                   |
|--------------|-----------------------------------------|
| ID           | RF01                                    |
| Prioridade   | Alta                                    |
| Status       | Rascunho                                |
| Versão       | 1.1                                     |
| Data         | 2026-11-07                              |
| Design       | [RF01-design.md](RF01-design.md)        |

### Histórico de versões

| Versão | Alteração |
|--------|-----------|
| 1.0    | Versão inicial (memória só em RAM, uma tool). |
| 1.1    | Configuração via `.env`, memória de sessão persistida em arquivo local e nova tool de data/hora. |

## 1. Descrição original

> Eu gostaria de um chat interativo via cmd, integrado com OpenAI e AWS Strands. Deve ser um agent super simples. Deve rodar em Python localmente na minha máquina.

## 2. Descrição refinada

O sistema deve disponibilizar um **chat interativo no terminal (CMD do Windows)**. Nele o usuário conversa em linguagem natural com um **agente de IA especialista em clima e previsão do tempo**. O agente é construído com o **AWS Strands Agents SDK (Python)** e usa um **modelo da OpenAI** como LLM. Toda a configuração fica em um **arquivo `.env`**.

O agente tem **duas ferramentas (tools)**:
- `obter_data_hora`: informa a data e a hora atuais, para interpretar "hoje", "amanhã", "sábado" etc.;
- `consultar_clima`: consulta dados reais na API pública **Open-Meteo**.

A conversa é gravada em **arquivo local** (memória de sessão). Ao reabrir o programa, o agente **retoma automaticamente a última sessão**. A aplicação roda **localmente**, sem servidor nem deploy em nuvem.

## 3. Ator

- **Usuário**: pessoa que executa o programa no próprio computador e conversa com o agente pelo terminal.

## 4. Pré-condições

1. Python 3.10 ou superior instalado e disponível no PATH.
2. Dependências instaladas via `pip install -r requirements.txt`.
3. Arquivo `.env` criado a partir do `.env.example`, com `OPENAI_API_KEY` válida.
4. Acesso à internet (OpenAI e Open-Meteo).

## 5. Fluxo principal

1. O usuário executa `python main.py` no CMD.
2. O sistema carrega o `.env` e restaura a sessão gravada (identificada por `SESSION_ID`), se ela existir.
3. O sistema exibe boas-vindas com instruções básicas e indica se a sessão foi retomada ou é nova.
4. O sistema exibe o prompt de entrada (`Você: `).
5. O usuário digita uma pergunta (ex.: "Vai chover amanhã em Curitiba?").
6. Se a pergunta tiver data relativa, o agente aciona `obter_data_hora`. Se envolver tempo em uma localidade, aciona `consultar_clima`.
7. O agente responde em português do Brasil, de forma didática, com base nos dados retornados.
8. O sistema exibe a resposta (`Agente: ...`), grava a interação no arquivo de sessão e volta ao passo 4.
9. O usuário digita `sair` (ou `exit`/`quit`) e o sistema encerra com uma mensagem de despedida.

## 6. Fluxos alternativos e de exceção

| ID   | Situação                                   | Comportamento esperado |
|------|--------------------------------------------|------------------------|
| FA01 | Pergunta conceitual sem localidade (ex.: "O que é El Niño?") | O agente responde sem acionar tools. |
| FA02 | Pergunta de continuação (ex.: "E no sábado?") | O agente usa o histórico da sessão para inferir a cidade citada antes, inclusive de execuções anteriores. |
| FA03 | Pergunta fora do domínio (ex.: "Me conta uma piada") | O agente informa educadamente que é especialista em clima e redireciona o assunto. |
| FA04 | Pergunta sobre data/hora (ex.: "Que dia é hoje?") | O agente aciona `obter_data_hora` e responde. |
| FA05 | Usuário quer começar uma conversa nova     | Troca o `SESSION_ID` no `.env` (ou apaga a pasta da sessão) e reinicia o programa. |
| FE01 | `.env` ausente ou `OPENAI_API_KEY` vazia   | O sistema explica como criar o `.env` e encerra sem stack trace. |
| FE02 | Cidade não encontrada no geocoding         | O agente informa que não localizou a cidade e pede outro nome ou mais detalhes (ex.: estado/país). |
| FE03 | Falha de rede/timeout na Open-Meteo        | O agente informa que não conseguiu obter os dados no momento. **Não inventa valores.** |
| FE04 | Erro na API da OpenAI (chave inválida, cota, rede) | O sistema exibe uma mensagem amigável e continua o loop, sem encerrar abruptamente. |
| FE05 | Entrada vazia                              | O sistema ignora e volta a pedir a entrada. |
| FE06 | `Ctrl+C`                                    | O sistema encerra de forma limpa, com mensagem de despedida. |
| FE07 | Arquivo de sessão corrompido               | O sistema informa o problema e sugere trocar o `SESSION_ID` ou apagar a pasta da sessão. |
| FE08 | `TIMEZONE` inválido no `.env`              | O sistema informa o erro de configuração e encerra sem stack trace. |

## 7. Regras de negócio

- **RN01** – O agente deve responder sempre em português do Brasil.
- **RN02** – O agente nunca deve inventar dados meteorológicos. Valores numéricos (temperatura, chuva etc.) devem vir da tool.
- **RN03** – A previsão é limitada a, no máximo, **7 dias** a partir da data atual.
- **RN04** – Unidades: temperatura em °C, chuva em mm, vento em km/h.
- **RN05** – Quando fizer sentido, o agente deve dar recomendações práticas (guarda-chuva, casaco, protetor solar, atividades ao ar livre).
- **RN06** – O histórico da conversa é **persistido em arquivo local** e retomado automaticamente na próxima execução com o mesmo `SESSION_ID`.
- **RN07** – Para datas relativas, a data de referência vem sempre da tool `obter_data_hora`, no fuso configurado (`TIMEZONE`, padrão `America/Sao_Paulo`).
- **RN08** – Para limitar custo e contexto, só as últimas `CONTEXT_WINDOW` mensagens (padrão 20) são enviadas ao modelo. O arquivo de sessão, porém, mantém o histórico completo.

## 8. Especificação técnica (resumo)

Os detalhes estão em [RF01-design.md](RF01-design.md).

| Item            | Escolha |
|-----------------|---------|
| Linguagem       | Python 3.10+ |
| Configuração    | Arquivo `.env`, carregado com `python-dotenv` |
| Framework agent | `strands-agents[openai]` (AWS Strands Agents SDK) |
| LLM             | OpenAI, via `strands.models.openai.OpenAIModel`. Modelo padrão `gpt-4o-mini` (`OPENAI_MODEL`) |
| Memória         | Session manager do Strands com armazenamento em arquivo local (`SESSION_DIR`, padrão `./sessions`) |
| Tools           | `obter_data_hora` (customizada, `zoneinfo` + `tzdata`) e `consultar_clima` (Open-Meteo) |
| HTTP            | `requests` |

## 9. Requisitos não funcionais relacionados

- **RNF01 – Simplicidade**: o código deve ser pequeno (meta: menos de 250 linhas, sem contar testes), com um único agente e duas tools.
- **RNF02 – Segurança**: a chave da OpenAI fica só no `.env`. Ela nunca pode estar no código nem aparecer em logs. `.env` e `sessions/` devem constar no `.gitignore`.
- **RNF03 – Portabilidade**: deve funcionar no CMD e no PowerShell do Windows, com acentuação exibida corretamente (UTF-8).
- **RNF04 – Desempenho**: a resposta típica deve chegar em até 10 s, dependendo da latência da OpenAI.
- **RNF05 – Execução local**: nenhuma infraestrutura AWS é necessária. O Strands é usado só como biblioteca.

## 10. Critérios de aceite (Gherkin)

```gherkin
Funcionalidade: Chat de clima no terminal

  Cenário: Iniciar o chat pela primeira vez
    Dado que o arquivo .env contém uma OPENAI_API_KEY válida
    E que não existe sessão gravada para o SESSION_ID configurado
    Quando executo "python main.py"
    Então vejo uma mensagem de boas-vindas indicando uma sessão nova
    E o prompt "Você:" aguardando minha pergunta

  Cenário: Consultar o clima atual de uma cidade
    Dado que o chat está em execução
    Quando pergunto "Como está o tempo agora em São Paulo?"
    Então o agente aciona a tool consultar_clima com cidade "São Paulo"
    E responde em português com temperatura em °C e a condição do céu

  Cenário: Pergunta com data relativa
    Dado que o chat está em execução
    Quando pergunto "Vai chover amanhã em Curitiba?"
    Então o agente aciona a tool obter_data_hora
    E aciona a tool consultar_clima para Curitiba
    E responde sobre a data correspondente a amanhã

  Cenário: Perguntar a data e a hora
    Quando pergunto "Que dia e que horas são?"
    Então o agente aciona a tool obter_data_hora
    E responde com a data, a hora e o dia da semana no fuso configurado

  Cenário: Previsão para os próximos dias
    Quando pergunto "Vai chover nos próximos 3 dias em Curitiba?"
    Então o agente consulta a previsão de 3 dias
    E informa a probabilidade de chuva de cada dia

  Cenário: Pergunta de continuação na mesma execução
    Dado que perguntei anteriormente sobre "Recife"
    Quando pergunto "E amanhã?"
    Então o agente responde sobre a previsão de amanhã em Recife

  Cenário: Memória persistida entre execuções
    Dado que perguntei sobre "Recife" e encerrei o chat com "sair"
    Quando executo "python main.py" novamente com o mesmo SESSION_ID
    Então vejo uma mensagem indicando que a sessão foi retomada
    E ao perguntar "E amanhã?" o agente responde sobre Recife

  Cenário: Iniciar uma sessão nova
    Dado que existe uma sessão gravada
    Quando altero o SESSION_ID no .env e executo "python main.py"
    Então vejo uma mensagem indicando uma sessão nova
    E o agente não conhece as conversas anteriores

  Cenário: Pergunta conceitual
    Quando pergunto "O que é uma frente fria?"
    Então o agente responde sem acionar tools

  Cenário: Cidade inexistente
    Quando pergunto "Como está o tempo em Xyzabcland?"
    Então o agente informa que não encontrou a cidade
    E não apresenta dados inventados

  Cenário: Chave da OpenAI ausente
    Dado que o .env não existe ou OPENAI_API_KEY está vazia
    Quando executo "python main.py"
    Então vejo uma mensagem explicando como configurar o .env
    E o programa encerra sem exibir stack trace

  Cenário: Encerrar o chat
    Quando digito "sair"
    Então vejo uma mensagem de despedida
    E o programa é encerrado
```

## 11. Fora de escopo (RF01)

- Interface gráfica ou web.
- Comandos de chat para gerenciar sessões (listar, trocar, apagar). A troca é feita pelo `.env`.
- Memória de longo prazo ou semântica (resumos, banco vetorial).
- Múltiplos agentes, multi-agent ou orquestração.
- Deploy na AWS (Lambda, Bedrock AgentCore etc.), uso de modelos do Bedrock ou sessões no S3.
- Streaming token a token (pode virar um RF futuro).
- Alertas meteorológicos, mapas ou dados históricos.

## 12. Dependências e premissas

- Conta OpenAI com créditos disponíveis (o uso da API é pago).
- A Open-Meteo é gratuita para uso não comercial e tem limite de requisições diário.
- No Windows, o pacote `tzdata` é necessário para o `zoneinfo` reconhecer fusos como `America/Sao_Paulo`.
- **Ambiente atual**: o Python ainda **não está instalado** nesta máquina (o comando `python` aponta para o atalho da Microsoft Store). É preciso instalar o Python 3.10+ (python.org ou `winget install Python.Python.3.12`) antes da implementação.
