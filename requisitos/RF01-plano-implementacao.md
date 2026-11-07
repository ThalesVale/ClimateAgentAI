# RF01 – Plano de implementação

| Campo         | Valor |
|---------------|-------|
| Requisito     | [RF01-chat-cli.md](RF01-chat-cli.md) (v1.1) |
| Design        | [RF01-design.md](RF01-design.md) (v1.0) |
| Responsável   | Tech Lead (humano), que aprova os gates |
| Execução      | Agentes de IA, coordenados por um agente orquestrador |
| Status        | Em andamento (rollback: Fase 0 concluída, G0 pendente) |
| Data          | 2026-11-07 |

## 1. Objetivo e escopo

Implementar o RF01 (chat de clima no CMD com Strands + OpenAI, memória de sessão em arquivo e as tools `obter_data_hora` e `consultar_clima`) seguindo o design aprovado, com estes padrões de qualidade:

- **Testes automatizados** com `pytest` e **cobertura mínima de 80%**;
- **Lint e formatação** com `ruff`, sem nenhum erro;
- os **12 cenários Gherkin** do RF01 executados manualmente com sucesso.

Fora deste plano: tudo o que está em "Fora de escopo" no RF01, além de CI remoto (GitHub Actions etc.), que pode virar uma melhoria futura.

## 2. Definition of Done (DoD) do RF01

- [ ] Todos os arquivos da estrutura do design (seção 3.2) existem e estão implementados.
- [ ] `ruff check .` e `ruff format --check .` passam sem erros.
- [ ] `pytest --cov --cov-fail-under=80` passa.
- [ ] Nenhum segredo no código. `.env` e `sessions/` estão no `.gitignore`.
- [ ] Os 12 cenários Gherkin do RF01 foram executados manualmente, com evidência registrada.
- [ ] O README permite que outra pessoa instale e rode do zero no Windows.
- [ ] Revisão de código aprovada (agente revisor + Tech Lead).
- [ ] Versões de dependências fixadas (`==`) no `requirements.txt`.

## 3. Agentes de IA

### 3.1 Visão geral

```
                         ┌──────────────────────────┐
                         │   Tech Lead (humano)     │
                         │  aprova gates G0..G4     │
                         └────────────┬─────────────┘
                                      │
                         ┌────────────▼─────────────┐
                         │ AG-00 Orquestrador       │
                         │ planeja, distribui,      │
                         │ atualiza o checklist     │
                         └──┬────┬────┬────┬────┬───┘
            ┌───────────────┘    │    │    │    └───────────────┐
            ▼                    ▼    │    ▼                    ▼
   ┌────────────────┐  ┌──────────────┴──┐  ┌────────────────┐  ┌────────────────┐
   │ AG-01 Ambiente │  │ AG-02 Dev Core  │  │ AG-03 Dev Tools│  │ AG-05 Docs     │
   │ setup / deps   │  │ config/agente/  │  │ data_hora /    │  │ README /       │
   │ ruff / pytest  │  │ main            │  │ clima          │  │ .env.example   │
   └────────────────┘  └────────┬────────┘  └───────┬────────┘  └────────────────┘
                                │                   │
                                ▼                   ▼
                       ┌─────────────────────────────────────┐
                       │ AG-04 QA: testes, cobertura, Gherkin│
                       └──────────────────┬──────────────────┘
                                          ▼
                       ┌─────────────────────────────────────┐
                       │ AG-06 Revisor: código e segurança   │
                       └─────────────────────────────────────┘
```

### 3.2 Catálogo de agentes

