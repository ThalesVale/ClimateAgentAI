# RF01 – Design: Chat interativo via CMD com agente especialista em clima

| Campo         | Valor                                                  |
|---------------|--------------------------------------------------------|
| Requisito     | [RF01 – Chat interativo via CMD](RF01-chat-cli.md) |
| Status        | Rascunho                                               |
| Versão        | 1.1 (ajustes do spike T03: `save_latest_on`, `executar_chat`, validação do `SESSION_ID`, modelo simulado) |
| Data          | 2026-11-07                                             |

## 1. Objetivo

Descrever **como** o RF01 será construído: arquitetura, componentes, configuração, tools, persistência da sessão e tratamento de erros. O resultado deve ser um agente **super simples**, rodando **localmente** em Python.

## 2. Decisões de design

| ID   | Decisão | Justificativa |
|------|---------|---------------|
| DD01 | Linguagem **Python 3.10+** | Exigida pelo requisito e pelo Strands Agents SDK. |
| DD02 | Configuração via arquivo **`.env`**, carregado com `python-dotenv` | Mantém chave e parâmetros fora do código. O `.env` não é versionado. |
| DD03 | Framework de agente **AWS Strands Agents SDK** (`strands-agents`) | Exigido pelo requisito. É usado só como biblioteca local, sem nenhuma infraestrutura AWS. |
| DD04 | Modelo **OpenAI** via `strands.models.openai.OpenAIModel` (extra `strands-agents[openai]`) | Exigido pelo requisito. Modelo padrão `gpt-4o-mini`, configurável no `.env`. |
| DD05 | **Memória de sessão em arquivo local** com o session manager do Strands (`SnapshotSessionManager` + `LocalFileStorage`) | Recurso nativo do SDK: persiste mensagens e estado automaticamente a cada interação, sem código de serialização próprio. |
| DD06 | **Sempre retomar a mesma sessão**: `SESSION_ID` fixo, definido no `.env` | É o comportamento mais simples. Ao abrir o chat, a conversa anterior continua de onde parou. |
| DD07 | Tool **customizada `obter_data_hora`** (`@tool`) | O LLM não sabe a data atual. A tool resolve "hoje", "amanhã", "sábado" etc. O fuso é configurável no `.env`. |
| DD08 | Tool **customizada `consultar_clima`** (`@tool`) usando a Open-Meteo | Dados reais, gratuitos e sem chave. |
| DD09 | Janela deslizante de contexto (`SlidingWindowConversationManager`) | Como a sessão é persistente, o histórico cresce sem limite. A janela evita estourar o contexto e reduz o custo de tokens. |
| DD10 | Interação **síncrona e sem streaming**, com a saída padrão do Strands desligada (`callback_handler=None`) | Simplicidade: o `main.py` imprime a resposta final formatada. |

## 3. Arquitetura

### 3.1 Visão geral

```
┌──────────────────────────────── Máquina local ────────────────────────────────┐
│                                                                                │
│  ┌──────────┐   input/print   ┌──────────────┐                                 │
│  │ Usuário  │ ◄─────────────► │   main.py    │  (loop do chat no CMD)          │
│  └──────────┘                 └──────┬───────┘                                 │
│                                      │ agent(pergunta)                         │
│                                      ▼                                         │
│  ┌──────────┐  lê config   ┌───────────────────────────┐                       │
│  │   .env   │ ───────────► │  strands.Agent (agente.py)│                       │
│  └──────────┘              │  • OpenAIModel            │                       │
│                            │  • system_prompt          │                       │
│                            │  • tools                  │                       │
│                            │  • session_manager        │                       │
│                            │  • conversation_manager   │                       │
│                            └──┬──────────┬──────────┬──┘                       │
│                               │          │          │                          │
│              ┌────────────────┘          │          └──────────────┐           │
│              ▼                           ▼                         ▼           │
│   ┌────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐ │
│   │ tools/data_hora.py │   │  tools/clima.py      │   │ ./sessions/ (JSON)   │ │
│   │ obter_data_hora    │   │  consultar_clima     │   │ memória da sessão    │ │
│   └────────────────────┘   └──────────┬───────────┘   └──────────────────────┘ │
│                                       │                                        │
└───────────────────────────────────────┼────────────────────────────────────────┘
                                        │ HTTPS
              ┌─────────────────────────┼──────────────────────┐
              ▼                         ▼                      ▼
     ┌─────────────────┐    ┌───────────────────┐   ┌───────────────────┐
     │   OpenAI API    │    │ Open-Meteo        │   │ Open-Meteo        │
     │ (LLM)           │    │ Geocoding API     │   │ Forecast API      │
     └─────────────────┘    └───────────────────┘   └───────────────────┘
```

