import os

from dotenv import load_dotenv
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_core.documents import Document
from langchain_core.output_parsers import CommaSeparatedListOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from doc_database.embedding import EmbeddingManager


class ConversationalRetrievalAgent:
    def __init__(
        self,
        document_embedding_manager: EmbeddingManager,
        api_embedding_manager: EmbeddingManager,
        temperature: float = 0.5,
    ):
        self.document_embedding_manager = document_embedding_manager
        self.api_embedding_manager = api_embedding_manager
        self.llm = ChatOpenAI(temperature=temperature)
        self.chat_history = []

    def create_function_retrieval_prompt(self) -> ChatPromptTemplate:
        dummy_parser = CommaSeparatedListOutputParser()
        sysmtem_prompt = (
            "You are an expert in the field of carla "
            "and are given a context extracted "
            "from the carla documentation. Please provide "
            "a list of functions that is required and should "
            f"be search for the usage. {dummy_parser.get_format_instructions()}"
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", sysmtem_prompt),
                ("human", "{context}"),
            ]
        )
        return prompt

    def setup_function_retreival_bot(self) -> Runnable:
        retriever = self.document_embedding_manager.vectordb.as_retriever(search_kwargs={"k": 4})
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
        self.api_retriever = self.api_embedding_manager.vectordb.as_retriever(search_kwargs={"k": 4})
        self.bot = self.setup_function_retreival_bot()

    def __call__(self, query: str) -> str:
        def stack_output(data: list[list[Document]]):
            return "\n\n".join([doc.page_content for docs in data for doc in docs])

        return stack_output(self.api_retriever.batch(self.bot.invoke({"input": query})))

    def test_fetch_from_db(self, query: str, save_folder: str = "test_fetch"):
        os.makedirs(save_folder, exist_ok=True)
        retriever = self.document_embedding_manager.vectordb.as_retriever(search_kwargs={"k": 4})
        relevant_docs = retriever.invoke(query)
        for i, doc in enumerate(relevant_docs, 1):
            with open(os.path.join(save_folder, f"doc_{i}.md"), "w") as f:
                f.write(doc.page_content)


if __name__ == "__main__":
    load_dotenv()
    document_embedding_manager = EmbeddingManager(persist_directory="db/documents", auto_load=True)
    api_embedding_manager = EmbeddingManager(persist_directory="db/api", auto_load=True)
    agent = ConversationalRetrievalAgent(
        document_embedding_manager,
        api_embedding_manager,
    )
    agent.setup_bot()
    query = input("Enter a question: ")
    print(agent(query))
