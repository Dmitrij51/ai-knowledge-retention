from app.parsers.document_loader import load_document
from app.processing.cleaner import clean_text
from app.processing.chunker import split_text


file_path = "test.txt"

text = load_document(file_path)

cleaned_text = clean_text(text)

chunks = split_text(cleaned_text, chunk_size=100, overlap=20)

print(f"Найдено chunks: {len(chunks)}")

for index, chunk in enumerate(chunks, start=1):
    print("\n" + "=" * 50)
    print(f"CHUNK {index}")
    print("=" * 50)
    print(chunk)
