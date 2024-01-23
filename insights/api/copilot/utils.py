# Copyright (c) 2022, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import hashlib

import tiktoken
from frappe import _dict

MODELS = _dict(
    GPT_4=_dict(
        name="gpt-4-1106-preview",
        cost=0.02,
    ),
    GPT_3_5=_dict(
        name="gpt-3.5-turbo-1106",
        cost=0.0013,
    ),
)


def count_token(messages, model=MODELS.GPT_3_5.name):
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
