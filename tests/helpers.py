"""Shared test helpers: every test gets a pristine, throwaway workspace and knowledge base,
so results never depend on whatever your demo runs have left in workspace/."""
import shutil
import tempfile
from pathlib import Path

from agentforge.config import PROJECT_ROOT, Settings


def make_settings(**overrides) -> tuple[Settings, tempfile.TemporaryDirectory]:
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    shutil.copytree(PROJECT_ROOT / "knowledge", root / "knowledge")
    for package in ("src", "tests"):
        (root / "workspace" / package).mkdir(parents=True)
        (root / "workspace" / package / "__init__.py").write_text("")
    return Settings(root=root, provider="mock", **overrides), tmp
