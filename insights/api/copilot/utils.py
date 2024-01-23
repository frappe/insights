# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import hashlib

import tiktoken

DEFAULT_MODEL = "gpt-3.5-turbo-1106"


def count_token(messages, model=DEFAULT_MODEL):
    if not isinstance(messages, list):
        messages = [messages]
    return sum((len(tiktoken.encoding_for_model(model).encode(m)) for m in messages))


def get_digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def get_message(message):
    if message["role"] == "assistant":
        return {"role": "assistant", "content": message["message"]}
    elif message["role"] == "user":
        return {"role": "user", "content": message["message"]}
    elif message["role"] == "tool":
        return {
            "role": "tool",
            "tool_call_id": message["tool_call_id"],
            "name": message["name"],
            "content": message["message"],
        }
    else:
        return {"role": "assistant", "content": message["message"]}


def get_function_definitions():
    return [
        {
            "type": "function",
            "function": {
                "name": "get_relevant_tables",
                "description": "A function useful for finding the tables that are relevant to generate a sql query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The user's question",
                        },
                    },
                    "required": ["question"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "validate_sql_query",
                "description": "A function useful for validating a sql query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "A syntactically correct sql query",
                        },
                    },
                    "required": ["query"],
                },
            },
        },
    ]
