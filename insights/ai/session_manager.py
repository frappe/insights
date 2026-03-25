import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AIMessage:
    role: str
    content: str
    operations: list[dict] | None = None
    error: str | None = None
    timestamp: str = ""


@dataclass
class AISession:
    session_id: str
    data_source: str
    question: str
    operations: list[dict] = field(default_factory=list)
    messages: list[AIMessage] = field(default_factory=list)
    schema: dict[str, Any] = field(default_factory=dict)

    def add_user_message(self, content: str):
        self.messages.append(AIMessage(role="user", content=content))

    def add_assistant_message(
        self, content: str, operations: list[dict] | None = None, error: str | None = None
    ):
        self.messages.append(AIMessage(role="assistant", content=content, operations=operations, error=error))

    def update_operations(self, operations: list[dict]):
        self.operations = operations

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "data_source": self.data_source,
            "question": self.question,
            "operations": self.operations,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "operations": m.operations,
                    "error": m.error,
                    "timestamp": m.timestamp,
                }
                for m in self.messages
            ],
        }


class AISessionManager:
    _sessions: dict[str, AISession] = {}

    @classmethod
    def create_session(cls, data_source: str, question: str, schema: dict[str, Any]) -> AISession:
        session_id = str(uuid.uuid4())[:8]
        session = AISession(
            session_id=session_id,
            data_source=data_source,
            question=question,
            schema=schema,
        )
        session.add_user_message(question)
        cls._sessions[session_id] = session
        return session

    @classmethod
    def get_session(cls, session_id: str) -> AISession | None:
        return cls._sessions.get(session_id)

    @classmethod
    def update_session_operations(cls, session_id: str, operations: list[dict]):
        session = cls._sessions.get(session_id)
        if session:
            session.update_operations(operations)

    @classmethod
    def add_assistant_response(
        cls,
        session_id: str,
        content: str,
        operations: list[dict] | None = None,
        error: str | None = None,
    ):
        session = cls._sessions.get(session_id)
        if session:
            session.add_assistant_message(content, operations, error)

    @classmethod
    def add_user_message(cls, session_id: str, content: str):
        session = cls._sessions.get(session_id)
        if session:
            session.add_user_message(content)

    @classmethod
    def get_conversation_history(cls, session_id: str) -> list[dict]:
        session = cls._sessions.get(session_id)
        if session:
            return [
                {
                    "role": m.role,
                    "content": m.content,
                    "operations": m.operations,
                    "error": m.error,
                }
                for m in session.messages
            ]
        return []

    @classmethod
    def list_sessions(cls) -> list[dict]:
        return [
            {
                "session_id": s.session_id,
                "data_source": s.data_source,
                "question": s.question,
                "message_count": len(s.messages),
            }
            for s in cls._sessions.values()
        ]

    @classmethod
    def delete_session(cls, session_id: str):
        if session_id in cls._sessions:
            del cls._sessions[session_id]
