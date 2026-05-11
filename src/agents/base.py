"""Base class shared by all 5 inventory agents.

Built on Mesa's Agent so agents fit into the Mesa scheduler. Each agent owns
its own decision log so we can satisfy the proposal's auditability and
transparency requirement.
"""
from __future__ import annotations

from typing import Any
from mesa import Agent


class BaseInventoryAgent(Agent):
    """Shared behavior: identity, message inbox, decision log."""

    def __init__(self, model: Any) -> None:
        # Mesa 3.x: Agent.__init__ takes only `model`; unique_id is auto-assigned.
        super().__init__(model)
        self.inbox: list[dict] = []
        self.decision_log: list[dict] = []

    # --- Messaging --------------------------------------------------------
    def send(self, recipient: "BaseInventoryAgent", message: dict) -> None:
        """Push a message into another agent's inbox.

        Messages are plain dicts; we'll formalize a schema once the agents
        are wired up end-to-end.
        """
        recipient.inbox.append({"from": self.unique_id, **message})

    def drain_inbox(self) -> list[dict]:
        msgs, self.inbox = self.inbox, []
        return msgs

    # --- Logging ----------------------------------------------------------
    def log(self, action: str, **fields: Any) -> None:
        self.decision_log.append(
            {"step": self.model.steps, "action": action, **fields}
        )

    # --- Mesa hook --------------------------------------------------------
    def step(self) -> None:  # pragma: no cover — overridden by subclasses
        raise NotImplementedError
