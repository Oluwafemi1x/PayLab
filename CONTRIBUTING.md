# Contributing to PayLab

Thanks for helping make payment integrations safer.

## Local setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## Good contributions for v0.x

- New provider adapters and realistic webhook fixtures
- More failure scenarios (timeouts, retries, out-of-order events)
- Signature verification tests
- Documentation and examples
- Dashboard work

Please add tests for behavior changes and never include real provider secrets or customer data.
