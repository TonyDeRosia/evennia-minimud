"""World package discovery, validation, and Builder workspace setup."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable


RUNTIME_ASSET_DIRS: tuple[str, ...] = (
    "rooms",
    "areas",
    "npcs",
    "items",
    "quests",
    "zones",
    "races",
    "classes",
    "skills",
    "spells",
    "abilities",
    "factions",
    "shops",
    "trainers",
    "dialogue",
    "lore",
    "rules",
)

BUILDER_WORKSPACE_DIRS: tuple[str, ...] = (
    "builder",
    "builder/audit",
    "builder/history",
    "builder/snapshots",
    "builder/exports",
    "builder/imports",
    "builder/templates",
)


class WorldValidationError(Exception):
    """Raised when a world package is missing fatal gameplay assets."""


@dataclass(frozen=True)
class WorldManifest:
    """Loaded world manifest data."""

    name: str
    path: Path
    data: dict


@dataclass
class RegisteredWorld:
    """Runtime representation of a validated and prepared world package."""

    name: str
    path: Path
    manifest: WorldManifest
    assets: dict[str, list[Path]] = field(default_factory=dict)
    created_workspace_dirs: list[Path] = field(default_factory=list)


LogFn = Callable[[str], None]


class WorldRegistry:
    """Owns the installed-world lifecycle from scan through registration."""

    def __init__(self, worlds_root: str | Path, *, logger: LogFn | None = None) -> None:
        self.worlds_root = Path(worlds_root)
        self.logger = logger or (lambda _message: None)
        self.worlds: dict[str, RegisteredWorld] = {}

    def scan_installed_worlds(self) -> list[Path]:
        """Return directories under the worlds root that look like world packages."""
        if not self.worlds_root.exists():
            return []
        return sorted(path for path in self.worlds_root.iterdir() if path.is_dir())

    def load_manifest(self, world_path: str | Path) -> WorldManifest:
        """Load and minimally parse a world's manifest.json file."""
        path = Path(world_path)
        manifest_path = path / "manifest.json"
        if not manifest_path.is_file():
            raise WorldValidationError(f"World package '{path.name}' is missing manifest.json")
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            raise WorldValidationError(
                f"World package '{path.name}' has invalid manifest.json: {err}"
            ) from err
        name = str(data.get("name") or path.name)
        return WorldManifest(name=name, path=manifest_path, data=data)

    def validate_runtime_package(self, world_path: str | Path) -> None:
        """Validate fatal gameplay assets without considering Builder workspace."""
        path = Path(world_path)
        missing: list[str] = []
        if not (path / "manifest.json").is_file():
            missing.append("manifest.json")
        for rel_path in RUNTIME_ASSET_DIRS:
            if not (path / rel_path).is_dir():
                missing.append(f"{rel_path}/")
        if missing:
            joined = ", ".join(missing)
            raise WorldValidationError(
                f"World package '{path.name}' is missing required runtime assets: {joined}"
            )

    def prepare_builder_workspace(self, world_path: str | Path) -> list[Path]:
        """Create non-fatal Builder workspace directories and empty .gitkeep files."""
        path = Path(world_path)
        created: list[Path] = []
        for rel_path in BUILDER_WORKSPACE_DIRS:
            directory = path / rel_path
            existed = directory.exists()
            directory.mkdir(parents=True, exist_ok=True)
            if not existed:
                created.append(directory)
                self.logger(f"[startup] Created Builder workspace directory: {rel_path}/")
            gitkeep = directory / ".gitkeep"
            if not existed and not any(directory.iterdir()) and not gitkeep.exists():
                gitkeep.touch()
        return created

    def load_world_assets(self, world_path: str | Path) -> dict[str, list[Path]]:
        """Load asset file paths for each runtime asset category.

        The registry intentionally records paths only; gameplay systems remain
        responsible for interpreting their data formats, preserving behavior.
        """
        path = Path(world_path)
        assets: dict[str, list[Path]] = {}
        for rel_path in RUNTIME_ASSET_DIRS:
            asset_dir = path / rel_path
            assets[rel_path] = sorted(child for child in asset_dir.iterdir() if child.is_file())
        return assets

    def load_world(self, world_path: str | Path) -> RegisteredWorld:
        """Load one world using the validated runtime/workspace lifecycle."""
        path = Path(world_path)
        self.logger("[startup] Loading world package:")
        self.logger(f"    {path.name}")
        manifest = self.load_manifest(path)
        self.logger("[startup] Validating runtime package...")
        self.validate_runtime_package(path)
        self.logger("    ✓ Runtime package valid")
        self.logger("[startup] Preparing builder workspace...")
        created = self.prepare_builder_workspace(path)
        if created:
            for directory in created:
                self.logger(f"    ✓ {directory.relative_to(path).as_posix()}/")
        else:
            self.logger("[startup] Builder workspace already prepared.")
        self.logger("[startup] Loading world assets...")
        assets = self.load_world_assets(path)
        for label in ("rooms", "npcs", "items", "quests", "rules"):
            self.logger(f"    ✓ {label.title()}")
        world = RegisteredWorld(
            name=manifest.name,
            path=path,
            manifest=manifest,
            assets=assets,
            created_workspace_dirs=created,
        )
        self.worlds[world.name] = world
        self.logger("[startup] World package loaded successfully.")
        return world

    def load_all_worlds(self, world_paths: Iterable[str | Path] | None = None) -> list[RegisteredWorld]:
        """Scan/load all installed worlds or a provided set of world directories."""
        paths = list(world_paths) if world_paths is not None else self.scan_installed_worlds()
        return [self.load_world(path) for path in paths]
