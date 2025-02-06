"""Tests to prevent circular imports in the codebase."""

import importlib
import os
import pkgutil
import sys
import warnings
from typing import List

import pytest


def get_all_modules(package_path: str, package_name: str) -> List[str]:
    """Get all module paths in a package recursively."""
    modules = []
    for module_info in pkgutil.walk_packages([package_path], prefix=f"{package_name}."):
        if not module_info.ispkg:  # Only include actual modules, not packages
            modules.append(module_info.name)
    return modules


def test_no_circular_imports():
    """Test that there are no circular imports in the codebase."""
    # Get the path to the pythmata package
    package_path = os.path.join(os.path.dirname(__file__), "../../src/pythmata")
    package_name = "pythmata"

    # Get all module paths
    modules = get_all_modules(package_path, package_name)

    # Capture warnings during imports to analyze their source
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # Try importing each module
        for module_path in modules:
            try:
                # Clear the module from sys.modules if it was previously imported
                if module_path in sys.modules:
                    del sys.modules[module_path]

                # Attempt to import the module
                importlib.import_module(module_path)
            except ImportError as e:
                if "circular import" in str(e).lower():
                    pytest.fail(
                        f"Circular import detected in module {module_path}: {str(e)}"
                    )
                else:
                    # Re-raise other import errors
                    raise

        # Check if any warnings came from our own code
        for warning in w:
            if warning.category == DeprecationWarning and "pythmata" in str(
                warning.filename
            ):
                pytest.fail(
                    f"Deprecation warning from our code: {warning.message} in {warning.filename}"
                )
