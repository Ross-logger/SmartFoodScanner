"""
Run automatically in interactive Python when PYTHONSTARTUP points here.

Recursively imports every submodule under backend.services and binds each
module object on __main__ as <path_with_underscores> (relative to
backend.services), e.g. ocr_service, ingredients_extraction_hf_section_detection.
Also sets ``services`` -> the ``backend.services`` package.

  export PYTHONPATH="/path/to/SmartFoodScanner"
  export PYTHONSTARTUP="/path/to/SmartFoodScanner/scripts/python_startup_services.py"

Then: python3   (or use: make shell)
"""
from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_root_s = str(_PROJECT_ROOT)
if _root_s not in sys.path:
    sys.path.insert(0, _root_s)

_failed: list[tuple[str, str]] = []
_total = 0

try:
    import backend.services as _svc_pkg
except Exception as exc:  # pragma: no cover - misconfigured env
    print(f"[python_startup_services] Cannot import backend.services: {exc}", file=sys.stderr)
else:
    _main = sys.modules["__main__"]
    _main.services = _svc_pkg

    for _finder, _modname, _ispkg in pkgutil.walk_packages(
        _svc_pkg.__path__, _svc_pkg.__name__ + "."
    ):
        _total += 1
        try:
            importlib.import_module(_modname)
        except Exception as exc:
            _failed.append((_modname, f"{type(exc).__name__}: {exc}"))

    _ok = _total - len(_failed)
    print(
        f"[python_startup_services] Loaded backend.services ({_ok}/{_total} modules"
        + (f", {len(_failed)} skipped" if _failed else "")
        + ").",
        file=sys.stderr,
    )
    for _name, _err in _failed:
        print(f"  skip {_name}: {_err}", file=sys.stderr)

    _failed_set = {n for n, _ in _failed}
    _dot_prefix = _svc_pkg.__name__ + "."
    _aliases = 0
    for _finder, _modname, _ispkg in pkgutil.walk_packages(
        _svc_pkg.__path__, _svc_pkg.__name__ + "."
    ):
        if _modname in _failed_set:
            continue
        mod = sys.modules.get(_modname)
        if mod is None:
            continue
        rel = _modname.removeprefix(_dot_prefix)
        if not rel:
            continue
        attr = rel.replace(".", "_")
        existing = getattr(_main, attr, None)
        if existing is not None and existing is not mod:
            attr = _modname.replace(".", "_")
        setattr(_main, attr, mod)
        _aliases += 1

    _hf_sd = getattr(_main, "ingredients_extraction_hf_section_detection", None)
    if _hf_sd is not None:
        _main.hf_section_detection = _hf_sd
        _main._get_pipeline = _hf_sd._get_pipeline
        _main.extract_ingredients_list_hf = _hf_sd.extract_ingredients_list_hf

    print(
        f"[python_startup_services] Bound {_aliases} service modules on __main__ "
        f"(_get_pipeline, hf_section_detection, services.<subpkg>, …).",
        file=sys.stderr,
    )
