from __future__ import annotations

import argparse

import httpx

from examples.test_agents.aop import Integration, build_json_export


def verify_rejections(agentq_url: str) -> None:
    service_name = "gemma-e2e-negative"
    with httpx.Client(base_url=agentq_url, timeout=15) as client:
        registration = client.post("/api/agents", json={
            "service_name": service_name,
            "integration_type": "otel",
        })
        registration.raise_for_status()
        token = registration.json()["connection_token"]
        valid_payload = build_json_export(
            integration=Integration.OTEL,
            service_name=service_name,
            name="chat",
            attributes={"gen_ai.system": "gemma", "gen_ai.operation.name": "chat"},
        )
        wrong_identity_payload = build_json_export(
            integration=Integration.OTEL,
            service_name="unauthorized-identity",
            name="chat",
            attributes={"gen_ai.system": "gemma", "gen_ai.operation.name": "chat"},
        )

        wrong_token = client.post(
            "/v1/traces",
            headers={"X-AgentQ-Agent-Token": "invalid-token"},
            json=valid_payload,
        )
        wrong_identity = client.post(
            "/v1/traces",
            headers={"X-AgentQ-Agent-Token": token},
            json=wrong_identity_payload,
        )
        malformed = client.post(
            "/v1/traces",
            headers={
                "X-AgentQ-Agent-Token": token,
                "Content-Type": "application/x-protobuf",
            },
            content=b"not-protobuf",
        )
        agent = next(
            item for item in client.get("/api/agents").json()
            if item["service_name"] == service_name
        )

    assert wrong_token.status_code == 403
    assert wrong_identity.status_code == 403
    assert malformed.status_code == 400
    assert agent["connection_status"] == "pending"
    assert agent["span_count"] == 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agentq-url", required=True)
    args = parser.parse_args()
    verify_rejections(args.agentq_url)
    print("Negative authorization checks verified")


if __name__ == "__main__":
    main()
