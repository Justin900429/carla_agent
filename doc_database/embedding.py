import os
from typing import Optional
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document


class EmbeddingManager:
    def __init__(
        self,
        all_sections: Optional[list[list[Document]]] = None,
        persist_directory: str = "db",
    ):
        self.all_sections = all_sections
        self.persist_directory = persist_directory
        self.vectordb = None

    def create_and_persist_embeddings(self):
        embedding = OpenAIEmbeddings()
        self.vectordb = Chroma.from_documents(
            documents=self.all_sections,
            embedding=embedding,
            persist_directory=self.persist_directory,
        )
        self.vectordb.persist()

    def load_embeddings(self):
        if not os.path.exists(self.persist_directory):
            raise FileNotFoundError(
                f"Database not found in {self.persist_directory}, please create the database first"
            )
        embedding = OpenAIEmbeddings()
        self.vectordb = Chroma(
            embedding_function=embedding,
            persist_directory=self.persist_directory,
        )
