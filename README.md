# AI Knowledge Retention

Локальная система сохранения и поиска знаний. Загружаете документы — система индексирует их, а потом отвечает на вопросы на основе вашего контента.

Всё работает на вашем компьютере, без облаков и API-ключей.

---

## 📦 Что умеет

### Наблюдение за файлами

- Отслеживает папки в реальном времени (через `watchdog`)
- Автоматически парсит новые и изменённые файлы
- Поддерживает: **PDF**, **DOCX**, **Markdown**, **TXT**
- Версионирование документов с историей изменений
- Soft-delete: удалённые документы можно восстановить

### Индексация

- Разбивает текст на смысловые чанки
- Создаёт эмбеддинги через `intfloat/multilingual-e5-small` (локально)
- Строит полнотекстовый индекс (FTS5) поверх SQLite

### Поиск

- **Гибридный поиск**: семантический + полнотекстовый (BM25)
- Объединяет результаты двух методов с весами
- Возвращает релевантные чанки с оценкой совпадения

### RAG-ответы

- Задаёте вопрос → система находит релевантные чанки
- Формирует контекст и отправляет в локальную LLM
- Модель: **Qwen 3 1.7B** через **Ollama**
- Ответ в Markdown с указанием источников

### Веб-интерфейс и API

- FastAPI с Swagger-документацией (`/docs`)
- Веб-интерфейс для поиска и RAG-вопросов
- REST API для управления папками и документами

---

## 🏗 Архитектура

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Watchdog   │────▶│   Parser     │────▶│  Ingestion   │
│  File Watcher│     │  PDF/DOCX/   │     │  Chunks &    │
│              │     │  MD/TXT      │     │  Embeddings  │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                                    ┌────────────▼────────────┐
                                    │        SQLite DB         │
                                    │  Documents | Chunks |    │
                                    │  Embeddings | FTS5 |     │
                                    │  Versions | Watched      │
                                    │  Folders                 │
                                    └────┬──────────────┬─────┘
                                         │              │
                            ┌────────────▼────┐  ┌──────▼──────────┐
                            │  Hybrid Search  │  │     RAG Pipeline│
                            │ Semantic + FTS  │  │ Search + LLM    │
                            └────────┬────────┘  └──────┬──────────┘
                                     │                  │
                            ┌────────▼──────────────────▼────────┐
                            │        FastAPI + Web UI             │
                            │  /search  /ask  /documents          │
                            └────────────────────────────────────┘
```

---

## 🚀 Запуск с нуля

### Шаг 1. Установите Python

Python 3.10 или новее. Проверьте:

```bash
python --version
```

### Шаг 2. Установите Ollama

1. Скачайте с **[https://ollama.com](https://ollama.com)**
2. Установите и запустите сервис
3. Проверьте:

```bash
ollama --version
```

### Шаг 3. Скачайте модель LLM

```bash
ollama pull qwen3:1.7b
```

### Шаг 4. Создайте виртуальное окружение

```bash
python -m venv venv
```

**Windows:**

```bash
venv\Scripts\activate
```

**Linux / macOS:**

```bash
source venv/bin/activate
```

### Шаг 5. Установите зависимости

```bash
pip install -r requirements.txt
```

### Шаг 6. Скачайте модель эмбеддингов

```bash
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('intfloat/multilingual-e5-small', cache_folder='models_ai')
model.save('models_ai/multilingual-e5-small')
"
```

Модель окажется в папке `models_ai/multilingual-e5-small`.

### Шаг 7. Примените миграции базы данных

```bash
alembic upgrade head
```

### Шаг 8. Запустите приложение

**Веб-сервер (рекомендуется):**

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

Откройте **http://localhost:8000** в браузере.

Swagger-документация: **http://localhost:8000/docs**

---

## 📡 API

| Метод  | Путь                            | Описание                    |
| ------ | ------------------------------- | --------------------------- |
| GET    | `/`                             | Веб-интерфейс               |
| GET    | `/search?q=...&limit=10`        | Поиск по базе знаний        |
| GET    | `/ask?q=...`                    | RAG-ответ на вопрос         |
| GET    | `/documents`                    | Список документов           |
| GET    | `/documents/{id}/file`          | Скачать оригинал            |
| GET    | `/documents/{id}/versions`      | История версий              |
| GET    | `/watched-folders`              | Список папок                |
| POST   | `/watched-folders`              | Добавить папку              |
| POST   | `/watched-folders/{id}/enable`  | Включить                    |
| POST   | `/watched-folders/{id}/disable` | Отключить                   |
| POST   | `/watched-folders/{id}/rescan`  | Повторное сканирование      |
| DELETE | `/watched-folders/{id}`         | Удалить папку из наблюдения |

### Примеры

**Поиск:**

```bash
curl "http://localhost:8000/search?q=как%20настроить%20базу%20данных&limit=5"
```

**RAG-вопрос:**

```bash
curl "http://localhost:8000/ask?q=что%20такое%20гибридный%20поиск?"
```

**Добавить папку:**

```bash
curl -X POST http://localhost:8000/watched-folders \
  -H "Content-Type: application/json" \
  -d '{"path": "C:/Documents/notes"}'
```

---

## ⚙️ Конфигурация

Файл: `app/config.py`

| Параметр               | По умолчанию                      | Описание             |
| ---------------------- | --------------------------------- | -------------------- |
| `EMBEDDING_MODEL_NAME` | `intfloat/multilingual-e5-small`  | Название модели      |
| `EMBEDDING_MODEL_PATH` | `models_ai/multilingual-e5-small` | Путь к модели        |
| `EMBEDDING_DIMENSION`  | `384`                             | Размерность векторов |

---

## 📂 Структура проекта

```
ai-knowledge-retention/
├── app/
│   ├── ai/              # Эмбеддинги, LLM, RAG
│   │   ├── embeddings.py  # SentenceTransformer
│   │   ├── llm.py         # Ollama / Qwen
│   │   ├── rag.py         # RAG-пайплайн
│   │   └── vector.py      # Утилиты векторов
│   ├── api/             # FastAPI
│   │   ├── main.py        # Приложение
│   │   ├── routes.py      # Эндпоинты
│   │   └── schemas.py     # Pydantic-модели
│   ├── web/             # Веб-интерфейс
│   ├── connectors/      # Подключение источников (Git, файлы)
│   ├── models/          # SQLAlchemy-модели
│   ├── parsers/         # Парсеры документов
│   ├── processing/      # Очистка, чанкинг, diff
│   ├── search/          # Гибридный поиск
│   ├── services/        # Ингестия, эмбеддинги
│   ├── storage/         # Работа с БД
│   ├── watcher/         # Наблюдение за файлами
│   └── config.py        # Конфигурация
├── alembic/             # Миграции БД
├── tests/               # Тесты
├── requirements.txt     # Зависимости
└── alembic.ini          # Конфиг Alembic
```

---

## 🧪 Тесты

```bash
python -m pytest tests/
```

---

## 📋 Требования к системе

- **RAM**: минимум 4 ГБ (модель эмбеддингов ~150 МБ)
- **CPU**: любой современный, эмбеддинги работают на CPU
- **Ollama**: нужен для генерации ответов через RAG
- **Диск**: место зависит от объёма загруженных документов

---

## ⚠️ Известные ограничения

- Эмбеддинги рассчитываются на CPU — большие документы обрабатываются не мгновенно
- Модель Qwen 3 1.7B — лёгкая, для сложных вопросов может потребоваться модель побольше
- Веб-интерфейс использует `tkinter` для выбора папок — может не работать без GUI-среды

---
