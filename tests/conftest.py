import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "chat"))


def pytest_collection_modifyitems(config, items):
    if os.getenv("RUN_INTEGRATION") != "1":
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(pytest.mark.skip(reason="Use RUN_INTEGRATION=1 com Docker Compose ativo."))