### 3.2 Estrutura de arquivos

```
projeto/
├── requisitos/
│   ├── RF01-chat-cli.md
│   └── RF01-design.md
├── main.py              # ponto de entrada: valida config, cria o agente, roda o loop
├── config.py            # carrega e valida o .env, expõe um objeto Config
├── agente.py            # fábrica do Agent (modelo, prompt, tools, sessão)
├── tools/
│   ├── __init__.py
│   ├── data_hora.py     # @tool obter_data_hora
│   └── clima.py         # @tool consultar_clima (+ tabela WMO -> pt-BR)
├── sessions/            # criada automaticamente; NÃO versionar
├── .env                 # NÃO versionar
├── .env.example         # modelo do .env (versionado)
├── .gitignore           # .env, sessions/, __pycache__/, .venv/
├── requirements.txt
└── README.md
```

## 4. Componentes

### 4.1 `config.py` – Configuração

Responsabilidades:
1. Chamar `load_dotenv()` para carregar o `.env` da raiz do projeto.
2. Ler as variáveis, aplicando os valores padrão da tabela abaixo.
3. Validar: se `OPENAI_API_KEY` estiver ausente ou vazia, lançar `ConfigError` com uma mensagem amigável.
4. Expor um `@dataclass(frozen=True) Config`.

#### Variáveis do `.env`

| Variável          | Obrigatória | Padrão               | Descrição |
|-------------------|-------------|----------------------|-----------|
| `OPENAI_API_KEY`  | Sim         | –                    | Chave da API da OpenAI. |
| `OPENAI_MODEL`    | Não         | `gpt-4o-mini`        | ID do modelo OpenAI. |
| `OPENAI_TEMPERATURE` | Não      | `0.3`                | Criatividade das respostas (0 a 2). |
| `SESSION_ID`      | Não         | `sessao-padrao`      | Identificador da sessão persistida. Trocar o valor inicia uma conversa nova. Não pode conter `/` nem `\`. |
| `SESSION_DIR`     | Não         | `./sessions`         | Pasta onde a sessão é gravada. |
| `CONTEXT_WINDOW`  | Não         | `20`                 | Número máximo de mensagens enviadas ao modelo (janela deslizante). |
| `TIMEZONE`        | Não         | `America/Sao_Paulo`  | Fuso IANA usado pela tool de data/hora. |
| `HTTP_TIMEOUT`    | Não         | `10`                 | Timeout (s) das chamadas à Open-Meteo. |

#### `.env.example`

```dotenv
OPENAI_API_KEY=coloque-sua-chave-aqui
OPENAI_MODEL=gpt-4o-mini
OPENAI_TEMPERATURE=0.3
SESSION_ID=sessao-padrao
SESSION_DIR=./sessions
CONTEXT_WINDOW=20
TIMEZONE=America/Sao_Paulo
HTTP_TIMEOUT=10
```

### 4.2 `agente.py` – Fábrica do agente

Função pública: `criar_agente(config: Config) -> Agent`.

```python
model = OpenAIModel(
    client_args={"api_key": config.openai_api_key},
    model_id=config.openai_model,
    params={"temperature": config.openai_temperature},
)

session_manager = SnapshotSessionManager(
    session_id=config.session_id,
    storage=LocalFileStorage(config.session_dir),
    save_latest_on="message",
)