| ID    | Agente | Responsabilidade | Permissões | Entradas | Saídas |
|-------|--------|------------------|------------|----------|--------|
| AG-00 | **Orquestrador (Tech Lead IA)** | Quebra o plano em tarefas, envia cada tarefa ao agente certo, consolida os resultados, atualiza o checklist (seção 6) e prepara o material de cada gate. | Leitura total; escrita só em `requisitos/` | RF01, design, este plano | Checklist atualizado, relatório de gate, decisões registradas |
| AG-01 | **Ambiente** | Prepara o ambiente Python, a venv, as dependências, a configuração de `ruff`/`pytest` e o `.gitignore`. Faz o spike de compatibilidade do Strands. | Leitura e escrita na raiz; executa comandos (`pip`, `python`) | Design seção 7, DD04, DD05 | `requirements*.txt`, `pyproject.toml`, `.gitignore`, relatório do spike |
| AG-02 | **Dev Core** | Implementa `config.py`, `agente.py` e `main.py`. | Escrita nos arquivos indicados; execução de testes | Design 4.1, 4.2, 4.5 e 6 | Código + testes unitários dos módulos |
| AG-03 | **Dev Tools** | Implementa `tools/data_hora.py` e `tools/clima.py`, incluindo a tabela WMO. | Escrita em `tools/` e `tests/` | Design 4.3, 4.4 | Código + testes unitários com HTTP simulado |
| AG-04 | **QA** | Completa a suíte de testes, mede a cobertura, roda o teste de integração da sessão e conduz a execução dos cenários Gherkin, coletando evidências. | Escrita em `tests/` e `requisitos/evidencias/`; execução | RF01 seção 10, design seção 9 | Relatório de testes, cobertura, evidências dos cenários |
| AG-05 | **Documentação** | Escreve o README (instalação no Windows, `.env`, uso, como trocar de sessão, como rodar os testes) e o `.env.example`. | Escrita em `README.md` e `.env.example` | Design 4.1, 5.3 e 7 | README, `.env.example` |
| AG-06 | **Revisor (código e segurança)** | Revisa cada entrega contra o design, as regras de negócio, a segurança (chave, logs, `.gitignore`) e a simplicidade (RNF01). Emite um parecer aprovado ou com ajustes. | Somente leitura; executa `ruff`/`pytest` | Diff da entrega, RF01, design | Parecer de revisão com lista de ajustes |

### 3.3 Prompt base de cada agente

Todo agente recebe este **cabeçalho comum**:

```
Contexto: projeto em C:\Users\Teste\Desktop\projeto. Leia requisitos/RF01-chat-cli.md,
requisitos/RF01-design.md e requisitos/RF01-plano-implementacao.md antes de agir.
Regras: siga o design à risca; não adicione dependências fora da seção 7 do design sem aprovação;
nunca grave segredos no código; código e mensagens ao usuário em português do Brasil;
ao terminar, rode `ruff check .`, `ruff format --check .` e `pytest` e informe o resultado.
Entregue: lista de arquivos alterados, resultado dos comandos e pendências/riscos.
```

Instruções específicas:

| Agente | Prompt específico |
|--------|-------------------|
| AG-01 | "Execute as tarefas T01–T04. No spike (T03), confirme no SDK instalado: (a) se existem `SnapshotSessionManager` e `LocalFileStorage` ou, caso contrário, `FileSessionManager`; (b) a assinatura de `OpenAIModel` (`client_args`, `model_id`, `params`); (c) o caminho de import de `SlidingWindowConversationManager`; (d) como simular o modelo em testes sem chamar a OpenAI. Registre as respostas em `requisitos/RF01-spike.md`." |
| AG-02 | "Execute T10–T13. Use o resultado de `requisitos/RF01-spike.md` para os imports. Em `main.py`, isole o loop numa função testável `executar_chat(agent, ler=input, escrever=print)`." |
| AG-03 | "Execute T20–T23. As tools nunca levantam exceção: em caso de erro, retornam `{\"erro\": ...}`. Use `requests` com timeout vindo da Config. Simule o HTTP nos testes com `responses`." |
| AG-04 | "Execute T30–T33. A cobertura mínima é 80%. Para os cenários Gherkin, registre em `requisitos/evidencias/RF01-gherkin.md` a pergunta, a resposta resumida, as tools acionadas e o resultado (OK/NOK)." |
| AG-05 | "Execute T40–T41. O README deve permitir instalar e rodar do zero no Windows CMD, sem conhecimento prévio." |
| AG-06 | "Revise a entrega indicada contra o design, as regras de negócio RN01–RN08 e os RNF01–RNF05. Classifique cada achado como Bloqueante, Importante ou Sugestão. Aprove somente se não houver nenhum Bloqueante." |

