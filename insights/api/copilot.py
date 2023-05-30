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
from insights.utils import DataSource, Table, get_data_source_dialect


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
                embedding_function=OpenAIEmbeddings(openai_api_key=OpenAI.get_key()),
            )

        return self._vector_store

    def ingest_schema(self, reset=False):
        schema = self.get_schema()
        schema = self.skip_ingested_tables(schema)

        if not schema and not reset:
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

        tables = Table.get_all(
            filters={
                "data_source": self.data_source,
                "is_query_based": 0,
                "hidden": 0,
            },
            fields=["name", "table", "modified"],
        )

        data = []
        doc = DataSource.get(self.data_source)
        for table in tables:
            query = f"SELECT * FROM `{table.table}` LIMIT 5"
            try:
                results = doc.db.execute_query(query, return_columns=True)
            except BaseException:
                continue

            id = self.get_id_for_table(table)
            text = self.get_text_for_table(table, results)
            metadata = {}
            data.append({"id": id, "text": text, "metadata": metadata})

        return data

    def get_id_for_table(self, table):
        """Returns a unique hash generated from the table name and modified date."""
        name = table.get("name")
        modified = table.get("modified")
        return hashlib.sha256(f"{name}{modified}".encode("utf-8")).hexdigest()

    def get_text_for_table(self, table, results):
        """
        Returns human-readable text to describe the table and columns along with 5 sample rows.
        Example:
            Table: tabUser
            Data: name, email, creation, modified
                  John Doe, john@doe.com, 2021-01-01, 2021-01-01
        """
        ret = f"Table: {table.get('table')}\nData: "
        cols = [col.label for col in results[0]]
        ret += ", ".join(cols)
        for row in results[1:]:
            ret += "\n      "
            ret += ", ".join(str(col)[:20] for col in row)
        return ret

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

    def find_relevant_tables(self, query, k=5):
        docs = self.vector_store.similarity_search(query, k)
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
You are a data analysis expert called BI_GPT. Your job is to analyze business data by writing SQL queries. You are expert in writing {dialect} SQL queries. Given a question and schema of the database, you can figure out the best possible SQL query that will gain insights from the database.

Before answering any user's question, always follow these instructions:
About database schema:
- DO NOT make any assumptions about the tables and columns in the database.
- If you don't have enough information, you **MUST** say that you don't have enough information.

About writing SQL queries:
- The user's database is a {dialect} database. So, you should write {dialect} SQL queries.
- DO NOT write any other type of query. write only SELECT queries.
- 90% of the time, users will expect a SELECT query with GROUP BY clauses.
- ALWAYS add a LIMIT clause to the query. The limit should be {limit}.

About answer format:
- DO NOT add any explanation to the answer.
- ALWAYS return the answer in the following format:
    1. <your interpretation of the user's question> eg. User wants to know the total sales for each customer.
    2. <list the relevant tables being used in the query> eg. Using `table1` and `table2`
    3. <the SQL query that answers the user's question in markdown format>
    eg.
        ```sql
        SELECT ...
        ```

STRICTLY follow the each and every instruction above. If you don't, you will be banned from the system.

