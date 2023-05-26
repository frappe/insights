# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import hashlib

import frappe
import tiktoken
from langchain.agents import Tool, initialize_agent
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain.vectorstores import Chroma

from insights.decorators import check_role
from insights.utils import get_data_source_dialect, get_data_source_schema


@frappe.whitelist()
@check_role("Insights User")
def create_new_chat():
    empty_chat = frappe.db.exists("Insights Copilot Chat", {"copilot_bot": "Default"})
    if empty_chat:
        return empty_chat

    new_chat = frappe.new_doc("Insights Copilot Chat")
    new_chat.copilot_bot = "Default"
    new_chat.save()
    return new_chat.name


class OpenAI:
    @staticmethod
    def get_key():
        return frappe.conf.get("openai_api_key")

    @staticmethod
    def get_chatgpt():
        return ChatOpenAI(
            openai_api_key=OpenAI.get_key(),
            model_name="gpt-3.5-turbo",
            temperature=0.0,
        )


def count_token(messages, model="gpt-3.5-turbo"):
    if not isinstance(messages, list):
        messages = [messages]
    return sum((len(tiktoken.encoding_for_model(model).encode(m)) for m in messages))


class SchemaStore:
    def __init__(self, data_source, debug=False):
        self.data_source = data_source
        self.collection_name = frappe.scrub(data_source)
        self.vector_store_path = frappe.get_site_path(
            "private",
            "files",
            "vector_stores",
            "schema_store",
        )
        self.debug = debug

    @property
    def vector_store(self):
        if not hasattr(self, "_vector_store"):
            self.debug and print("Loading vector store from disk")
            self._vector_store = Chroma(
                collection_name=self.collection_name,
                persist_directory=self.vector_store_path,
                embedding_function=OpenAIEmbeddings(openai_api_key=self.openai_api_key),
            )

        return self._vector_store

    def ingest_schema(self):
        schema = self.get_schema()
        schema = self.skip_ingested_tables(schema)

        if not schema:
            self.debug and print("No new data to ingest")
            return

        self.debug and print(f"Ingesting {len(schema)} rows of data")

        ids = [d["id"] for d in schema]
        texts = [d["text"] for d in schema]
        metadata = [d["metadata"] for d in schema]

        # $0.0004 / 1K tokens
        tokens_consumed = count_token(texts, model="text-embedding-ada-002")
        usage = tokens_consumed / 1000 * 0.0004
        self.debug and print(f"This will consume {usage} USD")

        self._vector_store = Chroma.from_texts(
            ids=ids,
            texts=texts,
            metadatas=metadata,
            collection_name=self.collection_name,
            persist_directory=self.vector_store_path,
            embedding=OpenAIEmbeddings(openai_api_key=OpenAI.get_key()),
        )
        self._vector_store.persist()

    def get_schema(self):
        """
        Returns a list of dicts with attributes: id, text, metadata.
        - ID: A unique identifier for the Table and its Columns.
        - Text: The Table name and Column names.
        - Metadata: The Table name and the number of rows in the table.
        """

        schema = get_data_source_schema(
            self.data_source,
            is_query_based=0,
            hidden=0,
        )

        # schema is a list of dicts with attributes: name, table, column, type, modified, row_count
        # name and modified can be used to generate the ID.
        # table and column can be used to generate the text.
        # row_count can be used to generate the metadata.

        data = []
        for table in schema:
            id = self.get_id_for_table(table)
            text = self.get_text_for_table(table)
            metadata = self.get_metadata_for_table(table)
            data.append({"id": id, "text": text, "metadata": metadata})

        return data

    def get_id_for_table(self, table):
        """Returns a unique hash generated from the table name and modified date."""
        name = table["name"]
        modified = table["modified"]
        return hashlib.sha256(f"{name}{modified}".encode("utf-8")).hexdigest()

    def get_text_for_table(self, table):
        """
        Returns human-readable text to describe the table and columns.
        Example: The database table `tabUser` has columns `name(String)`, `email(String)`, `creation(Date)`, `modified(Date)`.
        """
        table_name, columns = table["table"], table["columns"]
        column_names = [column["column"] for column in columns]
        column_types = [column["type"] for column in columns]
        column_descriptions = [
            f"{name}({type})" for name, type in zip(column_names, column_types)
        ]
        column_descriptions = ", ".join(column_descriptions)
        return f"The database table `{table_name}` has columns `{column_descriptions}`."

    def get_metadata_for_table(self, table):
        """Returns the table name and the number of rows in the table."""
        return {"table_name": table["table"], "row_count": table["row_count"]}

    def skip_ingested_tables(self, data):
        """Removes the tables that are already ingested."""
        new_ids = [row["id"] for row in data]
        results = self.vector_store._collection.get(ids=new_ids)
        if not results["ids"]:
            return data
        return [row for row in data if row["id"] not in results["ids"]]

    def find_relevant_tables(self, query):
        docs = self.vector_store.similarity_search(query, k=5)
        return "\n\n".join(doc.page_content for doc in docs)

    def make_agent_tool(self):
        def _find_relevant_tables(query):
            return self.find_relevant_tables(query)

        return Tool(
            func=_find_relevant_tables,
            name="Find Relevant Tables",
            description=(
                "A tool useful for finding the tables that are relevant to generate a sql query."
                "If user expects a sql query as an answer, this tool **should** be used to find the relevant tables first. "
                "Usage Eg.: `Show me relevant tables to <user question>?`"
            ),
        )