## 4. Fases, atividades e dependências

Legenda de status: `[ ]` não iniciado · `[~]` em andamento · `[x]` concluído · `[!]` bloqueado

### Fase 0 – Preparação do ambiente (AG-01)

| ID  | Atividade | Agente | Depende de | Entregável | Critério de aceite |
|-----|-----------|--------|------------|------------|--------------------|
| T01 | Instalar o Python 3.10+ na máquina (`winget install Python.Python.3.12`) e criar a venv `.venv` | AG-01 + Tech Lead | – | `.venv/` | `python --version` ≥ 3.10 dentro da venv |
| T02 | Criar `requirements.txt` (design seção 7) e `requirements-dev.txt` (`pytest`, `pytest-cov`, `ruff`, `responses`); instalar | AG-01 | T01 | Arquivos de dependências | `pip install -r requirements-dev.txt` sem erro |
| T03 | **Spike de compatibilidade do Strands** (session manager, `OpenAIModel`, conversation manager, modelo simulado para testes) | AG-01 | T02 | `requisitos/RF01-spike.md` | As 4 perguntas do prompt respondidas com trecho de código validado |
| T04 | Criar `pyproject.toml` (config de `ruff`, `pytest` e `coverage`), `.gitignore` (`.env`, `sessions/`, `.venv/`, `__pycache__/`, `.coverage`) e a estrutura de pastas vazia (`tools/`, `tests/`) | AG-01 | T02 | Configurações | `ruff check .` e `pytest` executam (mesmo sem testes) |

**Gate G0 (Tech Lead):** ambiente pronto e spike aprovado. Se o spike revelar uma diferença em relação ao design, AG-00 atualiza o design antes de seguir.

### Fase 1 – Núcleo: configuração e agente (AG-02)

| ID  | Atividade | Agente | Depende de | Entregável | Critério de aceite |
|-----|-----------|--------|------------|------------|--------------------|
| T10 | `config.py`: `load_dotenv`, `Config` (dataclass frozen), valores padrão, `ConfigError`, validação da chave e do `TIMEZONE` | AG-02 | G0 | `config.py` + `tests/test_config.py` | Testes: chave ausente, fuso inválido, valores padrão, valores customizados |
| T11 | `agente.py`: `criar_agente(config)` com `OpenAIModel`, `SYSTEM_PROMPT`, tools, session manager e `SlidingWindowConversationManager`, com `callback_handler=None` | AG-02 | T10, T20, T21 | `agente.py` + `tests/test_agente.py` | O agente é criado com as 2 tools, o prompt e o session manager no diretório configurado |
| T12 | `main.py`: UTF-8, carga da config, boas-vindas (sessão nova ou retomada), `executar_chat`, comandos de saída, tratamento de erros (design seção 6) | AG-02 | T11 | `main.py` + `tests/test_main.py` | Testes com agente falso: entrada vazia, `sair`, erro da OpenAI não derruba o loop, `KeyboardInterrupt`, `ConfigError` encerra com código 1 |
| T13 | Revisão da Fase 1 | AG-06 | T10–T12 | Parecer | Nenhum achado Bloqueante |

### Fase 2 – Tools (AG-03), em paralelo à T10

