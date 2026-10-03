import json
from dataclasses import dataclass


def to_sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@dataclass
class RunStartedEvent:
    thread_id: str
    run_id: str

    def to_sse(self) -> str:
        return to_sse({
            "type": "RUN_STARTED",
            "threadId": self.thread_id,
            "runId": self.run_id,
        })


@dataclass
class RunFinishedEvent:
    thread_id: str
    run_id: str

    def to_sse(self) -> str:
        return to_sse({
            "type": "RUN_FINISHED",
            "threadId": self.thread_id,
            "runId": self.run_id,
        })

@dataclass
class TextMessageStartEvent:
    message_id: str
    role: str = "assistant"

    def to_sse(self) -> str:
        return to_sse({
            "type": "TEXT_MESSAGE_START",
            "messageId": self.message_id,
            "role": self.role,
        })


@dataclass
class TextMessageContentEvent:
    message_id: str
    delta: str

    def to_sse(self) -> str:
        return to_sse({
            "type": "TEXT_MESSAGE_CONTENT",
            "messageId": self.message_id,
            "delta": self.delta,
        })


@dataclass
class TextMessageEndEvent:
    message_id: str

    def to_sse(self) -> str:
        return to_sse({
            "type": "TEXT_MESSAGE_END",
            "messageId": self.message_id,
        })

# --- Tool call events ---

@dataclass
class ToolCallStartEvent:
    tool_call_id: str
    tool_call_name: str

    def to_sse(self) -> str:
        return to_sse({
            "type": "TOOL_CALL_START",
            "toolCallId": self.tool_call_id,
            "toolCallName": self.tool_call_name,
        })


@dataclass
class ToolCallArgsEvent:
    tool_call_id: str
    delta: str

    def to_sse(self) -> str:
        return to_sse({
            "type": "TOOL_CALL_ARGS",
            "toolCallId": self.tool_call_id,
            "delta": self.delta,
        })


@dataclass
class ToolCallEndEvent:
    tool_call_id: str

    def to_sse(self) -> str:
        return to_sse({
            "type": "TOOL_CALL_END",
            "toolCallId": self.tool_call_id,
        })


@dataclass
class ToolCallResultEvent:
    message_id: str | None
    tool_call_id: str
    content: str

    def to_sse(self) -> str:
        return to_sse({
            "type": "TOOL_CALL_RESULT",
            "messageId": self.message_id,
            "toolCallId": self.tool_call_id,
            "content": self.content,
        })

# ----- Step events -----
@dataclass
class StepStartedEvent:
    step_name: str

    def to_sse(self) -> str:
        return to_sse({
            "type": "STEP_STARTED",
            "stepName": self.step_name,
        })


@dataclass
class StepFinishedEvent:
    step_name: str

    def to_sse(self) -> str:
        return to_sse({
            "type": "STEP_FINISHED",
            "stepName": self.step_name,
        })

# ----- Error -----

@dataclass
class ErrorEvent:
    message: str
    code: str | None = None

    def to_sse(self) -> str:
        return to_sse({
            "type": "ERROR",
            "error": {
                "message": self.message,
                "code": self.code,
            },
        })