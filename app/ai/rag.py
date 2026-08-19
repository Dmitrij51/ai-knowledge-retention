from app.ai.context import ContextBuilder
from app.ai.llm import OllamaLLM
from app.models.chunk import Chunk
from app.search.service import SearchService


class RAGResponse:
    def __init__(
        self,
        answer: str,
        sources: list[tuple[float, Chunk]],
    ):
        self.answer = answer
        self.sources = sources


class RAGService:
    """
    RAG-сервис:

    1. Ищет информацию в базе знаний.
    2. Проверяет, есть ли релевантные источники.
    3. Формирует контекст.
    4. Передаёт контекст локальной LLM.
    5. Возвращает ответ вместе с источниками.
    """

    def __init__(
        self,
        search_service: SearchService | None = None,
        llm: OllamaLLM | None = None,
        context_builder: ContextBuilder | None = None,
    ):
        self.search_service = search_service or SearchService()
        self.llm = llm or OllamaLLM()

        self.context_builder = context_builder or ContextBuilder(
            max_chunks=5,
            max_chars=8000,
        )

    def ask(
        self,
        question: str,
        limit: int = 5,
    ) -> RAGResponse:

        if not question.strip():
            raise ValueError("Вопрос не может быть пустым")

        # -----------------------------------------
        # 1. Ищем информацию
        # -----------------------------------------

        results = self.search_service.search(
            query=question,
            limit=limit,
        )

        # -----------------------------------------
        # 2. Если ничего не найдено —
        #    НЕ вызываем LLM
        # -----------------------------------------

        if not results:
            return RAGResponse(
                answer="В базе знаний недостаточно информации для точного ответа.",
                sources=[],
            )

        # -----------------------------------------
        # 3. Формируем контекст
        # -----------------------------------------

        context = self.context_builder.build(results)

        if not context.strip():
            return RAGResponse(
                answer="В базе знаний недостаточно информации для точного ответа.",
                sources=[],
            )

        # -----------------------------------------
        # 4. Формируем prompt
        # -----------------------------------------

        prompt = f"""
Ты — AI-ассистент локальной базы знаний.

Отвечай ТОЛЬКО на основе информации из контекста.

Очень важные правила:

1. Не используй свои знания, если их нет в контексте.
2. Не придумывай факты.
3. Не добавляй информацию от себя.
4. Если на вопрос нельзя ответить на основе контекста,
   скажи:

"В базе знаний недостаточно информации для точного ответа."

5. Отвечай кратко и понятно.
6. Если пользователь пишет на русском — отвечай на русском.
7. Не упоминай, что ты анализировал контекст.
8. Не придумывай преимущества, недостатки, характеристики
   или дополнительные сведения.

Контекст из базы знаний:

{context}

Вопрос пользователя:

{question}

Ответ:
""".strip()

        # -----------------------------------------
        # 5. Запускаем LLM
        # -----------------------------------------

        answer = self.llm.generate(prompt)

        # -----------------------------------------
        # 6. Возвращаем ответ + источники
        # -----------------------------------------

        return RAGResponse(
            answer=answer.strip(),
            sources=results,
        )