agent = Agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[obter_data_hora, consultar_clima],
    session_manager=session_manager,
    conversation_manager=SlidingWindowConversationManager(window_size=config.context_window),
    callback_handler=None,
)
```

> **Nota de compatibilidade (validada no spike, [RF01-spike.md](RF01-spike.md)):** com `strands-agents` 1.64.0 existem `SnapshotSessionManager` (de `strands.session`), `LocalFileStorage` (de `strands.storage`) e `SlidingWindowConversationManager` (de `strands.agent.conversation_manager`). `save_latest_on="message"` grava o snapshot a cada mensagem (o padrão do SDK é `"invocation"`). O plano B `FileSessionManager(session_id=..., storage_dir=...)` também foi validado. A sessão fica em `<SESSION_DIR>/session/<SESSION_ID>/scopes/agent/default/snapshots/snapshot_latest.json`.
>
> **Restrição:** o SDK rejeita `SESSION_ID` vazio, `.`, `..` ou com separador de caminho (`/`, `\`). O `config.py` deve validar isso e lançar `ConfigError`.

#### System prompt

```
Você é um meteorologista experiente, simpático e didático.
Responda sempre em português do Brasil, de forma curta e clara.

Regras:
1. Sempre que a pergunta envolver datas relativas ("hoje", "amanhã", "fim de semana",
   "sexta"), chame primeiro a ferramenta obter_data_hora para saber a data atual.
2. Para perguntas sobre o tempo em uma localidade, use SEMPRE a ferramenta consultar_clima.
   A previsão vai até, no máximo, 7 dias.
3. Nunca invente dados meteorológicos. Se uma ferramenta retornar erro, informe que não foi
   possível obter os dados e sugira o que o usuário pode fazer.
4. Se o usuário não informar a cidade, use a última cidade citada na conversa. Se não houver
   nenhuma, pergunte qual é.
5. Quando fizer sentido, dê recomendações práticas (roupa, guarda-chuva, protetor solar).
6. Use °C, mm e km/h.
7. Se a pergunta não for sobre clima, tempo ou data/hora, diga educadamente que esse é seu foco.
```

### 4.3 `tools/data_hora.py` – Tool `obter_data_hora`

| Item        | Definição |
|-------------|-----------|
| Assinatura  | `obter_data_hora() -> dict` |
| Docstring   | "Retorna a data, a hora e o dia da semana atuais no fuso configurado. Use para interpretar referências como hoje, amanhã ou fim de semana." |
| Fonte       | `datetime.now(ZoneInfo(TIMEZONE))` |
| Dependência | `tzdata` (**obrigatória no Windows**, que não traz a base de fusos IANA usada pelo `zoneinfo`) |

O dia da semana é montado com uma lista própria em português, para não depender do locale do Windows.

Exemplo de retorno:

```json
{
  "data": "2026-11-07",
  "hora": "14:32:05",
  "dia_semana": "sábado",
  "fuso": "America/Sao_Paulo",
  "iso": "2026-11-07T14:32:05-03:00"
}
```

### 4.4 `tools/clima.py` – Tool `consultar_clima`

| Item        | Definição |
|-------------|-----------|
| Assinatura  | `consultar_clima(cidade: str, dias: int = 1) -> dict` |
| Docstring   | "Consulta o clima atual e a previsão diária de uma cidade. `cidade`: nome da cidade, podendo incluir estado ou país. `dias`: quantidade de dias de previsão, de 1 a 7." |
| Validação   | `dias` é limitado ao intervalo 1–7. `cidade` vazia gera erro. |

**Sequência:**

1. **Geocoding:** `GET https://geocoding-api.open-meteo.com/v1/search`
   - Parâmetros: `name={cidade}`, `count=1`, `language=pt`, `format=json`
   - Sem `results`: retorna `{"erro": "Cidade não encontrada: <cidade>"}`
2. **Previsão:** `GET https://api.open-meteo.com/v1/forecast`
   - `latitude`, `longitude`, `timezone=auto`, `forecast_days={dias}`
   - `current=temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m`
   - `daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,uv_index_max,sunrise,sunset`
3. **Conversão:** `weather_code` (WMO) → descrição em pt-BR por meio de um dicionário local, por exemplo: 0 = céu limpo, 1–3 = parcialmente nublado/nublado, 45/48 = nevoeiro, 51–57 = garoa, 61–67 = chuva, 71–77 = neve, 80–82 = pancadas de chuva, 95–99 = trovoadas.

