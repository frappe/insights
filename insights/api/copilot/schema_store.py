# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt


import frappe
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

from insights.utils import InsightsDataSource

from .utils import count_token, get_digest


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
                embedding_function=OpenAIEmbeddings(
                    openai_api_key=frappe.conf.get("openai_api_key"),
                ),
            )

        return self._vector_store

    def ingest_schema(self, reset=False):
        schema = self.get_schema()

        if not reset:
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
            embedding=OpenAIEmbeddings(
                openai_api_key=frappe.conf.get("openai_api_key"),
            ),
        )
        self._vector_store.persist()

    def get_schema(self):
        """
        Returns a list of dicts with attributes: id, text, metadata.
        - ID: A unique identifier for the Table and its Columns.
        - Text: The Table name and Column names.
        - Metadata: The Table name and the number of rows in the table.
        """

        tables = frappe.get_all(
            "Insights Table",
            filters={
                "data_source": self.data_source,
                "is_query_based": 0,
                "hidden": 0,
            },
            fields=["name", "table", "modified"],
        )

        data = []
        doc = InsightsDataSource.get_doc(self.data_source)
        for table in tables:
            query = f"SELECT * FROM `{table.table}` LIMIT 2"
            try:
                results = doc._db.execute_query(query, return_columns=True)
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
        return get_digest(f"{name}{modified}")

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
            for col in row:
                trimmed = str(col)[:7]
                trimmed = trimmed + "..." if len(trimmed) >= 7 else trimmed
                ret += f"{trimmed}, "
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
