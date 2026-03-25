import frappe

from insights.ai import AIClient, OperationParser, PromptBuilder, validate_operations
from insights.ai.session_manager import AISessionManager
from insights.api.data_sources import get_schema
from insights.decorators import insights_whitelist, validate_type

MAX_RETRIES = 3


@insights_whitelist()
@validate_type
def create_ai_session(question: str, data_source: str):
    if not question or not question.strip():
        frappe.throw("Question cannot be empty")

    schema = get_schema(data_source)
    session = AISessionManager.create_session(data_source, question, schema)

    result = _generate_query_with_retries(
        question=question,
        data_source=data_source,
        schema=schema,
        session_id=session.session_id,
    )

    if result.get("operations"):
        session.update_operations(result["operations"])
        session.add_assistant_message(
            content=f"Generated {len(result['operations'])} operations",
            operations=result["operations"],
            error=result.get("error"),
        )

    return {
        "session_id": session.session_id,
        "data_source": data_source,
        "question": question,
        "operations": result.get("operations"),
        "attempts": result.get("attempts", 1),
        "error": result.get("error"),
    }


@insights_whitelist()
@validate_type
def ask_follow_up(session_id: str, question: str):
    session = AISessionManager.get_session(session_id)
    if not session:
        frappe.throw("Session not found. Please start a new conversation.")

    schema = session.schema
    session.add_user_message(question)

    result = _generate_query_with_retries(
        question=question,
        data_source=session.data_source,
        schema=schema,
        session_id=session_id,
        previous_operations=session.operations,
        conversation_history=AISessionManager.get_conversation_history(session_id),
    )

    if result.get("operations"):
        session.update_operations(result["operations"])
        session.add_assistant_message(
            content=f"Updated query with {len(result['operations'])} operations",
            operations=result["operations"],
            error=result.get("error"),
        )

    return {
        "session_id": session_id,
        "question": question,
        "operations": result.get("operations"),
        "attempts": result.get("attempts", 1),
        "error": result.get("error"),
        "is_modification": bool(session.operations),
    }


@insights_whitelist()
@validate_type
def get_ai_session(session_id: str):
    session = AISessionManager.get_session(session_id)
    if not session:
        frappe.throw("Session not found")

    return {
        "session_id": session.session_id,
        "data_source": session.data_source,
        "question": session.question,
        "operations": session.operations,
        "messages": session.messages,
    }


@insights_whitelist()
@validate_type
def list_ai_sessions():
    return AISessionManager.list_sessions()


@insights_whitelist()
@validate_type
def delete_ai_session(session_id: str):
    AISessionManager.delete_session(session_id)
    return {"success": True}


def _generate_query_with_retries(
    question: str,
    data_source: str,
    schema: dict,
    session_id: str,
    previous_operations: list | None = None,
    conversation_history: list | None = None,
):
    prompt_builder = PromptBuilder(schema, question, data_source)
    ai_client = AIClient()
    operations = None
    last_error: dict | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        if attempt == 1:
            prompt = prompt_builder.build(
                previous_operations=previous_operations,
                conversation_history=conversation_history,
            )
        else:
            prompt = prompt_builder.build_correction_prompt(
                current_operations=operations,
                error_message=last_error["message"],
                failed_at_index=last_error["failed_at_index"],
                operation_type=last_error["operation_type"],
                available_columns=last_error["available_columns"],
                partial_sql=last_error["partial_sql"],
                attempt=attempt,
                max_attempts=MAX_RETRIES,
            )

        print(f"\n{'=' * 60}")
        print(f"SESSION: {session_id}")
        print(f"ATTEMPT {attempt}/{MAX_RETRIES}")
        print(f"{'=' * 60}")
        print("\n--- Prompt (first 800 chars) ---")
        print(prompt[:800])
        print(f"\n--- Full Prompt Length: {len(prompt)} chars ---")

        raw_response = ai_client.generate_query(prompt)
        print("\n--- Raw Response (first 500 chars) ---")
        print(raw_response[:500])
        print(f"\n--- Full Response Length: {len(raw_response)} chars ---")

        parser = OperationParser(raw_response)
        operations = parser.parse()
        print(f"\n--- Parsed Operations ({len(operations)}) ---")
        for i, op in enumerate(operations):
            print(f"  [{i}] {op}")

        is_valid, validation_error = validate_operations(data_source, operations)
        print("\n--- Validation Result ---")
        print(f"  Valid: {is_valid}")
        if validation_error:
            print(f"  Error: {validation_error.message}")
            print(f"  Failed at index: {validation_error.failed_at_index}")
            print(f"  Operation type: {validation_error.operation_type}")
            print(f"  Available columns: {validation_error.available_columns}")

        if is_valid:
            return {
                "operations": operations,
                "question": question,
                "data_source": data_source,
                "attempts": attempt,
            }

        last_error = {
            "message": validation_error.message,
            "failed_at_index": validation_error.failed_at_index,
            "operation_type": validation_error.operation_type,
            "available_columns": validation_error.available_columns,
            "partial_sql": validation_error.partial_sql,
        }
        print("\n--- Will Retry with Correction Prompt ---")

    return {
        "operations": operations,
        "question": question,
        "data_source": data_source,
        "attempts": MAX_RETRIES,
        "error": last_error["message"] if last_error else "Unknown error",
        "failed_at_index": last_error["failed_at_index"] if last_error else None,
    }
