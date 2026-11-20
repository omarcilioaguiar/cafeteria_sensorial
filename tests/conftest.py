import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "chat"))
sys.path.insert(0, str(ROOT / "scripts"))
from local_config import configure_ports
configure_ports()


@pytest.fixture(autouse=True)
def isolated_chat(monkeypatch):
    import main
    monkeypatch.setattr(main.semantic_cache, "state", "disabled")
    monkeypatch.setattr(main.semantic_cache, "start", lambda: None)
    main._request_log.clear()


def pytest_collection_modifyitems(config, items):
    if os.getenv("RUN_INTEGRATION") != "1":
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="Use RUN_INTEGRATION=1 com Docker Compose ativo."))
