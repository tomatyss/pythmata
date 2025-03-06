"""Plugin discovery and management for Pythmata.

This module provides functionality for discovering and loading plugins
that can extend Pythmata with custom service tasks.
"""

import importlib
import importlib.util
import os
import sys

from pythmata.utils.logger import get_logger

logger = get_logger(__name__)


def discover_plugins(plugin_dir: str) -> None:
    """
    Discover and import plugins from the specified directory.

    This function scans the given directory for Python packages (directories
    containing __init__.py files) and imports them. Each plugin package is
    expected to register its service tasks in its __init__.py file.

    Args:
        plugin_dir: Directory containing plugin packages
    """
    if not os.path.isdir(plugin_dir):
        logger.warning(f"Plugin directory not found: {plugin_dir}")
        return

    logger.info(f"Discovering plugins in {plugin_dir}")

    # Add plugin directory to Python path if not already there
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    # Find plugin packages (directories with __init__.py)
    for item in os.listdir(plugin_dir):
        item_path = os.path.join(plugin_dir, item)
        init_file = os.path.join(item_path, "__init__.py")

        if os.path.isdir(item_path) and os.path.isfile(init_file):
            try:
                # Import the plugin package
                logger.info(f"Importing plugin: {item}")
                importlib.import_module(item)
                logger.info(f"Successfully loaded plugin: {item}")
            except Exception as e:
                logger.error(f"Error loading plugin {item}: {e}", exc_info=True)
