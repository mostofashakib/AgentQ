import subprocess
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "app.sh"


def test_unified_cli_help_lists_all_modes():
    result = subprocess.run([SCRIPT, "help"], text=True, capture_output=True, check=False)

    assert result.returncode == 0
    for mode in ("run", "kill", "demo", "test", "agent", "e2e"):
        assert mode in result.stdout


def test_unified_cli_rejects_unknown_mode():
    result = subprocess.run([SCRIPT, "unknown"], text=True, capture_output=True, check=False)

    assert result.returncode == 2
    assert "Unknown mode" in result.stderr
