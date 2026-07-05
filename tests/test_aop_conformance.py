import pytest
from httpx import ASGITransport, AsyncClient

from agentq.api.app import app
from agentq.ingest.parser import parse_otlp_json, parse_otlp_protobuf
from examples.test_agents.aop import Integration, build_json_export, build_protobuf_export


@pytest.mark.parametrize("integration", [Integration.OTEL, Integration.CURL, Integration.MCP])
def test_json_integrations_build_valid_aop_payloads(integration):
    payload = build_json_export(
        integration=integration,
        service_name=f"{integration.value}-agent",
        name="tool:web_search",
        attributes={"gen_ai.tool.name": "web_search"},
    )

    records = parse_otlp_json(payload)
    assert len(records) == 1
    assert records[0].service_name == f"{integration.value}-agent"
    assert records[0].gen_ai_tool_name == "web_search"


def test_mcp_test_agent_emits_mcp_semantic_attributes():
    payload = build_json_export(
        integration=Integration.MCP,
        service_name="mcp-agent",
        name="tools/call",
        attributes={"gen_ai.tool.name": "web_search"},
    )

    record = parse_otlp_json(payload)[0]
    assert record.attributes["mcp.method.name"] == "tools/call"
    assert record.attributes["mcp.tool.name"] == "web_search"
    assert record.gen_ai_system == "mcp:test-agent-tools"


@pytest.mark.parametrize("integration", [Integration.OTEL_PROTOBUF, Integration.OPENCLAW])
def test_protobuf_integrations_build_valid_aop_payloads(integration):
    body = build_protobuf_export(
        integration=integration,
        service_name=f"{integration.value}-agent",
        name="chat",
        attributes={"gen_ai.system": "gemma", "gen_ai.operation.name": "chat"},
    )

    records = parse_otlp_protobuf(body)
    assert len(records) == 1
    assert records[0].service_name == f"{integration.value}-agent"
    assert records[0].gen_ai_system == "gemma"
    if integration is Integration.OPENCLAW:
        assert records[0].attributes["openclaw.integration"] == "diagnostics-otel"


@pytest.mark.parametrize("integration", list(Integration))
async def test_each_integration_establishes_connection_end_to_end(integration):
    service_name = f"e2e-{integration.value}"
    registration_type = "otel" if integration is Integration.OTEL_PROTOBUF else integration.value
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        registration = await client.post("/api/agents", json={
            "service_name": service_name,
            "integration_type": registration_type,
        })
        assert registration.status_code == 201
        token = registration.json()["connection_token"]
        headers = {"X-AgentQ-Agent-Token": token}
        attributes = {"gen_ai.system": "gemma", "gen_ai.operation.name": "chat"}

        if integration in {Integration.OPENCLAW, Integration.OTEL_PROTOBUF}:
            headers["Content-Type"] = "application/x-protobuf"
            response = await client.post("/v1/traces", headers=headers, content=build_protobuf_export(
                integration=integration, service_name=service_name, name="chat", attributes=attributes,
            ))
        else:
            response = await client.post("/v1/traces", headers=headers, json=build_json_export(
                integration=integration, service_name=service_name, name="chat", attributes=attributes,
            ))

        listed = (await client.get("/api/agents")).json()

    assert response.status_code == 200
    assert listed[0]["connection_status"] == "connected"
    assert listed[0]["span_count"] == 1


async def test_mismatched_service_identity_is_rejected_and_remains_pending():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        registration = await client.post("/api/agents", json={
            "service_name": "authorized-agent", "integration_type": "otel",
        })
        token = registration.json()["connection_token"]
        payload = build_json_export(
            integration=Integration.OTEL,
            service_name="different-agent",
            name="chat",
            attributes={"gen_ai.system": "gemma"},
        )
        response = await client.post(
            "/v1/traces", headers={"X-AgentQ-Agent-Token": token}, json=payload,
        )
        listed = (await client.get("/api/agents")).json()

    assert response.status_code == 403
    assert listed[0]["connection_status"] == "pending"
    assert listed[0]["span_count"] == 0


async def test_malformed_protobuf_is_rejected_without_creating_test_records():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        registration = await client.post("/api/agents", json={
            "service_name": "malformed-agent", "integration_type": "otel",
        })
        token = registration.json()["connection_token"]
        response = await client.post(
            "/v1/traces",
            headers={
                "X-AgentQ-Agent-Token": token,
                "Content-Type": "application/x-protobuf",
            },
            content=b"not-protobuf",
        )
        listed = (await client.get("/api/agents")).json()

    assert response.status_code == 400
    assert listed[0]["connection_status"] == "pending"
    assert listed[0]["span_count"] == 0
