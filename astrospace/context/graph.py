"""
LangGraph integration point (agent orchestration with checkpointing).

Deliberately thin: the Context Engine is framework-agnostic; this module is
the only place LangGraph is touched, and it is imported lazily so the core
engine, API and tests never require the dependency.

Install when the agent layer lands:
    pip install langgraph langgraph-checkpoint-sqlite

Graph shape (v1):
    route -> assemble -> domain_agent -> END
with a SQLite checkpointer keyed by thread_id, so a user can leave a reading
conversation and resume it with state (question, bundle, messages) intact.

The domain agent node receives ReadingState and must return {"messages": [...],
"reading": str}. Model calls stay in the caller-supplied `agent_fn` so the
existing anthropic SDK usage (astrospace/agents) plugs in unchanged.
"""
from __future__ import annotations

from typing import Any, Callable, TypedDict

from .assembler import assemble
from .router import KeywordRouter, Router


class ReadingState(TypedDict, total=False):
    question: str
    kundli_id: str
    domains: list[str]
    routing: dict
    bundle: dict
    messages: list[dict]
    reading: str


def build_reading_graph(chart_loader: Callable[[str], Any],
                        agent_fn: Callable[[ReadingState], dict],
                        router: Router | None = None,
                        checkpoint_path: str = "astrospace_readings.sqlite"):
    """Compile the reading graph. Raises a helpful ImportError without langgraph.

    chart_loader: kundli_id -> VedicChart
    agent_fn: ReadingState -> {"messages": [...], "reading": str}
    """
    try:
        from langgraph.graph import END, StateGraph
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError as e:
        raise ImportError(
            "LangGraph is not installed. The Context Engine works without it; "
            "for the agent graph run: pip install langgraph langgraph-checkpoint-sqlite"
        ) from e

    router = router or KeywordRouter()

    def route_node(state: ReadingState) -> dict:
        decision = router.route(state["question"])
        return {
            "domains": decision.domains,
            "routing": {
                "primary": decision.primary,
                "secondary": list(decision.secondary),
                "confidence": decision.confidence,
                "method": decision.method,
            },
        }

    def assemble_node(state: ReadingState) -> dict:
        chart = chart_loader(state["kundli_id"])
        bundle = assemble(chart, state["domains"], question=state["question"])
        return {"bundle": bundle}

    graph = StateGraph(ReadingState)
    graph.add_node("route", route_node)
    graph.add_node("assemble", assemble_node)
    graph.add_node("domain_agent", agent_fn)
    graph.set_entry_point("route")
    graph.add_edge("route", "assemble")
    graph.add_edge("assemble", "domain_agent")
    graph.add_edge("domain_agent", END)

    checkpointer = SqliteSaver.from_conn_string(checkpoint_path)
    return graph.compile(checkpointer=checkpointer)