| ID  | Atividade | Agente | Depende de | Entregável | Critério de aceite |
|-----|-----------|--------|------------|------------|--------------------|
| T20 | `tools/data_hora.py`: `@tool obter_data_hora` com `ZoneInfo`, dia da semana em pt-BR e retorno conforme o design 4.3 | AG-03 | G0 | Código + `tests/test_data_hora.py` | Relógio fixado: campos corretos, todos os 7 dias da semana em pt-BR, fuso aplicado |
| T21 | `tools/clima.py`: geocoding + forecast, `dias` limitado a 1–7, tabela WMO em pt-BR, retorno conforme o design 4.4 | AG-03 | G0 | Código + `tests/test_clima.py` | HTTP simulado: sucesso, cidade não encontrada, timeout, HTTP 500, `dias` fora da faixa |
| T22 | Smoke test real das tools (sem LLM): chamar `consultar_clima("Curitiba", 3)` e `obter_data_hora()` direto no Python | AG-03 | T20, T21 | Saída registrada no relatório | Dados reais retornados, sem campo `erro` |
| T23 | Revisão da Fase 2 | AG-06 | T20–T22 | Parecer | Nenhum achado Bloqueante |

**Gate G1 (Tech Lead):** núcleo e tools aprovados (T13 e T23 aprovados, lint e testes passando).

### Fase 3 – Qualidade e testes integrados (AG-04)

| ID  | Atividade | Agente | Depende de | Entregável | Critério de aceite |
|-----|-----------|--------|------------|------------|--------------------|
| T30 | Teste de integração da **persistência de sessão**: `SESSION_DIR` temporário + modelo simulado; 2 mensagens; recriar o agente; verificar o histórico restaurado; com outro `SESSION_ID`, verificar histórico vazio | AG-04 | G1 | `tests/test_sessao.py` | Passa sem acessar a rede |
| T31 | Medir a cobertura e completar os testes faltantes | AG-04 | T30 | Relatório `pytest --cov` | Cobertura ≥ 80% |
| T32 | Execução **manual** dos 12 cenários Gherkin com uma chave OpenAI real | AG-04 + Tech Lead | T31, T40 | `requisitos/evidencias/RF01-gherkin.md` | 12/12 OK |
| T33 | Registrar defeitos encontrados (seção 7) e reenviar ao AG-02/AG-03; repetir até fechar | AG-04 / AG-00 | T32 | Defeitos fechados | Nenhum defeito aberto de severidade alta |

**Gate G2 (Tech Lead):** qualidade aprovada (cobertura ≥ 80%, Gherkin 12/12, lint OK).

### Fase 4 – Documentação e fechamento

| ID  | Atividade | Agente | Depende de | Entregável | Critério de aceite |
|-----|-----------|--------|------------|------------|--------------------|
| T40 | `.env.example` (design 4.1) | AG-05 | T10 | `.env.example` | Contém todas as variáveis, sem nenhuma chave real |
| T41 | `README.md`: pré-requisitos, instalação no Windows, configuração do `.env`, como rodar, trocar ou reiniciar a sessão, como rodar testes e lint, problemas comuns | AG-05 | G2 | `README.md` | Uma pessoa (ou AG-06) segue o README do zero e consegue rodar |
| T42 | Fixar as versões em `requirements.txt` e `requirements-dev.txt` | AG-01 | G2 | Arquivos atualizados | Instalação limpa numa venv nova funciona |
| T43 | Revisão final (código, segurança, DoD) | AG-06 | T41, T42 | Parecer final | DoD 100% marcado |
| T44 | Atualizar o status do RF01 e do design para "Implementado" e registrar as lições aprendidas | AG-00 | T43 | Documentos atualizados | – |

**Gate G3 (Tech Lead):** aceite final do RF01.

### 4.1 Sequência e paralelismo

```
T01 → T02 → T03 → T04 ─► [G0]
                           ├─► T10 ───────────────┐
                           ├─► T20 ─┐              │
                           └─► T21 ─┴─► T22 ─► T23 │
                                     T11 ◄─────────┘ (precisa de T10, T20, T21)
                                     T11 → T12 → T13 ─► [G1]
T10 ─► T40                                            │
[G1] → T30 → T31 → T32 → T33 ─► [G2] → T41, T42 → T43 → T44 ─► [G3]
```

