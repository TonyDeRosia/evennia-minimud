"""Prototype package."""

# Load the legacy ``world/prototypes.py`` module and re-export all of its
# public attributes so that ``import world.prototypes`` continues to work
# as before while still allowing submodules like ``world.prototypes.rooms``
# to exist.
from importlib.util import spec_from_file_location, module_from_spec
from pathlib import Path

_legacy_path = (Path(__file__).resolve().parent.parent / "prototypes.py")
spec = spec_from_file_location("world._legacy_prototypes", _legacy_path)
_legacy = module_from_spec(spec)
spec.loader.exec_module(_legacy)

if hasattr(_legacy, "_normalize_proto"):
    _normalize_proto = _legacy._normalize_proto

for _name in [n for n in dir(_legacy) if not n.startswith("_")]:
    globals()[_name] = getattr(_legacy, _name)

__all__ = [n for n in globals() if not n.startswith("_")]
if "_normalize_proto" in globals():
    __all__.append("_normalize_proto")
