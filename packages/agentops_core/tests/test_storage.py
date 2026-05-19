from pathlib import Path

import pytest

from agentops_core.services.storage import LocalStorage


@pytest.fixture
def storage(tmp_path: Path) -> LocalStorage:
    return LocalStorage(root=tmp_path)


def test_save_and_load_file(storage: LocalStorage):
    saved_path = storage.save("sop/factory-1/spec.md", b"# SOP\n\nStep 1\n")
    assert saved_path.exists()
    assert storage.load(saved_path) == b"# SOP\n\nStep 1\n"


def test_save_creates_intermediate_dirs(storage: LocalStorage):
    saved_path = storage.save("sop/factory-2/sub/dir/spec.pdf", b"binary")
    assert saved_path.exists()
    assert saved_path.parent.is_dir()


def test_dir_for_returns_path(storage: LocalStorage):
    skill_dir = storage.dir_for("skills/refund-flow")
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("hello")
    assert (storage.root / "skills" / "refund-flow" / "SKILL.md").read_text() == "hello"


def test_resolve_relative_path(storage: LocalStorage):
    resolved = storage.resolve("sop/x.pdf")
    assert resolved == storage.root / "sop" / "x.pdf"
