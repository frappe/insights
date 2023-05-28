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
from insights.insights.doctype.insights_data_source.sources.utils import (
    add_limit_to_sql,
)
from insights.utils import DataSource, get_data_source_dialect, get_data_source_schema


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


OPENAI_MODEL = "gpt-3.5-turbo"


class OpenAI:
    @staticmethod
    def get_key():
        return frappe.conf.get("openai_api_key")

    @staticmethod
    def get_chatgpt():
        return ChatOpenAI(
            openai_api_key=OpenAI.get_key(),
            model_name=OPENAI_MODEL,
            temperature=0.0,
        )


def count_token(messages, model=OPENAI_MODEL):
    if not isinstance(messages, list):
        messages = [messages]
    return sum((len(tiktoken.encoding_for_model(model).encode(m)) for m in messages))


class SchemaStore:
    def __init__(self, data_source, verbose=False):
        self.data_source = data_source
        self.collection_name = frappe.scrub(data_source)
        self.vector_store_path = frappe.get_site_path(
            "private",
            "files",
            "vector_stores",
            "schema_store",
        )
        self.verbose = verbose

    @property
    def vector_store(self):
        if not hasattr(self, "_vector_store"):
            self.verbose and print("Loading vector store from disk")
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
            self.verbose and print("No new data to ingest")
            return

        self.verbose and print(f"Ingesting {len(schema)} rows of data")

        ids = [d["id"] for d in schema]
        texts = [d["text"] for d in schema]
        metadata = [d["metadata"] for d in schema]

        # $0.0004 / 1K tokens
        tokens_consumed = count_token(texts, model="text-embedding-ada-002")
        usage = tokens_consumed / 1000 * 0.0004
        self.verbose and print(f"This will consume {usage} USD")

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
You are a data analysis assistant called BI_GPT. Your job is to help users analyze their business data using SQL queries. You are expert in writing {dialect} SQL queries to find insights from business data. Given a question and schema of the database, you should be able to figure out the best possible SQL query that will help the user gain insights from their database.

Before answering any user's question, always follow these instructions:
About database schema:
- DO NOT make any assumptions about the tables and columns in the database.
- If you don't have enough information about the schema, you can use the tools provided to find the relevant tables and columns.
- Even then, if you don't have enough information, you should say that you don't have enough information.

About writing SQL queries:
- The user's database is a {dialect} database. So, you should write {dialect} SQL queries.
- DO NOT write any other type of query. write only SELECT queries.
- 90% of the time, users will expect a SELECT query with GROUP BY clauses.
- ALWAYS add a LIMIT clause to the query. The limit should be {limit}.

About verbosity:
- User is smart enough to understand the answer.
- DO NOT use any more words than necessary while answering. Each word costs money. 
- Make sure to use markdown syntax for easy readability.

STRICTLY follow the each and every instruction above. If you don't, you will be banned from the system.

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
    max_query_limit = 20

    def __init__(
        self, data_source, allow_executions=False, verbose=False, with_tools=False
    ):
        self.data_source = data_source
        self.verbose = verbose
        self.allow_executions = allow_executions
        self.with_tools = with_tools or allow_executions
        self.schema_store = SchemaStore(
            data_source=self.data_source,
            verbose=self.verbose,
        )
        self.database_schema = self.schema_store.get_schema()
        if not self.database_schema:
            raise frappe.ValidationError(
                "No tables found in the database. Please make sure the data source is synced."
            )
        self.database_schema_text = "\n".join([d["text"] for d in self.database_schema])

    def ask(self, question, history=None):
        self.prepare_tools()
        self.prepare_memory(history)
        self.prepare_copilot()
        return self._ask(question)

    def has_large_schema(self):
        tokens = count_token(self.database_schema_text)
        return tokens > self.max_schema_tokens

    def prepare_tools(self):
        schema_retrieval_tool = self.schema_store.make_agent_tool()
        execute_query_tool = self.make_execute_query_tool()
        self.tools = []
        if self.has_large_schema():
            self.tools.append(schema_retrieval_tool)
        if self.allow_executions:
            self.tools.append(execute_query_tool)

    def prepare_memory(self, history):
        msg_count = 5
        self.memory = ConversationBufferWindowMemory(
            k=msg_count,  # no. of messages to remember
            memory_key="chat_history",
            return_messages=True,
        )
        if not history or not isinstance(history, list):
            return

        self.verbose and print(f"Using history: {len(history)} messages")
        for message in history[-msg_count:]:
            if message["role"] == "assistant":
                self.memory.chat_memory.add_ai_message(message["message"])
            else:
                self.memory.chat_memory.add_user_message(message["message"])

    def prepare_copilot(self):
        if self.with_tools or self.has_large_schema():
            self.verbose and print("Using schema retrieval tool")
            self.initialize_agent_with_tools()
            return

        self.verbose and print("Using default agent")
        self.initialize_default_agent()

    def initialize_default_agent(self):
        messages = []
        messages.append(SystemMessage(content=self.get_system_message()))
        messages += self.memory.chat_memory.messages

        def _ask(question):
            messages.append(HumanMessage(content=question))
            tokens = count_token([m.content for m in messages])
            self.verbose and print(f"Consuming {tokens} tokens")
            reply = OpenAI.get_chatgpt()(messages)
            return reply.content

        self._ask = _ask

    def initialize_agent_with_tools(self):
        agent = initialize_agent(
            agent="conversational-react-description",
            llm=OpenAI.get_chatgpt(),
            verbose=True,
            max_iterations=3,
            memory=self.memory,
            tools=self.tools or [],
            early_stopping_method="generate",
            agent_kwargs={
                "prefix": self.get_system_message(),
                "ai_prefix": "BI_GPT",
            },
        )
        self._ask = agent.run

    def get_system_message(self):
        dialect = get_data_source_dialect(self.data_source)
        has_large_schema = self.has_large_schema()
        show_schema = not has_large_schema
        show_tools = self.with_tools or has_large_schema
        instructions = ""
        if show_schema:
            # if schema is small, show the schema in the instructions
            instructions += SCHEMA_INSTRUCTIONS.format(schema=self.database_schema_text)
            instructions += "\n\n"
        if show_tools:
            # if schema is large or tools are enabled, show the tools in the instructions
            instructions += TOOLS_INSTRUCTIONS
            instructions += "\n\n"
        system_message = SQL_GEN_INSTRUCTIONS.format(
            dialect=dialect, suffix=instructions, limit=self.max_query_limit
        )
        print(system_message)
        return system_message

    def make_execute_query_tool(self):
        def _execute_query(args):
            if not self.allow_executions:
                return "Sorry, I am not allowed to execute queries."

            try:
                query = frappe.parse_json(args).get("sql")
            except BaseException:
                return "Incorrect input. It should be a valid JSON with 'sql' key and sql query as value"

            doc = DataSource.get(self.data_source)
            try:
                limited_query = add_limit_to_sql(query, limit=self.max_query_limit)
                results = doc.db.execute_query(limited_query)
                return frappe.as_json(results)
            except BaseException as e:
                return f"""
                    Failed to execute query. BI_GPT can use the error message to debug the query and try again.
                    Error: {e}
                """

        return Tool(
            func=_execute_query,
            name="Execute Query",
            description=(
                "A tool useful for executing SQL queries. "
                "If user explicitly asks for a sql query to be executed, this tool **should** be used to execute the query."
                "Input Format: <Valid JSON with 'sql' key and sql query as value> eg. {{'sql': 'SELECT 1'}}"
            ),
        )
