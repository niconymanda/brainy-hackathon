from dataclasses import dataclass


@dataclass(frozen=True)
class AgentStep:
    narration: str
    action: str


@dataclass(frozen=True)
class NeedsUser:
    question: str


@dataclass(frozen=True)
class ConfirmRequest:
    summary: str


@dataclass(frozen=True)
class Done:
    result: str


@dataclass(frozen=True)
class AgentError:
    reason: str
    suggestion: str
