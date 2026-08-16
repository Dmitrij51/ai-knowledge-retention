from app.parsers.document_loader import load_document
from app.processing.cleaner import clean_text
from app.processing.chunker import split_text
from app.storage.documents import create_document
from app.storage.chunks import create_chunks


file_path = "test.txt"


# 1. Читаем документ
text = load_document(file_path)

# 2. Очищаем текст
cleaned_text = clean_text(text)

# 3. Разбиваем на chunks
chunks = split_text(
    cleaned_text,
    chunk_size=500,
    overlap=100,
)

# 4. Сохраняем документ
document = create_document(file_path)

# 5. Сохраняем chunks
saved_chunks = create_chunks(
    document.id,
    chunks,
)


print("Документ обработан!")

print(f"Документ: {document.filename}")
print(f"ID: {document.id}")
print(f"Chunks сохранено: {len(saved_chunks)}")
