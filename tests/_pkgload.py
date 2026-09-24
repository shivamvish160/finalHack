"""Test helper: import a service's `app` package under a unique alias.

Services under `services/<name>-service/app/` use hyphenated directory
names (matching their deployed Cloud Run service name) but each has its
own local `app` Python package. Two services' `app` packages can't both be
imported as literal `app` in the same pytest session without colliding, so
this loads each one under a unique registered name (e.g. `api_gateway_app`)
while preserving normal relative-import semantics (`from .auth import X`)
inside the loaded package, by giving it real package `__path__` search
locations.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_package(unique_name: str, relative_package_dir: str) -> ModuleType:
    """Register REPO_ROOT/relative_package_dir as a package under `unique_name`.

    Returns the package module. Submodules can then be imported normally via
    `importlib.import_module(f"{unique_name}.submodule")`.
    """
    if unique_name in sys.modules:
        return sys.modules[unique_name]

    package_dir = REPO_ROOT / relative_package_dir
    init_file = package_dir / "__init__.py"
    spec = importlib.util.spec_from_file_location(
        unique_name, init_file, submodule_search_locations=[str(package_dir)]
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load package spec for {package_dir}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module
    spec.loader.exec_module(module)
    return module


def load_submodule(unique_pkg_name: str, relative_package_dir: str, submodule: str) -> ModuleType:
    """Convenience: load the package, then import one of its submodules by dotted name."""
    load_package(unique_pkg_name, relative_package_dir)
    return importlib.import_module(f"{unique_pkg_name}.{submodule}")

