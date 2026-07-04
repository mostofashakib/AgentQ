from sqlalchemy import select

from agentq.db.models import ConnectedAgent, Span


def visible_trace_ids(*, require_behavior: bool = False):
    query = select(Span.trace_id).join(
        ConnectedAgent, ConnectedAgent.service_name == Span.service_name,
    ).where(ConnectedAgent.enabled.is_(True), ConnectedAgent.capture_traces.is_(True))
    if require_behavior:
        query = query.where(ConnectedAgent.analyze_behavior.is_(True))
    return query.distinct()


def visible_spans():
    return select(Span).join(
        ConnectedAgent, ConnectedAgent.service_name == Span.service_name,
    ).where(ConnectedAgent.enabled.is_(True), ConnectedAgent.capture_traces.is_(True))
