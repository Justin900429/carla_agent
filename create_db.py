from pathlib import Path

import tyro
from dotenv import load_dotenv

from doc_database import APIDocumentManager, DocumentManager, EmbeddingManager


def main(directory_path: Path, db_path: Path):
    # Create embeddings for documents
    doc_manager = DocumentManager(directory_path)
    doc_manager.load_documents()
    doc_manager.split_documents()
    EmbeddingManager(
        doc_manager.all_sections,
        persist_directory=db_path / "documents",
        auto_load=True,
    )

    # Create embeddings for API
    api_manager = APIDocumentManager(directory_path / "python_api.md")
    api_manager.load_api_document()
    api_manager.get_api_key()
    EmbeddingManager(
        api_manager.all_sections,
        persist_directory=db_path / "api",
        auto_load=True,
    )


if __name__ == "__main__":
    load_dotenv()
    tyro.cli(main)
