# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from openai import OpenAI

from insights.insights.doctype.insights_data_source.sources.utils import (
    add_limit_to_sql,
)
from insights.utils import InsightsDataSource, get_data_source_dialect

from .schema_store import SchemaStore
from .utils import DEFAULT_MODEL, get_function_definitions, get_message

SQL_GEN_INSTRUCTIONS = """
You are expert in writing {dialect} SQL queries. Given a question and schema of the database,
you can figure out the best possible SQL query that will help business users answer their questions.

Before answering any question, always follow these instructions:
About database schema:
- DO NOT make any assumptions about the tables and columns in the database.
- Use the tool `get_relevant_tables` to find the tables that are relevant to the question.
- Still if you lack information, you **MUST** ask the user to provide more information.

About writing SQL queries:
- The user's database is a {dialect} database. So, you should write {dialect} SQL queries.
- DO NOT write any other type of query. write only SELECT queries.
- 90% of the time, users will a query with GROUP BY clause.
- ALWAYS add a LIMIT clause to the query. The max limit can be 1000.

About answer format:
- DO NOT explain the generated query.
- Use markdown formatting to format the answer.

STRICTLY follow the each and every instruction above.
"""


class SQLCopilot:
    def __init__(
        self,
        data_source,
        chat_history=None,
        verbose=False,
    ):
        self.data_source = data_source
        self.message_log = chat_history or []
        self.verbose = verbose
        self._function_messages = []
        self.client = OpenAI(
            api_key=frappe.conf.get("openai_api_key"),
        )
        self.prepare_schema()

    def prepare_schema(self):
        self.schema_store = SchemaStore(data_source=self.data_source, verbose=self.verbose)
        self.database_schema = self.schema_store.get_schema()
        if not self.database_schema:
            raise frappe.ValidationError(
                "No tables found in the database. Please make sure the data source is synced."
            )

    def ask(self, question, stream=False):
        usage = 0
        max_iterations = 3
        messages = self.prepare_messages(question)

        for iteration in range(max_iterations):
            self.verbose and print(messages)
            is_final_iteration = iteration == max_iterations - 1
            response = self.client.chat.completions.create(
                model=DEFAULT_MODEL,
                messages=messages,
                temperature=0.1,
                tools=get_function_definitions(),
                tool_choice="none" if is_final_iteration else "auto",
            )
            usage += response.usage.total_tokens
            if not self.is_function_call(response) or is_final_iteration:
                break
            self.message_log = self.handle_function_and_add_context(response)

        final_response = response.choices[0].message.content
        self.message_log.append({"role": "assistant", "message": final_response})
        self.verbose and print("Usage:", usage, "Cost:", usage / 1000 * 0.0013)
        return final_response

    def prepare_messages(self, question):
        messages = []
        messages = self.add_system_instructions(messages)
        messages = self.add_previous_messages(messages)
        messages = self.add_user_prompt(messages, question)
        return messages

    def add_system_instructions(self, messages):
        dialect = get_data_source_dialect(self.data_source)
        system_prompt = SQL_GEN_INSTRUCTIONS.format(dialect=dialect)
        messages.append({"role": "system", "content": system_prompt})
        return messages

    def add_user_prompt(self, messages, prompt):
        messages.append({"role": "user", "content": prompt})
        return messages

    def add_previous_messages(self, messages):
        if not self.message_log:
            return messages
        for message in self.message_log:
            messages.append(get_message(message))
        return messages

    def is_function_call(self, response):
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        return bool(tool_calls)

    def handle_function_and_add_context(self, response):
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls
        self.message_log.append(response_message)
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = frappe.parse_json(tool_call.function.arguments)
            function_response = self.run_function(function_name, function_args)
            self.message_log.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": function_name,
                    "content": function_response,
                }
            )
        return self.message_log

    def run_function(self, function_name, arguments):
        def _get_relevant_tables(question):
            tables = self.schema_store.find_relevant_tables(question)
            return "Relevant tables:\n\n" + tables

        def validate_sql_query(query):
            if "SELECT" not in query.upper():
                return "The query is not a SELECT query. Try writing a SELECT query."

            source = InsightsDataSource.get_doc(self.data_source)
            limited_query = add_limit_to_sql(query, limit=10)
            try:
                source._db.execute_query(limited_query)
                self.learn_query(query)
                return "The query is valid."
            except BaseException as e:
                return f"ERROR: {e}. Look for corrections and try again."

        try:
            if function_name == "get_relevant_tables":
                return _get_relevant_tables(**arguments)
            elif function_name == "validate_sql_query":
                return validate_sql_query(**arguments)
        except BaseException as e:
            return f"ERROR: {e}. Look for corrections and try again."

    def learn_query(self, query):
        # generate a question from the query
        # store the pair of question and query in the vector store
        # use the vector store to find the relevant queries for a question
        pass
