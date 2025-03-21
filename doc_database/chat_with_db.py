import os

from dotenv import load_dotenv
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_core.output_parsers import CommaSeparatedListOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from doc_database import APIDocumentManager, DocumentManager


class ConversationalRetrievalAgent:
    def __init__(
        self,
        document_manager: DocumentManager,
        api_manager: APIDocumentManager,
        temperature: float = 0.5,
    ):
        self.document_manager = document_manager
        self.api_manager = api_manager
        self.llm = ChatOpenAI(temperature=temperature)
        self.chat_history = []

    def create_function_retrieval_prompt(self) -> ChatPromptTemplate:
        dummy_parser = CommaSeparatedListOutputParser()
        sysmtem_prompt = (
            "You are an expert in the field of carla "
            "and are given a context extracted "
            "from the carla documentation. Please provide "
            "a list of carla functions that is required (e.g., `carla.Waypoint`) "
            "to answer the question. "
            f"{dummy_parser.get_format_instructions()}"
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", sysmtem_prompt),
                ("human", "{context}"),
            ]
        )
        return prompt

    def setup_function_retreival_bot(self) -> Runnable:
        retriever = self.document_manager.embedding.vectordb.as_retriever(search_kwargs={"k": 8})
        question_answer_chain = create_stuff_documents_chain(
            self.llm,
            self.create_function_retrieval_prompt(),
            output_parser=CommaSeparatedListOutputParser(),
        )
        return create_retrieval_chain(retriever, question_answer_chain)

    def create_chat_prompt(self) -> ChatPromptTemplate:
        system_prompt = (
            "You are an assistant for writing code to create a scene within carla. "
            "Use the following pieces of retrieved context to answer "
            "the question. If you don't know the answer, say that you "
            "don't know. The output should be a valid python code only without any other text."
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{input}"),
            ]
        )
        return prompt

    def setup_bot(self):
        self.api_retriever = self.api_manager.embedding.vectordb.as_retriever(search_kwargs={"k": 4})
        self.bot = self.setup_function_retreival_bot()

    def __call__(self, query: str) -> str:
        def stack_and_fetch_output(data: list[str]):
            return "\n\n".join(
                [
                    f"## {func}\n{self.api_manager.doc_map[func]}"
                    for func in data
                    if func in self.api_manager.doc_map
                ]
            )

        api_for_usage = self.bot.invoke({"input": query})["answer"]
        print(api_for_usage)
        return stack_and_fetch_output(api_for_usage)

    def test_fetch_from_db(self, query: str, save_folder: str = "test_fetch"):
        os.makedirs(save_folder, exist_ok=True)
        retriever = self.document_manager.embedding.vectordb.as_retriever(search_kwargs={"k": 4})
        relevant_docs = retriever.invoke(query)
        for i, doc in enumerate(relevant_docs, 1):
            with open(os.path.join(save_folder, f"doc_{i}.md"), "w") as f:
                f.write(doc.page_content)


if __name__ == "__main__":
    load_dotenv()
    document_manager = DocumentManager(directory_path="carla_docs", glob_pattern="**/*.md")
    document_manager.load_embeddings(persist_directory="db/documents")
    api_manager = APIDocumentManager(api_file="python_api.md")
    api_manager.load_embeddings(persist_directory="db/api")
    api_manager.load_doc_map()
    agent = ConversationalRetrievalAgent(
        document_manager,
        api_manager,
    )
    agent.setup_bot()
    query = input("Enter a question: ")
    agent(query)
