from pathlib import Path


def test_launch_demo_rejects_stale_merchant() -> None:
    script = Path("examples/launch_demo.ps1").read_text(encoding="utf-8")

    assert "Test-DemoMerchantCompatibility" in script
    assert "paylab_demo_preflight" in script
    assert "stale or incompatible demo merchant" in script
    assert "deliveries_received" in script
    assert "side_effect_count" in script
