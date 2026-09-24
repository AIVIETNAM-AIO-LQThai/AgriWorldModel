import enum
import uuid
from typing import Any

from pydantic import BaseModel


class ToolExecutionStatus(str, enum.Enum):
    SUCCESS = "success"
    BLOCKED = "blocked"


class CalculatedFact(BaseModel):
    """
    One deterministic fact produced by a trusted tool.
    """

    name: str

    value: float
    unit: str

    source_tool: str

    source_event_ids: list[uuid.UUID]


class ToolExecutionRecord(BaseModel):
    """
    Auditable record of one deterministic tool execution.
    """

    tool_name: str
    tool_version: str

    status: ToolExecutionStatus

    inputs: dict[str, Any]

    outputs: dict[str, Any]

    source_event_ids: list[uuid.UUID]

    message: str | None = None


class ToolExecutionPacket(BaseModel):
    executions: list[ToolExecutionRecord]

    calculated_facts: list[CalculatedFact]