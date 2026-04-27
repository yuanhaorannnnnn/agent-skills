"""Unified data model for normalizing conversation events across agents."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Event:
    """A normalized event from any agent's conversation log."""

    timestamp: datetime
    agent: str  # "claude", "codex", "kimi"
    session_id: str
    event_type: str  # "user_prompt", "assistant_response", "file_change",
    # "tool_call", "tool_result", "system", "thinking", "title"
    content: str = ""
    project: str = ""
    cwd: str = ""
    git_branch: str = ""
    file_path: str = ""
    tool_name: str = ""
    metadata: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        ts = self.timestamp.strftime("%m-%d %H:%M")
        content_preview = self.content[:60].replace("\n", " ") if self.content else ""
        return f"Event({ts} {self.agent} {self.event_type}: {content_preview}...)"


@dataclass
class Session:
    """A collection of events belonging to a single conversation session."""

    session_id: str
    agent: str
    project: str = ""
    title: str = ""
    cwd: str = ""
    git_branch: str = ""
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    status: str = ""  # "active", "completed", "abandoned"
    events: list[Event] = field(default_factory=list)

    def first_user_prompt(self) -> Optional[Event]:
        for e in self.events:
            if e.event_type == "user_prompt":
                return e
        return None

    def last_assistant_response(self) -> Optional[Event]:
        for e in reversed(self.events):
            if e.event_type == "assistant_response":
                return e
        return None

    def file_change_events(self) -> list[Event]:
        return [e for e in self.events if e.event_type == "file_change"]

    def tool_call_events(self) -> list[Event]:
        return [e for e in self.events if e.event_type == "tool_call"]

    def user_prompt_events(self) -> list[Event]:
        return [e for e in self.events if e.event_type == "user_prompt"]

    def assistant_response_events(self) -> list[Event]:
        return [e for e in self.events if e.event_type == "assistant_response"]
