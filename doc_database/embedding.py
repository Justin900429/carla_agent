import os
from typing import Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import OpenAIEmbeddings

EMBEDDING_MAP = {
    "google": (GoogleGenerativeAIEmbeddings, {"model": "models/gemini-embedding-exp-03-07"}),
    "openai": (OpenAIEmbeddings, {"model": "text-embedding-3-small"}),
}


class EmbeddingManager:
    def __init__(
        self,
        all_sections: Optional[list[list[Document]]] = None,
        persist_directory: str = "db",
        use_embedding: str = "openai",
        auto_load: bool = False,
    ):
        self.use_embedding = use_embedding
        self.all_sections = all_sections
        self.persist_directory = str(persist_directory)
        self.vectordb = None

        if auto_load:
            self.load_embeddings()

    def reload_section_and_path(
        self,
        persist_directory: str,
        sections: list[list[Document]],
    ):
        del self.all_sections
        self.persist_directory = persist_directory
        self.all_sections = sections

    def create_and_persist_embeddings(self):
        embedding_cls, embedding_kwargs = EMBEDDING_MAP[self.use_embedding]
        self.vectordb = Chroma.from_documents(
            documents=self.all_sections,
            embedding=embedding_cls(**embedding_kwargs),
            persist_directory=self.persist_directory,
        )

    def load_embeddings(self):
        if not os.path.exists(self.persist_directory):
            try:
                self.create_and_persist_embeddings()
            except Exception as e:
                raise FileNotFoundError(
                    f"Database not found in {self.persist_directory}, please create the database first"
                ) from e
        embedding_cls, embedding_kwargs = EMBEDDING_MAP[self.use_embedding]
        self.vectordb = Chroma(
            embedding_function=embedding_cls(**embedding_kwargs),
            persist_directory=self.persist_directory,
        )
