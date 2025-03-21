import pickle
from typing import Union

import html2text
import mistletoe
from langchain.schema import Document
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader

from doc_database.embedding import EmbeddingManager


def convert_to_plain(section: Union[str, Document]) -> str:
    if isinstance(section, Document):
        section = section.page_content
    plain_text = html2text.html2text(mistletoe.markdown(section))
    return plain_text


class Manager:
    def __init__(self):
        self.all_sections = []
        self.embedding = None

    def load_embeddings(
        self,
        persist_directory: str,
        use_embedding: str = "openai",
    ):
        self.embedding = EmbeddingManager(
            persist_directory=persist_directory,
            use_embedding=use_embedding,
            auto_load=True,
        )

    def create_embeddings(
        self,
        persist_directory: str,
        use_embedding: str = "openai",
    ):
        self.embedding = EmbeddingManager(
            self.all_sections,
            persist_directory=persist_directory,
            use_embedding=use_embedding,
            auto_load=True,
        )


class DocumentManager(Manager):
    def __init__(
        self,
        directory_path: str = "carla_docs",
        glob_pattern: str = "**/*.md",
    ):
        super().__init__()
        self.directory_path = directory_path
        self.glob_pattern = glob_pattern
        self.documents = []

    def load_documents(self):
        loader = DirectoryLoader(
            self.directory_path,
            glob=self.glob_pattern,
            exclude=["python_api.md"],
            show_progress=True,
            loader_cls=TextLoader,
        )
        self.documents = loader.load()

    def split_documents(self):
        headers_to_split_on = [("#", "Header 1"), ("##", "Header 2")]
        text_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        for doc in self.documents:
            assert "python_api.md" not in doc.metadata["source"]
            page_content = convert_to_plain(doc.page_content)
            sections = text_splitter.split_text(page_content)
            self.all_sections.extend(sections)


class APIDocumentManager(Manager):
    def __init__(self, api_file: str):
        super().__init__()
        self.api_file = api_file
        self.document = None
        self.doc_map = {}

    def load_doc_map(self, map_path: str = "doc_map.pkl"):
        with open(map_path, "rb") as f:
            self.doc_map = pickle.load(f)

    def load_api_document(self):
        loader = TextLoader(self.api_file)
        self.document = loader.load()

    def get_api_key(self, map_path: str = "doc_map.pkl"):
        plain_document = convert_to_plain(self.document[0].page_content)

        headers_to_split_on = [("##", "H2")]
        text_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        doc_searching = text_splitter.split_text(plain_document)

        for section in doc_searching:
            if "H2" in section.metadata:
                self.doc_map[section.metadata["H2"]] = section.page_content

        headers_for_embeddings = [("##", "H2"), ("###", "H3"), ("####", "H4")]
        text_splitter_for_embeddings = MarkdownHeaderTextSplitter(headers_to_split_on=headers_for_embeddings)
        all_sections = text_splitter_for_embeddings.split_text(plain_document)
        all_sections = list(
            filter(
                lambda x: ("H2" in x.metadata) and ("H3" not in x.metadata) and ("H4" not in x.metadata),
                all_sections,
            )
        )
        self.all_sections = all_sections

        for section in self.all_sections:
            assert section.metadata["H2"] in self.doc_map

        with open(map_path, "wb") as f:
            pickle.dump(self.doc_map, f)
