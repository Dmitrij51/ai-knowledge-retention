from app.parsers.docx import parse_docx


text = parse_docx("test.docx")

print(text)