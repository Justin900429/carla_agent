from langchain_openai import ChatOpenAI
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.retrieval import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from doc_database.embedding import EmbeddingManager
from langchain_core.messages import AIMessage, HumanMessage
from dotenv import load_dotenv


class ConversationalRetrievalAgent:
    def __init__(self, embedding_manager: EmbeddingManager, temperature: float = 0.5):
        self.embedding_manager = embedding_manager
        self.llm = ChatOpenAI(temperature=temperature)
        self.chat_history = []

    def get_chat_history(self, inputs):
        res = []
        for human, ai in inputs:
            res.append(f"Human:{human}\nAI:{ai}")
        return "\n".join(res)

    def create_history_aware_retriever_prompt(self):
        contextualize_q_system_prompt = (
            "Given a chat history and the latest user question "
            "which might reference context in the chat history, "
            "formulate a standalone question which can be understood "
            "without the chat history. Do NOT answer the question, "
            "just reformulate it if needed and otherwise return it as is."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", contextualize_q_system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )
        return prompt

    def create_chat_prompt(self):
        system_prompt = system_prompt = (
            "You are an assistant for writing code to create a scene within carla. "
            "Use the following pieces of retrieved context to answer "
            "the question. If you don't know the answer, say that you "
            "don't know. The output should be a valid python code only without any other text."
            "\n\n"
            "{context}"
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder("chat_history"),
                ("human", "{input}"),
            ]
        )

        return prompt

    def setup_bot(self):
        retriever = self.embedding_manager.vectordb.as_retriever(search_kwargs={"k": 4})
        history_aware_retriever = create_history_aware_retriever(
            self.llm, retriever, self.create_history_aware_retriever_prompt()
        )
        question_answer_chain = create_stuff_documents_chain(self.llm, self.create_chat_prompt())
        self.bot = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    def ask_question(self, question):
        result = self.bot.invoke({"input": question, "chat_history": self.chat_history})
        self.chat_history.append(
            [
                HumanMessage(content=question),
                AIMessage(content=result["answer"]),
            ]
        )
        return result["answer"]


if __name__ == "__main__":
    load_dotenv()
    embedding_manager = EmbeddingManager(persist_directory="db")
    embedding_manager.load_embeddings()
    agent = ConversationalRetrievalAgent(embedding_manager)
    agent.setup_bot()
    while True:
        query = input("Enter a question: ")
        answer = agent.ask_question(query)
        print(answer)
