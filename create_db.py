from pathlib import Path

import tyro
from dotenv import load_dotenv

from doc_database import APIDocumentManager, DocumentManager


def main(directory_path: Path, db_path: Path):
    # # Create embeddings for documents
    doc_manager = DocumentManager(directory_path)
    doc_manager.load_documents()
    doc_manager.split_documents()
    doc_manager.create_embeddings(db_path / "documents")

    # Create embeddings for API
    api_manager = APIDocumentManager(directory_path / "python_api.md")
    api_manager.load_api_document()
    api_manager.get_api_key()
    api_manager.create_embeddings(db_path / "api")


if __name__ == "__main__":
    load_dotenv()
    tyro.cli(main)
