import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv
from strands import Agent, tool
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.models.openai import OpenAIModel
from strands.session import SnapshotSessionManager
from strands.storage import LocalFileStorage

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
SESSION_ID = os.getenv("SESSION_ID", "sessao-padrao")
SESSION_DIR = os.getenv("SESSION_DIR", "./sessions")
CONTEXT_WINDOW = int(os.getenv("CONTEXT_WINDOW", "20"))
TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "10"))

SAIDAS = {"sair", "exit", "quit"}
DIAS_SEMANA = [
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
]
WMO = {
    0: "céu limpo",
    1: "predominantemente limpo",
    2: "parcialmente nublado",
    3: "nublado",
    45: "nevoeiro",
    48: "nevoeiro com geada",
    51: "garoa fraca",
    53: "garoa moderada",
    55: "garoa forte",
    56: "garoa congelante fraca",
    57: "garoa congelante forte",
    61: "chuva fraca",
    63: "chuva moderada",
    65: "chuva forte",
    66: "chuva congelante fraca",
    67: "chuva congelante forte",
    71: "neve fraca",
    73: "neve moderada",
    75: "neve forte",
    77: "grãos de neve",
    80: "pancadas de chuva fracas",
    81: "pancadas de chuva moderadas",
    82: "pancadas de chuva violentas",
    85: "pancadas de neve fracas",
    86: "pancadas de neve fortes",
    95: "trovoada",
    96: "trovoada com granizo fraco",
    99: "trovoada com granizo forte",
}

SYSTEM_PROMPT = """Você é um meteorologista experiente, simpático e didático.
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
7. Se a pergunta não for sobre clima, tempo ou data/hora, diga educadamente que esse é seu foco."""


@tool
def obter_data_hora() -> dict:
    """Retorna a data, a hora e o dia da semana atuais no fuso configurado.

    Use para interpretar referências como hoje, amanhã ou fim de semana.
    """
    agora = datetime.now(ZoneInfo(TIMEZONE))
    return {
        "data": agora.strftime("%Y-%m-%d"),
        "hora": agora.strftime("%H:%M:%S"),
        "dia_semana": DIAS_SEMANA[agora.weekday()],
        "fuso": TIMEZONE,
    }


@tool
def consultar_clima(cidade: str, dias: int = 1) -> dict:
    """Consulta o clima atual e a previsão diária de uma cidade.

    Args:
        cidade: Nome da cidade, podendo incluir estado ou país.
        dias: Quantidade de dias de previsão, de 1 a 7.
    """
    cidade = (cidade or "").strip()
    if not cidade:
        return {"erro": "Informe o nome de uma cidade."}
    try:
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": cidade, "count": 1, "language": "pt", "format": "json"},
            timeout=HTTP_TIMEOUT,
        )
        geo.raise_for_status()
        resultados = geo.json().get("results")
        if not resultados:
            return {"erro": f"Cidade não encontrada: {cidade}"}
        local = resultados[0]
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": local["latitude"],
                "longitude": local["longitude"],
                "timezone": "auto",
                "forecast_days": min(max(int(dias), 1), 7),
                "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                "precipitation,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                "precipitation_probability_max,precipitation_sum,uv_index_max,sunrise,sunset",
            },
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        dados = resp.json()
        atual, d = dados["current"], dados["daily"]
        return {
            "local": {
                "cidade": local.get("name"),
                "estado": local.get("admin1"),
                "pais": local.get("country"),
            },
            "atual": {
                "temperatura_c": atual["temperature_2m"],
                "sensacao_c": atual["apparent_temperature"],
                "umidade_pct": atual["relative_humidity_2m"],
                "vento_kmh": atual["wind_speed_10m"],
                "precipitacao_mm": atual["precipitation"],
                "condicao": WMO.get(atual["weather_code"], "condição desconhecida"),
            },
            "previsao": [
                {
                    "data": d["time"][i],
                    "condicao": WMO.get(d["weather_code"][i], "condição desconhecida"),
                    "max_c": d["temperature_2m_max"][i],
                    "min_c": d["temperature_2m_min"][i],
                    "chuva_prob_pct": d["precipitation_probability_max"][i],
                    "chuva_mm": d["precipitation_sum"][i],
                    "uv_max": d["uv_index_max"][i],
                    "nascer_sol": d["sunrise"][i][11:16],
                    "por_sol": d["sunset"][i][11:16],
                }
                for i in range(len(d["time"]))
            ],
        }
    except requests.Timeout:
        return {"erro": "Tempo esgotado ao consultar o serviço de clima."}
    except (requests.RequestException, ValueError, KeyError, TypeError, IndexError):
        return {"erro": "Não foi possível obter os dados de clima no momento."}


def build_agent() -> Agent:
    model = OpenAIModel(
        client_args={"api_key": OPENAI_API_KEY},
        model_id=OPENAI_MODEL,
        params={"temperature": OPENAI_TEMPERATURE},
    )
    return Agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=[obter_data_hora, consultar_clima],
        session_manager=SnapshotSessionManager(
            session_id=SESSION_ID,
            storage=LocalFileStorage(SESSION_DIR),
            save_latest_on="message",
        ),
        conversation_manager=SlidingWindowConversationManager(window_size=CONTEXT_WINDOW),
        callback_handler=None,
    )


def main() -> None:
    for fluxo in (sys.stdin, sys.stdout):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")

    if not OPENAI_API_KEY:
        print("OPENAI_API_KEY não definida. Crie o arquivo .env a partir do .env.example.")
        sys.exit(1)

    agent = build_agent()
    print("=== Chat de clima === (digite 'sair' para encerrar)")
    if agent.messages:
        print(f"Sessão '{SESSION_ID}' retomada ({len(agent.messages)} mensagens).")
    else:
        print(f"Nova sessão '{SESSION_ID}'.")

    while True:
        try:
            message = input("Você: ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not message:
            continue
        if message.lower() in SAIDAS:
            break

        try:
            result = agent(message)
            print(f"Agente: {result}")
        except Exception as erro:
            print(f"Não foi possível obter a resposta ({type(erro).__name__}). Tente de novo.")

    print("Encerrado. Até logo!")


if __name__ == "__main__":
    main()