Exemplo de retorno:

```json
{
  "local": {"cidade": "Curitiba", "estado": "Paraná", "pais": "Brasil"},
  "atual": {
    "temperatura_c": 18.4, "sensacao_c": 17.9, "umidade_pct": 82,
    "vento_kmh": 11.2, "precipitacao_mm": 0.0, "condicao": "nublado"
  },
  "previsao": [
    {"data": "2026-11-07", "condicao": "chuva moderada", "max_c": 21.0, "min_c": 14.2,
     "chuva_prob_pct": 80, "chuva_mm": 6.3, "uv_max": 5.1,
     "nascer_sol": "05:21", "por_sol": "18:47"}
  ]
}
```

**Erros:** timeout, falha de conexão ou HTTP diferente de 2xx retornam `{"erro": "<mensagem amigável>"}` e nunca levantam exceção para o agente. Assim o LLM consegue explicar a falha ao usuário (RN02).

### 4.5 `main.py` – Loop do chat

```
1. Configurar stdout/stdin para UTF-8 (sys.stdout.reconfigure(encoding="utf-8")).
2. Carregar a Config. Se der ConfigError: imprimir instruções de configuração e sair com código 1.
3. agent = criar_agente(config)
4. Mostrar boas-vindas, incluindo o SESSION_ID e se a sessão foi retomada (len(agent.messages) > 0).
5. Loop:
     entrada = input("Você: ").strip()
     se entrada vazia            -> continue
     se entrada em {sair, exit, quit} -> despedida e break
     try:
         resposta = agent(entrada)
         print("Agente:", str(resposta))
     except Exception (erro da OpenAI/rede):
         print mensagem amigável e continua o loop
6. KeyboardInterrupt / EOFError -> despedida e saída com código 0.
```

Para ser testável, o loop do passo 5 fica isolado na função `executar_chat(agent, ler=input, escrever=print)`. Nos testes, `ler` e `escrever` são substituídos e `agent` é um objeto falso.

A persistência é automática: com `save_latest_on="message"`, o session manager grava o snapshot no disco a cada mensagem adicionada. O `main.py` não precisa salvar nada.

## 5. Fluxos (sequência)

### 5.1 Pergunta com data relativa + clima

```
Usuário        main.py         Agent(Strands)        OpenAI         obter_data_hora   consultar_clima   Open-Meteo   sessions/
   │ "Vai chover   │                  │                  │                  │                │              │            │
   │  amanhã em    │                  │                  │                  │                │              │            │
   │  Curitiba?"   │                  │                  │                  │                │              │            │
   │──────────────►│ agent(pergunta)  │                  │                  │                │              │            │
   │               │─────────────────►│ salva msg user ──┼──────────────────┼────────────────┼──────────────┼───────────►│
   │               │                  │ chat + tools ───►│                  │                │              │            │
   │               │                  │◄── tool_call ────│                  │                │              │            │
   │               │                  │─────────────────────────────────────►│                │              │            │
   │               │                  │◄──────────── {data: 2026-11-07, sábado}                │              │            │
   │               │                  │ chat ───────────►│                  │                │              │            │
   │               │                  │◄── tool_call(cidade=Curitiba, dias=2)                 │              │            │
   │               │                  │──────────────────────────────────────────────────────►│ geocoding +  │            │
   │               │                  │                  │                  │                │ forecast ───►│            │
   │               │                  │◄────────────────────────────────────────── dados ─────│◄─────────────│            │
   │               │                  │ chat ───────────►│                  │                │              │            │
   │               │                  │◄── resposta final│                  │                │              │            │
   │               │                  │ salva msgs ──────┼──────────────────┼────────────────┼──────────────┼───────────►│
   │               │◄──── resposta ───│                  │                  │                │              │            │
   │◄── "Agente: …"│                  │                  │                  │                │              │            │
```

### 5.2 Inicialização com sessão existente

1. O `main.py` cria o agente com `SESSION_ID=sessao-padrao`.
2. O session manager encontra a sessão gravada em `./sessions/` e restaura as mensagens no `agent.messages`.
3. O `main.py` exibe: "Sessão 'sessao-padrao' retomada (N mensagens)."
4. O usuário pergunta "E amanhã?" e o agente usa o histórico restaurado para saber a cidade.

