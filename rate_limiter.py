# rate_limiter.py
"""
Лимитирование запросов к ИИ-консультанту для академического тестирования.
Бюджет: до $5 на ~250 запросов от 10 рецензентов.

Использование (FastAPI):
    from rate_limiter import RateLimiter, require_valid_key

    limiter = RateLimiter(api_keys_path="api_keys.json")

    @app.post("/chat")
    async def chat(req: ChatRequest, api_key: str = Header(...)):
        await limiter.check_and_consume(api_key)
        # ... остальная логика обращения к LLM
"""

from __future__ import annotations
import json
import time
from collections import defaultdict, deque
from pathlib import Path
from threading import Lock
from typing import Deque
from fastapi import HTTPException, status


# ============================================================
# КОНФИГУРАЦИЯ — настрой под себя
# ============================================================

GLOBAL_BUDGET_REQUESTS = 250         # общий лимит на всё демо
PER_KEY_BUDGET = 25                  # запросов на одного рецензента
RATE_LIMIT_PER_MINUTE = 5            # запросов в минуту на ключ
MAX_INPUT_CHARS = 1500               # макс. длина пользовательского запроса
MAX_OUTPUT_TOKENS = 600              # макс. токенов в ответе модели

STATE_FILE = Path("rate_limiter_state.json")  # куда писать счётчики


# ============================================================
# КЛАСС ЛИМИТЕРА
# ============================================================

class RateLimiter:
    def __init__(self, api_keys_path: str = "api_keys.json"):
        self._lock = Lock()
        self._keys = self._load_keys(api_keys_path)
        self._state = self._load_state()
        # Окно для rate limit (последние N запросов с timestamp)
        self._windows: dict[str, Deque[float]] = defaultdict(lambda: deque(maxlen=RATE_LIMIT_PER_MINUTE))

    @staticmethod
    def _load_keys(path: str) -> set[str]:
        """Список валидных API-ключей рецензентов из JSON-файла."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return set(data.get("keys", []))
        except FileNotFoundError:
            raise RuntimeError(f"Не найден файл с API-ключами: {path}")

    @staticmethod
    def _load_state() -> dict:
        """Загружает счётчики из файла либо создаёт пустые."""
        if STATE_FILE.exists():
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"global_used": 0, "per_key": {}}

    def _save_state(self) -> None:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self._state, f, ensure_ascii=False, indent=2)

    def check_input(self, user_message: str) -> None:
        """Проверяет, что входящий запрос не превышает лимит длины."""
        if len(user_message) > MAX_INPUT_CHARS:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"Запрос слишком длинный ({len(user_message)} символов). "
                    f"Максимум {MAX_INPUT_CHARS} символов. "
                    f"Сформулируйте вопрос короче."
                ),
            )

    def check_and_consume(self, api_key: str) -> None:
        """Главная функция — проверка всех лимитов + списание квоты."""
        with self._lock:
            # 1) Валидность ключа
            if api_key not in self._keys:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Недействительный API-ключ",
                )

            # 2) Глобальный лимит
            if self._state["global_used"] >= GLOBAL_BUDGET_REQUESTS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        "Демонстрационный лимит запросов исчерпан. "
                        "Прототип временно недоступен."
                    ),
                )

            # 3) Лимит на ключ
            used = self._state["per_key"].get(api_key, 0)
            if used >= PER_KEY_BUDGET:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Вы исчерпали лимит запросов в рамках демонстрации "
                        f"({PER_KEY_BUDGET} запросов). Спасибо за тестирование."
                    ),
                )

            # 4) Rate limit (5 запросов в минуту)
            now = time.time()
            window = self._windows[api_key]
            # удаляем устаревшие
            while window and now - window[0] > 60:
                window.popleft()
            if len(window) >= RATE_LIMIT_PER_MINUTE:
                wait = int(60 - (now - window[0]))
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=(
                        f"Слишком частые запросы. Попробуйте через {wait} сек."
                    ),
                )
            window.append(now)

            # 5) Списание квоты
            self._state["global_used"] += 1
            self._state["per_key"][api_key] = used + 1
            self._save_state()

    def get_status(self, api_key: str) -> dict:
        """Возвращает остаток квоты для отображения пользователю."""
        with self._lock:
            used = self._state["per_key"].get(api_key, 0)
            return {
                "personal_remaining": max(0, PER_KEY_BUDGET - used),
                "personal_limit": PER_KEY_BUDGET,
                "global_remaining": max(0, GLOBAL_BUDGET_REQUESTS - self._state["global_used"]),
            }