- **Paralelo:** T10 (AG-02) com T20/T21 (AG-03). T40 (AG-05) pode começar assim que a T10 terminar.
- **Caminho crítico:** T01 → T03 → T21 → T11 → T12 → T30 → T32 → T41 → T43.

## 5. Gates de aprovação

| Gate | Quando | Quem aprova | Evidências exigidas |
|------|--------|-------------|---------------------|
| G0 | Fim da Fase 0 | Tech Lead | `python --version`, `RF01-spike.md`, `ruff`/`pytest` executando |
| G1 | Fim das Fases 1 e 2 | Tech Lead | Pareceres T13 e T23 aprovados; saída de `ruff` e `pytest` |
| G2 | Fim da Fase 3 | Tech Lead | Relatório de cobertura ≥ 80%; `RF01-gherkin.md` 12/12 OK |
| G3 | Fim da Fase 4 | Tech Lead | Parecer final do AG-06; DoD 100% |

Regra: **nenhuma fase começa sem o gate anterior aprovado**, exceto as atividades marcadas como paralelas.

## 6. Checklist de acompanhamento

> Atualizado pelo AG-00 ao fim de cada tarefa. Cada atualização registra a data e um resumo no histórico (seção 9).

| ID  | Atividade | Agente | Status | Evidência / Observação |
|-----|-----------|--------|--------|------------------------|
| T01 | Instalar Python e criar a venv | AG-01 + TL | [x] | Python 3.14.6 já instalado (launcher `py`); `.venv` criada |
| T02 | Dependências | AG-01 | [x] | `requirements.txt`, `requirements-dev.txt`; `pip check` OK; strands-agents 1.64.0 |
| T03 | Spike Strands | AG-01 | [x] | [RF01-spike.md](RF01-spike.md): (a)–(d) validados; design atualizado para v1.1 |
| T04 | `pyproject`, `.gitignore`, estrutura | AG-01 | [x] | `ruff check` e `ruff format --check` OK; `pytest` sem testes (exit 5) |
| G0  | **Gate ambiente** | TL | [~] | Aguardando aprovação do Tech Lead |
| T10 | `config.py` | AG-02 | [ ] | |
| T20 | Tool `obter_data_hora` | AG-03 | [ ] | |
| T21 | Tool `consultar_clima` | AG-03 | [ ] | |
| T22 | Smoke test das tools | AG-03 | [ ] | |
| T23 | Revisão das tools | AG-06 | [ ] | |
| T11 | `agente.py` | AG-02 | [ ] | |
| T12 | `main.py` | AG-02 | [ ] | |
| T13 | Revisão do núcleo | AG-06 | [ ] | |
| G1  | **Gate núcleo + tools** | TL | [ ] | |
| T40 | `.env.example` | AG-05 | [ ] | |
| T30 | Integração da sessão | AG-04 | [ ] | |
| T31 | Cobertura ≥ 80% | AG-04 | [ ] | |
| T32 | Gherkin manual 12/12 | AG-04 + TL | [ ] | |
| T33 | Correção de defeitos | AG-04 / AG-00 | [ ] | |
| G2  | **Gate qualidade** | TL | [ ] | |
| T41 | README | AG-05 | [ ] | |
| T42 | Fixar versões | AG-01 | [ ] | |
| T43 | Revisão final | AG-06 | [ ] | |
| T44 | Fechamento | AG-00 | [ ] | |
| G3  | **Aceite final** | TL | [ ] | |

### 6.1 Indicadores

| Indicador | Meta | Atual |
|-----------|------|-------|
| Tarefas concluídas | 25/25 (incluindo gates) | 4/25 |
| Cobertura de testes | ≥ 80% | – |
| Erros de `ruff` | 0 | – |
| Cenários Gherkin OK | 12/12 | 0/12 |
| Defeitos abertos (alta/média/baixa) | 0/0/– | – |
| Linhas de código (sem testes) | < 250 (RNF01) | – |

