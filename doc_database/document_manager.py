from typing import Union

import html2text
import mistletoe
from langchain.schema import Document
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader


def convert_to_plain(section: Union[str, Document]) -> str:
    if isinstance(section, Document):
        section = section.page_content
    plain_text = html2text.html2text(mistletoe.markdown(section))
    return plain_text


class DocumentManager:
    def __init__(self, directory_path: str = "carla_docs", glob_pattern: str = "**/*.md"):
        self.directory_path = directory_path
        self.glob_pattern = glob_pattern
        self.documents = []
        self.all_sections = []

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


class APIDocumentManager:
    def __init__(self, api_file: str):
        self.api_file = api_file
        self.document = None
        self.all_sections = []

    def load_api_document(self):
        loader = TextLoader(self.api_file)
        self.document = loader.load()

    def get_api_key(self):
        headers_to_split_on = [("##", "Header 2")]
        text_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on, strip_headers=False
        )
        sections = text_splitter.split_text(convert_to_plain(self.document[0].page_content))
        self.all_sections.extend(sections)
        self.all_sections.pop(0)