SQL_GEN_INSTRUCTIONS = """
You are sqlGPT, a dedicated AI assistant for generating SQL queries. Specializing in {dialect}, sqlGPT is designed to create precise, syntactically correct SQL queries.

sqlGPT does not assumes any prior knowledge of the database schema. Instead, it uses a special action/tool to get the list of tables and columns, then with this information, it generate the SQL queries. In case of ambiguity, you can ask for clarification.

Make sure to follow these rules:
- STRICTLY generate SELECT queries. Only!
- Remember to find out the relevant tables first before generating the SQL query.
- 90% of the time, users will expect a SELECT query as an answer.
- In case user asks for an explanation, keep it short and simple.
- In case you need to explain the answer, make sure to use markdown syntax for easy readability.

Remember, sqlGPT is specifically designed for {dialect} databases.

{suffix}
"""
TOOLS_INSTRUCTIONS = """You have access to the following tools:"""
SCHEMA_INSTRUCTIONS = (
    """Use **ONLY** the following tables and columns in your queries:\n\n{schema}"""
)


class SQLCopilot:
    tools = None
    memory = None
    agent = None
    schema_store = None
    max_schema_tokens = 1000

    def __init__(self, data_source, debug=False, with_tools=False):
        self.data_source = data_source
        self.with_tools = with_tools
        self.debug = debug
        self.schema_store = SchemaStore(
            data_source=self.data_source,
            debug=self.debug,
        )

    def ask(self, question, history=None):
        self.prepare_tools()
        self.prepare_memory(history)
        self.prepare_copilot()
        return self._ask(question)

    def has_small_schema(self):
        self.schema = self.schema_store.get_schema()
        if not self.schema:
            return True
        self.schema_text = "\n\n".join([d["text"] for d in self.schema])
        tokens = count_token(self.schema_text)
        return tokens < self.max_schema_tokens

    def prepare_tools(self):
        self.tools = [self.schema_store.make_agent_tool()]

    def prepare_memory(self, history):
        msg_count = 5
        self.memory = ConversationBufferWindowMemory(
            k=msg_count,  # no. of messages to remember
            memory_key="chat_history",
            return_messages=True,
        )
        if not history or not isinstance(history, list):
            return

        self.debug and print(f"Using history: {len(history)} messages")
        for message in history[-msg_count:]:
            if message["role"] == "assistant":
                self.memory.chat_memory.add_ai_message(message["message"])
            else:
                self.memory.chat_memory.add_user_message(message["message"])

    def prepare_copilot(self):
        if self.with_tools or not self.has_small_schema():
            self.debug and print("Using schema retrieval tool")
            self.initialize_agent_with_tools()
            return

        self.debug and print("Using default agent")
        self.initialize_default_agent()

    def initialize_default_agent(self):
        schema = self.schema_store.get_schema()
        if not schema:
            raise ValueError("No tables found in the database.")

        schema_text = "\n".join([d["text"] for d in schema])
        dialect = get_data_source_dialect(self.data_source)
        system_prompt = SQL_GEN_INSTRUCTIONS.format(
            dialect=dialect, suffix=SCHEMA_INSTRUCTIONS.format(schema=schema_text)
        )

        messages = []
        messages.append(SystemMessage(content=system_prompt))
        messages += self.memory.chat_memory.messages

        def _ask(question):
            messages.append(HumanMessage(content=question))
            tokens = count_token([m.content for m in messages])
            self.debug and print(f"Consuming {tokens} tokens")
            reply = OpenAI.get_chatgpt()(messages)
            return reply.content

        self._ask = _ask

    def initialize_agent_with_tools(self):
        dialect = get_data_source_dialect(self.data_source)
        system_prompt = SQL_GEN_INSTRUCTIONS.format(
            dialect=dialect, suffix=TOOLS_INSTRUCTIONS
        )
        agent = initialize_agent(
            agent="conversational-react-description",
            llm=OpenAI.get_chatgpt(),
            verbose=True,
            max_iterations=3,
            memory=self.memory,
            tools=self.tools or [],
            early_stopping_method="generate",
            agent_kwargs={"prefix": system_prompt},
        )
        self._ask = agent.run