## 7. Registro de defeitos

| ID | Encontrado em | Descrição | Severidade | Agente responsável | Status |
|----|---------------|-----------|------------|--------------------|--------|
| –  | –             | –         | –          | –                  | –      |

Severidades: **Alta** (quebra um cenário Gherkin, uma RN ou a segurança) · **Média** (comportamento incorreto com contorno) · **Baixa** (cosmético).

## 8. Riscos

| ID | Risco | Prob. | Impacto | Mitigação | Dono |
|----|-------|-------|---------|-----------|------|
| R01 | Python ainda não instalado na máquina | Certa | Alto | T01 é a primeira tarefa e precisa do Tech Lead (pode exigir privilégio de administrador) | TL |
| R02 | API do Strands diferente do design (session manager, imports) | Média | Médio | Spike T03 antes de codar; plano B `FileSessionManager` previsto no design | AG-01 |
| R03 | Dificuldade de simular o modelo nos testes, afetando a cobertura | Média | Médio | Spike T03 (d); `executar_chat` testável com agente falso | AG-04 |
| R04 | Custo e cota da OpenAI nos testes manuais | Baixa | Baixo | Testes automatizados não chamam a OpenAI; manual só na T32, com `gpt-4o-mini` | TL |
| R05 | O LLM não aciona `obter_data_hora` em datas relativas | Média | Médio | Regra explícita no system prompt; cenário Gherkin dedicado; ajuste de prompt na T33 | AG-02 |
| R06 | Indisponibilidade ou limite da Open-Meteo | Baixa | Baixo | Tool retorna `erro`; testes automatizados usam HTTP simulado | AG-03 |
| R07 | Acentuação quebrada no CMD | Média | Baixo | `sys.stdout.reconfigure(encoding="utf-8")`; validação na T32 no CMD e no PowerShell | AG-02 |
| R08 | Vazamento da chave (commit do `.env`) | Baixa | Alto | `.gitignore` na T04; checagem do AG-06 em todas as revisões | AG-06 |

## 9. Histórico de acompanhamento

| Data | Autor | Atualização |
|------|-------|-------------|
| 2026-11-07 | AG-00 | Plano criado. Aguardando a T01 (instalação do Python). |
| 2026-11-07 | AG-00 | Fase 0 concluída (T01–T04). R01 resolvido: Python 3.14.6 via `py`. Spike sem bloqueios. Design v1.1: `save_latest_on="message"`, `executar_chat`, validação do `SESSION_ID`, `ModeloFalso` nos testes. Script do spike mantido em `requisitos/spike/` como evidência. G0 aguardando o Tech Lead. |
| 2026-11-07 | AG-00 | G0 aprovado. Fases 1 e 2 concluídas (T10–T13, T20–T23): 65 testes, cobertura de 99%, `ruff` sem erros. Revisão AG-06: aprovado. **Importante:** RNF01 estourado em linhas físicas (385; 329 não vazias), embora sejam 156 instruções; o peso vem da tabela WMO (28 códigos) e do mapeamento de campos. Decisão pendente do TL: aceitar e redefinir a métrica ou compactar. **Sugestão:** risco R09 adicionado para validar na T32. Desvios menores aceitos: `ModeloFalso` em `tests/fakes.py` (não em `conftest.py`); `ruff format` também formata os snippets Python de `RF01-spike.md`. |
| 2026-11-07 | AG-00 | **Rollback para o fim da Fase 0**, a pedido do Tech Lead. A Fase 3 foi interrompida no meio da T32. O trabalho das Fases 1 a 3 (código, testes, `.env.example`, evidências, `sessions_qa/`) foi movido para `../projeto_backup_fases1-3/`, sem exclusão. `.gitignore` e RNF01 restaurados. G0 e G1 voltam a pendente. O `.env` foi mantido. |
