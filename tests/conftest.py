from pathlib import Path
import re
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class WorkspaceTmpPathFactory:
    def __init__(self, base_path: Path):
        self._base_path = base_path
        self._counter = 0

    def getbasetemp(self) -> Path:
        return self._base_path

    def mktemp(self, basename: str, numbered: bool = True) -> Path:
        token = re.sub(r"[^A-Za-z0-9_.-]+", "_", basename).strip("._") or "tmp"
        if not numbered:
            target = self._base_path / token
            target.mkdir(parents=True, exist_ok=True)
            return target
        while True:
            target = self._base_path / f"{token}_{self._counter:03d}"
            self._counter += 1
            if target.exists():
                continue
            target.mkdir(parents=True, exist_ok=False)
            return target


def _make_unique_dir(parent: Path, prefix: str) -> Path:
    for index in range(1000):
        candidate = parent / f"{prefix}_{index:03d}"
        if candidate.exists():
            continue
        candidate.mkdir(parents=True, exist_ok=False)
        return candidate
    raise RuntimeError(f"could not allocate temp directory in {parent}")


@pytest.fixture(scope="session")
def tmp_path_factory():
    workspace_tmp_root = ROOT / ".test_work"
    workspace_tmp_root.mkdir(parents=True, exist_ok=True)
    base_path = _make_unique_dir(workspace_tmp_root, "run")
    factory = WorkspaceTmpPathFactory(base_path)
    yield factory
    shutil.rmtree(base_path, ignore_errors=True)


@pytest.fixture
def tmp_path(tmp_path_factory, request):
    name = getattr(request.node, "name", "tmp_path")
    return tmp_path_factory.mktemp(name, numbered=True)
