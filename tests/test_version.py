import tomllib
from pathlib import Path

import paylab


def test_package_and_runtime_versions_match() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == paylab.__version__