### 5.3 Iniciar uma conversa nova

Há duas formas, ambas sem código adicional:
- trocar `SESSION_ID` no `.env`; ou
- apagar a pasta da sessão dentro de `SESSION_DIR`.

## 6. Tratamento de erros

| Cenário | Onde é tratado | Comportamento |
|---------|----------------|---------------|
| `.env` ausente ou `OPENAI_API_KEY` vazia | `config.py` → `main.py` | Mensagem: "Crie o arquivo .env a partir do .env.example e defina OPENAI_API_KEY". Sai com código 1, sem stack trace. |
| Chave inválida, cota esgotada ou rede indisponível (OpenAI) | `main.py` (try/except em volta de `agent(...)`) | Mensagem amigável. O loop continua. |
| Cidade não encontrada | `consultar_clima` | Retorna `{"erro": ...}` e o agente pede outro nome. |
| Timeout ou erro HTTP na Open-Meteo | `consultar_clima` | Retorna `{"erro": ...}` e o agente informa que não obteve os dados. |
| Fuso inválido em `TIMEZONE` | `config.py` | Valida com `ZoneInfo(...)` na carga e lança `ConfigError`. |
| Arquivo de sessão corrompido | `main.py` | Mensagem sugerindo trocar `SESSION_ID` ou apagar a pasta da sessão. Sai com código 1. |
| `Ctrl+C` / `Ctrl+Z` (EOF) | `main.py` | Despedida e saída limpa. |

## 7. Dependências (`requirements.txt`)

```
strands-agents[openai]
python-dotenv
requests
tzdata
```

> Fixe as versões (`==`) depois da primeira instalação validada, preferindo releases publicadas há pelo menos 7 dias.

## 8. Segurança

- A `OPENAI_API_KEY` só existe no `.env`, que está no `.gitignore`. Nunca é impressa nem logada.
- A pasta `sessions/` contém o histórico das conversas em texto puro e também está no `.gitignore`.
- As tools fazem apenas requisições `GET` a domínios fixos da Open-Meteo. Não executam comandos nem acessam arquivos.

## 9. Estratégia de testes

| Tipo | Alvo | Como |
|------|------|------|
| Unitário | `obter_data_hora` | Fixar o relógio (monkeypatch em `datetime`) e verificar os campos e o dia da semana em pt-BR. |
| Unitário | `consultar_clima` | Simular as respostas HTTP (`responses`/`unittest.mock`) nos cenários: sucesso, cidade não encontrada, timeout, `dias` fora de 1–7. |
| Unitário | `config.py` | Chave ausente, fuso inválido, valores padrão. |
| Integração | Persistência | Criar o agente com um `SESSION_DIR` temporário e um modelo simulado, enviar 2 mensagens, recriar o agente e verificar que `agent.messages` foi restaurado. |
| Manual (E2E) | Chat real | Executar os cenários Gherkin do RF01 com uma chave OpenAI válida. |

Ferramentas (só de desenvolvimento): `pytest`, `pytest-cov` (meta de 80%), `responses` (HTTP simulado) e `ruff` (lint e formatação).

**Modelo simulado:** o SDK não traz um modelo de teste pronto. Os testes usam uma subclasse `ModeloFalso(strands.models.Model)`, em `tests/conftest.py`, que implementa `stream`, `get_config`, `update_config` e `structured_output` e emite eventos roteirizados (texto ou `toolUse`). A referência validada está em [RF01-spike.md](RF01-spike.md), seção 2(d).

## 10. Rastreabilidade

| Requisito do usuário | Atendido por |
|----------------------|--------------|
| 1. Linguagem Python | DD01, seção 7 |
| 2. Arquivo `.env` | DD02, seção 4.1 |
| 3. AWS Strands | DD03, seção 4.2 |
| 4. Memória de sessão em arquivo local | DD05, DD06, DD09, seções 4.2 e 5.2 |
| 5. Tool de data e hora atual | DD07, seção 4.3 |
| 6. Modelo da OpenAI | DD04, seção 4.2 |
