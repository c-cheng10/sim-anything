import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def find_menagerie() -> Path | None:
    env = os.environ.get("MENAGERIE_DIR")
    for cand in ([Path(env)] if env else []) + [ROOT / "third_party" / "mujoco_menagerie"]:
        if cand.is_dir():
            return cand
    return None


@pytest.fixture
def menagerie_dir() -> Path:
    d = find_menagerie()
    if d is None:
        pytest.skip("Menagerie not available (set MENAGERIE_DIR or clone into third_party/)")
    return d


@pytest.fixture
def examples_dir() -> Path:
    return ROOT / "examples"
