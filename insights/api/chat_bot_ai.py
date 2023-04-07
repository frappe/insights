# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import os
from typing import List

import frappe
import tiktoken
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.schema import HumanMessage, SystemMessage
from langchain.vectorstores import Chroma

from insights.utils import get_data_source_schema_for_prompt


class ChatBotAI:
    def __init__(
        self,
        name: str,
        api_key: str,
        system_prompt: str = None,
        model_name: str = "gpt-3.5-turbo",
        **kwargs,
    ):
        self.name = name
        self.api_key = api_key
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.debug = kwargs.get("debug", False)

        private_folder = frappe.get_site_path("private", "files", "vectorstores")
        self.vector_store_path = os.path.join(private_folder, self.name)

    @property
    def vector_store(self):
        if not os.path.exists(self.vector_store_path):
            return None

        if not hasattr(self, "_vector_store"):
            self._vector_store = Chroma(
                collection_name=self.name,
                persist_directory=self.vector_store_path,
                embedding_function=OpenAIEmbeddings(openai_api_key=self.api_key),
            )

        return self._vector_store

    def reset_ingested_data(self):
        self.vector_store and self.vector_store.delete_collection()

    def has_ingested_data(self):
        return bool(self.vector_store and self.vector_store._collection.count())

    def validate_data(self, data: List[str]):
        if not data:
            frappe.throw("No data to ingest")
        if not isinstance(data, list):
            frappe.throw("Data must be a list")
        if not all(isinstance(d, str) for d in data):
            frappe.throw("All data must be a string")

    def ingest_data(self, data: List[str], reset: bool = False):
        self.validate_data(data)

        encoding = tiktoken.encoding_for_model("text-embedding-ada-002")
        token_count = len(encoding.encode("".join(data)))
        print(f"{token_count} tokens to ingest")

        print("Ingesting data")
        reset and self.reset_ingested_data()
        self._vector_store = Chroma.from_texts(
            data,
            collection_name=self.name,
            persist_directory=self.vector_store_path,
            embedding=OpenAIEmbeddings(openai_api_key=self.api_key),
        )

    def set_system_prompt(self, system_prompt):
        self.system_prompt = system_prompt

    def count_tokens(self, string: str) -> int:
        encoding = tiktoken.encoding_for_model(self.model_name)
        token_count = len(encoding.encode(string))
        print(f"Tokens Consumed: {token_count}")
        return token_count

    def add_context(self, question):
        context = self.vector_store.similarity_search(question, k=5)
        context = "\n".join([d.page_content for d in context])
        return f"""{self.system_prompt}
        ---------------
        {context}"""

    def answer_question(self, question):
        system_prompt = self.system_prompt
        if self.vector_store:
            system_prompt = self.add_context(question)

        self.count_tokens(system_prompt + question)
        chat = ChatOpenAI(openai_api_key=self.api_key)
        system_message = SystemMessage(content=system_prompt)
        human_message = HumanMessage(content=question)

        answer = chat([system_message, human_message])
        self.count_tokens(answer.content)
        return answer.content


def get_sql_bot_prompt():
    return """
    You are a sqlGPT, an AI assistant that generates SQL queries. You only respond with the SQL query and "do not explain" it or provide any other additional information. You build queries from the database tables and columns context provided below. You respond with a syntactically correct SQLite query that can be executed in the database to find the result as is. You "must" give short and proper aliases to the tables and columns. If you don't find any answer you "must" respond with the following text: "-"
    """


@frappe.whitelist()
def generate_sql(prompt, data_source, chat_history=None):
    if not frappe.conf.get("openai_api_key"):
        frappe.throw("OpenAI API Key not set")

    slug = frappe.scrub(data_source)
    chat_bot = ChatBotAI(
        name=f"sql_bot_for_{slug}",
        system_prompt=get_sql_bot_prompt(),
        api_key=frappe.conf.get("openai_api_key"),
    )
    if not chat_bot.has_ingested_data():
        schema = get_data_source_schema_for_prompt(data_source)
        chat_bot.ingest_data(schema)

    data_source_type = frappe.db.get_value(
        "Insights Data Source", data_source, "database_type"
    )
    data_source_type_context = f"Generate a query for {data_source_type} database"
    prompt = f"{data_source_type_context}\n{prompt}"
    return chat_bot.answer_question(prompt)
