from doc_database import DocumentManager, EmbeddingManager
import tyro
from pathlib import Path
from dotenv import load_dotenv


def main(directory_path: Path):
    doc_manager = DocumentManager(directory_path)
    doc_manager.load_documents()
    doc_manager.split_documents()

    embed_manager = EmbeddingManager(doc_manager.all_sections)
    embed_manager.create_and_persist_embeddings()


if __name__ == "__main__":
    load_dotenv()
    tyro.cli(main)