{suffix}
"""
TOOLS_INSTRUCTIONS = """You have access to following tools:"""
SCHEMA_INSTRUCTIONS = """Database has the following tables:\n\n{schema}"""


class SQLCopilot:
    def __init__(
        self,
        data_source,
        verbose=False,
        history=None,
    ):
        self.data_source = data_source
        self.verbose = verbose
        self.history = history or []
        self.max_query_limit = 20
        self.prepare_schema()

    def prepare_schema(self):
        self.schema_store = SchemaStore(
            data_source=self.data_source,
            verbose=self.verbose,
        )
        self.database_schema = self.schema_store.get_schema()
        if not self.database_schema:
            raise frappe.ValidationError(
                "No tables found in the database. Please make sure the data source is synced."
            )

    def ask(self, question, validate=True):
        messages = self.prepare_messages(question)
        tokens = count_token([m.content for m in messages])
        self.verbose and print(f"Consuming {tokens} tokens")
        self.verbose and print(f"\n\nUser: {question}")
        if not validate:
            reply = OpenAI.get_chatgpt()(messages)
            messages.append(AIMessage(content=reply.content))
            self.history.append({"role": "assistant", "message": reply.content})
            return reply.content

        iteration, max_iterations = 0, 3
        final_answer = None
        while not final_answer:
            reply = OpenAI.get_chatgpt()(messages)
            messages.append(AIMessage(content=reply.content))
            self.verbose and print(f"\n\nCopilot: {reply.content}")
            validation_error = self.validate_answer(reply.content)
            if not validate or not validation_error or iteration >= max_iterations:
                final_answer = reply.content
                break
            iteration += 1
            messages.append(HumanMessage(content=validation_error))
            self.verbose and print(f"\n\nUser: {validation_error}")

        self.history.append({"role": "assistant", "message": final_answer})
        return reply.content

    def prepare_messages(self, question):
        messages = []
        relevant_tables = self.schema_store.find_relevant_tables(question, k=3)
        system_message = self.get_system_message(relevant_tables)
        messages.append(system_message)
        messages += self.get_history_messages()
        messages.append(HumanMessage(content=question))
        self.history.append({"role": "user", "message": question})
        return messages

    def get_system_message(self, relevant_tables):
        dialect = get_data_source_dialect(self.data_source)
        system_message = SQL_GEN_INSTRUCTIONS.format(
            dialect=dialect,
            limit=self.max_query_limit,
            suffix=SCHEMA_INSTRUCTIONS.format(schema=relevant_tables),
        )
        return SystemMessage(content=system_message)

    def get_history_messages(self):
        if not self.history:
            return []

        messages = []
        for message in self.history:
            if message["role"] == "assistant":
                messages.append(AIMessage(content=message["message"]))
            else:
                messages.append(HumanMessage(content=message["message"]))
        return messages

    def validate_answer(self, answer):
        """
        Returns the error message if validation fails.
        Returns None if validation succeeds.

        Validates the answer by executing the query and checking the results.

        If execution fails, returns the error message
        If execution succeeds and there are no results, returns a message saying that there are no results
        If execution succeeds and there are results, returns None
        """

        try:
            query = self.get_query_from_answer(answer)
        except BaseException as e:
            return f"It threw an error. Error: {e}. Look for corrections and try again."

        doc = DataSource.get(self.data_source)
        try:
            limited_query = add_limit_to_sql(query, limit=self.max_query_limit)
            results = doc.db.execute_query(limited_query)
            if not results:
                return "The query didn't return any results. Look for corrections and try again."

            self.verbose and print(f"Query executed successfully. Results: {results}")
            return None
        except BaseException as e:
            return f"It threw an error. Error: {e}. Look for corrections and try again."

    def get_query_from_answer(self, answer):
        ans_lower = answer.lower()
        if "select" not in ans_lower and "from" not in ans_lower:
            raise frappe.ValidationError("Answer doesn't contain a select query")

        # try to manually extract the query from the answer
        try:
            query = answer.split("```sql")[1].split("```")[0]
            if query.lower().startswith("select"):
                return query
        except BaseException:
            self.verbose and print("Manual extraction failed")

        chatgpt = OpenAI.get_chatgpt()
        query = chatgpt(
            [
                SystemMessage(
                    content="Extract the sql query from the given text. "
                    "Reply with ONLY the sql query and NOTHING else. "
                    "DO NOT use any kind of formatting."
                ),
                HumanMessage(content=answer),
            ]
        )
        self.verbose and print(f"Extracted query: {query.content}")
        if "select" not in ans_lower and "from" not in ans_lower:
            raise frappe.ValidationError("Answer doesn't contain a select query")
        return query.content
