# main.py — пример интеграции в твой бэкенд
"""
Минимальный пример того, как подключить rate_limiter к существующему
эндпоинту /chat. Адаптируй под свой код — у тебя уже есть логика
обращения к Claude/GPT и RAG-поиска.
"""

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from rate_limiter import RateLimiter, MAX_OUTPUT_TOKENS


app = FastAPI(title="ИИ-консультант (демо)")

# CORS — разрешить запросы с твоего фронта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.example.com"],  # подставь свой домен
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

limiter = RateLimiter(api_keys_path="api_keys.json")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    answer: str
    quota_remaining: int


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, x_api_key: str = Header(..., alias="X-API-Key")):
    """Главный эндпоинт ИИ-консультанта."""

    # 1) Проверка длины ввода — до всех остальных проверок
    limiter.check_input(req.message)

    # 2) Проверка квот и списание
    limiter.check_and_consume(x_api_key)

    # 3) Здесь твоя существующая логика:
    #    a. векторный поиск по корпусу (RAG)
    #    b. формирование системного промпта
    #    c. вызов Claude/GPT API с max_tokens=MAX_OUTPUT_TOKENS
    #    d. возврат ответа
    #
    # Заглушка для примера:
    answer = generate_answer(req.message)  # ← твоя функция

    status = limiter.get_status(x_api_key)
    return ChatResponse(answer=answer, quota_remaining=status["personal_remaining"])


@app.get("/quota")
async def get_quota(x_api_key: str = Header(..., alias="X-API-Key")):
    """Эндпоинт для проверки остатка квоты — фронт может показывать
    «осталось N запросов»."""
    if x_api_key not in limiter._keys:
        raise HTTPException(status_code=401, detail="Недействительный API-ключ")
    return limiter.get_status(x_api_key)


def generate_answer(message: str) -> str:
    """Твоя функция обращения к LLM — здесь только заглушка.
    В реальном коде:
      - подбираешь фрагменты из корпуса через эмбеддинги
      - собираешь system prompt с ними
      - вызываешь Claude или GPT с max_tokens=MAX_OUTPUT_TOKENS
      - возвращаешь ответ
    """
    return f"[Заглушка ответа на: {message}]"
