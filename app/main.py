from app.services.ingestion import ingest_document


def main():
    document_id = ingest_document("test.txt")

    print(f"\nDocument ID: {document_id}")


if __name__ == "__main__":
    main()
