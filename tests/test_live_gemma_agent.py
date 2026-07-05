import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]


@pytest.mark.live
def test_real_gemma_agent_exercises_every_integration_and_tool():
    """Run the actual local model; app.sh bootstraps Ollama/Gemma when absent."""
    environment = os.environ.copy()
    result = subprocess.run(
        [ROOT / "app.sh", "e2e", "all"],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        timeout=900,
        check=False,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "Negative authorization checks verified" in output
    assert "Removed isolated test database, logs, and telemetry" in output
    for integration in ("openclaw", "otel", "otel-protobuf", "mcp", "curl"):
        assert f"Gemma → {integration}" in output
    for tool in ("calculator", "web_search", "current_time"):
        expected = "calculate" if tool == "calculator" else tool
        assert f"→ {expected} →" in output
