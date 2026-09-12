from pathlib import Path


def test_action_manifest_uses_secret_as_environment_input() -> None:
    manifest = Path("action.yml").read_text(encoding="utf-8")
    assert "PAYLAB_SECRET: ${{ inputs.secret }}" in manifest
    assert "python -m paylab.action_runner" in manifest
    assert "value: ${{ steps.gate.outputs.passed }}" in manifest


def test_action_smoke_workflow_executes_local_action() -> None:
    workflow = Path(".github/workflows/action-smoke.yml").read_text(encoding="utf-8")
    assert "uses: ./" in workflow
    assert 'test "$PAYLAB_PERCENTAGE" = "100"' in workflow
