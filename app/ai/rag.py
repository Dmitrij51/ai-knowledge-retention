from app.ai.context import ContextBuilder
from app.ai.llm import OllamaLLM
from app.models.chunk import Chunk
from app.search.service import SearchService


NO_ANSWER = "В базе знаний недостаточно информации для точного ответа."


class RAGResponse:
    """
    Результат работы RAG.

    answer:
        Ответ LLM в Markdown-формате.

    sources:
        Chunks, которые были использованы для формирования ответа.
    """

    def __init__(
        self,
        answer: str,
        sources: list[tuple[float, Chunk]],
    ):
        self.answer = answer
        self.sources = sources


class RAGService:
    """
    RAG pipeline:

        вопрос
          ↓
        Hybrid Search
          ↓
        найденные chunks
          ↓
        ContextBuilder
          ↓
        prompt
          ↓
        Ollama / Qwen
          ↓
        Markdown-ответ
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

        question = question.strip()

        if not question:
            raise ValueError("Вопрос не может быть пустым")

        if limit <= 0:
            raise ValueError("limit должен быть больше 0")

        # --------------------------------------------------------
        # 1. Поиск
        # --------------------------------------------------------

        results = self.search_service.search(
            query=question,
            limit=limit,
        )

        # --------------------------------------------------------
        # DEBUG SEARCH
        # --------------------------------------------------------

        print()
        print("=" * 80)
        print("RAG QUESTION")
        print("=" * 80)
        print(question)

        print()
        print("=" * 80)
        print("RAG SEARCH RESULTS")
        print("=" * 80)

        for score, chunk in results:
            print(
                f"\n"
                f"score: {score:.4f}\n"
                f"chunk_id: {chunk.id}\n"
                f"document_id: {chunk.document_id}\n"
                f"content:\n{chunk.content[:500]}"
            )

        # --------------------------------------------------------
        # 2. Ничего не найдено
        # --------------------------------------------------------

        if not results:
            print()
            print("=" * 80)
            print("RAG: NO SEARCH RESULTS")
            print("=" * 80)

            return RAGResponse(
                answer=NO_ANSWER,
                sources=[],
            )

        # --------------------------------------------------------
        # 3. Контекст
        # --------------------------------------------------------

        context = self.context_builder.build(results)

        print()
        print("=" * 80)
        print("RAG CONTEXT")
        print("=" * 80)
        print(context)

        if not context.strip():
            print()
            print("=" * 80)
            print("RAG: EMPTY CONTEXT")
            print("=" * 80)

            return RAGResponse(
                answer=NO_ANSWER,
                sources=[],
            )

        # --------------------------------------------------------
        # 4. Prompt
        # --------------------------------------------------------

        prompt = self._build_prompt(
            question=question,
            context=context,
        )

        print()
        print("=" * 80)
        print("RAG PROMPT")
        print("=" * 80)
        print(prompt)

        # --------------------------------------------------------
        # 5. Ollama / Qwen
        # --------------------------------------------------------

        try:
            answer = self.llm.generate(prompt)
        except Exception as exc:
            print()
            print("=" * 80)
            print("RAG LLM ERROR")
            print("=" * 80)
            print(exc)
            raise

        # --------------------------------------------------------
        # 6. Нормализация
        # --------------------------------------------------------

        answer = answer.strip()

        if not answer:
            answer = NO_ANSWER

        print()
        print("=" * 80)
        print("RAG ANSWER")
        print("=" * 80)
        print(answer)

        return RAGResponse(
            answer=answer,
            sources=results,
        )

    def _build_prompt(
        self,
        question: str,
        context: str,
    ) -> str:
        """
        Prompt для небольшой локальной модели.

        Модель должна возвращать Markdown, чтобы frontend
        мог красиво показать текст, списки и код.
        """

        return f"""
Ты помощник по локальной базе знаний.

Ответь на вопрос пользователя, используя ТОЛЬКО информацию
из блока БАЗА ЗНАНИЙ.

ПРАВИЛА:

1. Не выдумывай информацию.
2. Если нужная информация есть в базе, используй её.
3. Отвечай непосредственно на вопрос.
4. Отвечай на языке вопроса.
5. Не упоминай RAG, chunks, embeddings, поиск, контекст
   и внутренние механизмы системы.
6. Не начинай ответ словами "Согласно базе знаний" или
   "Согласно предоставленной информации".
7. Ответ должен быть понятным и компактным.
8. Используй Markdown для красивого отображения ответа.
9. Для важных терминов используй **жирный текст**.
10. Для названий функций, классов, файлов, команд и коротких
    фрагментов кода используй `одинарные обратные кавычки`.
11. Для многострочного кода ВСЕГДА используй блок:

```python
код
```

12. Никогда не заключай обычный ответ, код или отдельные строки
    кода в кавычки "..." или «...».
13. Если приводишь код из базы знаний, сохраняй его содержимое
    без изменения.
14. Не добавляй комментарии к коду, которых не было в базе,
    если пользователь их не просил.
15. Если информации действительно недостаточно, ответь ровно:

В базе знаний недостаточно информации для точного ответа.

БАЗА ЗНАНИЙ:

{context}

ВОПРОС:

{question}

ОТВЕТ:
""".strip()
