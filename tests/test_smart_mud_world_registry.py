from __future__ import annotations

import json
from pathlib import Path

import pytest

from smart_mud.startup import initialize_engine
from smart_mud.world_registry import (
    BUILDER_WORKSPACE_DIRS,
    RUNTIME_ASSET_DIRS,
    WorldRegistry,
    WorldValidationError,
)


def make_world(root: Path, name: str = "shattered_realms") -> Path:
    world = root / name
    world.mkdir()
    (world / "manifest.json").write_text(json.dumps({"name": name}), encoding="utf-8")
    for directory in RUNTIME_ASSET_DIRS:
        (world / directory).mkdir()
    return world


def test_missing_builder_folders_are_recreated_with_gitkeep(tmp_path: Path):
    world = make_world(tmp_path)
    registry = WorldRegistry(tmp_path)

    created = registry.prepare_builder_workspace(world)

    assert [path.relative_to(world).as_posix() for path in created] == list(BUILDER_WORKSPACE_DIRS)
    for directory in BUILDER_WORKSPACE_DIRS:
        assert (world / directory).is_dir()
        assert (world / directory / ".gitkeep").is_file()


def test_existing_builder_folders_remain_unchanged(tmp_path: Path):
    world = make_world(tmp_path)
    existing = world / "builder" / "history"
    existing.mkdir(parents=True)
    marker = existing / "existing.txt"
    marker.write_text("keep me", encoding="utf-8")

    WorldRegistry(tmp_path).prepare_builder_workspace(world)

    assert marker.read_text(encoding="utf-8") == "keep me"
    assert not (existing / ".gitkeep").exists()


def test_runtime_validation_still_fails_when_gameplay_folder_missing(tmp_path: Path):
    world = make_world(tmp_path)
    (world / "rooms").rmdir()

    with pytest.raises(WorldValidationError, match="rooms/"):
        WorldRegistry(tmp_path).validate_runtime_package(world)


def test_startup_succeeds_after_workspace_creation(tmp_path: Path):
    world = make_world(tmp_path)
    messages: list[str] = []

    registry = initialize_engine(tmp_path, logger=messages.append)

    assert "shattered_realms" in registry.worlds
    assert all((world / directory).is_dir() for directory in BUILDER_WORKSPACE_DIRS)
    assert "[startup] Ready." in messages


def test_startup_logging_reports_workspace_initialization(tmp_path: Path):
    make_world(tmp_path)
    messages: list[str] = []

    initialize_engine(tmp_path, logger=messages.append)

    assert "[startup] Validating runtime package..." in messages
    assert "    ✓ Runtime package valid" in messages
    assert "[startup] Preparing builder workspace..." in messages
    assert "    ✓ builder/" in messages
    assert "    ✓ builder/history/" in messages
    assert "[startup] Loading world assets..." in messages


def test_startup_logging_reports_already_prepared_workspace(tmp_path: Path):
    world = make_world(tmp_path)
    WorldRegistry(tmp_path).prepare_builder_workspace(world)
    messages: list[str] = []

    initialize_engine(tmp_path, logger=messages.append)

    assert "[startup] Builder workspace already prepared." in messages
    assert "    ✓ builder/" not in messages


def test_multiple_installed_worlds_each_receive_workspace(tmp_path: Path):
    first = make_world(tmp_path, "first")
    second = make_world(tmp_path, "second")

    registry = initialize_engine(tmp_path, logger=lambda _message: None)

    assert set(registry.worlds) == {"first", "second"}
    for world in (first, second):
        assert all((world / directory).is_dir() for directory in BUILDER_WORKSPACE_DIRS)
