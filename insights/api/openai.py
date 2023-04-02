# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe.integrations.utils import make_post_request
from frappe.utils.caching import redis_cache

SYSTEM_PROMPT = """
Rules:
    1. I am text to sql conversion bot. I will only respond with SQL queries.
    2. For best practices, I use aliases for tables and columns.
    3. I will only respond with the SQL query with proper aliases. 
    4. I will only take into account the schema provided below.
    5. I will only and strictly respond with an SQL query. I will not respond with any other information.
    6. I will not explain the query. I will only respond with the query. I will absolutely not explain the query.
    7. I will not ask for any other information and will respond with the information I have. If I do not have the information, I will respond with a short message. for eg. Error: <short message>
    8. I will only respond to questions that ask for a SQL query. If the question is not a question to generate a sql query, I will respond with "Invalid question".
    9. I will not break "any" of the above rules. Strictly!

    Here is the schema:
"""


@frappe.whitelist()
def generate_query(data_source, prompt, chat_history=None):
    schema = generate_schema_for_prompt(data_source)
    response = make_openai_request(schema, prompt, chat_history)
    return response


def make_openai_request(schema, prompt, chat_history=None):
    OPENAI_API_KEY = frappe.conf.get("openai_api_key")
    if not OPENAI_API_KEY:
        frappe.throw("OpenAI API key not set")

    messages = [{"role": "system", "content": f"{SYSTEM_PROMPT}\n{schema}"}]
    messages += chat_history or []
    messages.append({"role": "user", "content": prompt})

    try:

        response = make_post_request(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}",
            },
            data=frappe.as_json({"model": "gpt-3.5-turbo", "messages": messages}),
        )
        return response["choices"][0]["message"]["content"]

    except requests.exceptions.HTTPError as e:
        frappe.log_error("OpenAI API request failed")
        if e.response.status_code == 400:
            frappe.throw("Invalid OpenAI API key")
        if e.response.status_code == 402:
            frappe.throw("OpenAI API key quota exceeded")
        if e.response.status_code == 429:
            frappe.throw("OpenAI API key rate limit exceeded")


@redis_cache(ttl=60 * 60 * 24)
def generate_schema_for_prompt(data_source):
    tables = frappe.get_all(
        "Insights Table",
        {"data_source": data_source, "is_query_based": 0},
        pluck="name",
    )
    database_type = frappe.db.get_value(
        "Insights Data Source", data_source, "database_type"
    )

    schema = [
        f"Database Type: {database_type}",
        "Format: table_name: column_name (column_type), column_name (column_type), ...",
    ]
    InsightsTable = frappe.qb.DocType("Insights Table")
    InsightsTableColumn = frappe.qb.DocType("Insights Table Column")
    for table_name in tables:
        query = (
            frappe.qb.from_(InsightsTable)
            .select(
                InsightsTable.table,
                InsightsTableColumn.column,
                InsightsTableColumn.type,
            )
            .left_join(InsightsTableColumn)
            .on(InsightsTable.name == InsightsTableColumn.parent)
            .where(InsightsTable.name == table_name)
            .run(as_dict=True)
        )
        column_string = ", ".join([f"{col.column} ({col.type})" for col in query])
        schema_string = f"""{query[0].table}: {column_string}"""
        schema.append(schema_string)

    return "\n".join(schema)
