"""Filesystem adapter for PluginRegistryPort (ADR-001, AC-06/AC-07; RF-3)."""

from __future__ import annotations

import importlib.util
import inspect
import logging
from pathlib import Path

from workflow_engine.domain.exceptions import PluginNotFoundError
from workflow_engine.domain.ports import Plugin, PluginRegistryPort

logger = logging.getLogger("workflow_engine.plugin_registry")


class FileSystemPluginRegistry(PluginRegistryPort):
    """Discovers plugins from a directory and validates them against the Plugin contract.

    Convention: each `*.py` file in the directory (excluding files starting with
    `_`) is a candidate module. It must expose a module-level `PLUGIN` attribute
    that is a class implementing `workflow_engine.domain.ports.Plugin`. The
    plugin's name is `PLUGIN_NAME` if the module defines one, else the filename
    stem. A module that doesn't satisfy the contract is skipped with a warning —
    it never prevents other valid plugins from loading.
    """

    def __init__(self, plugins_dir: str | Path):
        self._plugins_dir = Path(plugins_dir)
        self._plugins: dict[str, Plugin] = {}

    def discover(self) -> dict[str, Plugin]:
        self._plugins = {}
        if not self._plugins_dir.exists():
            return self._plugins

        for path in sorted(self._plugins_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            self._load_module(path)
        return dict(self._plugins)

    def _load_module(self, path: Path) -> None:
        module_name = f"workflow_engine_plugins.{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            logger.warning("plugin_load_failed path=%s reason=cannot_create_spec", path)
            return
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # noqa: BLE001 - a broken plugin must not break discovery
            logger.warning("plugin_load_failed path=%s reason=%s", path, exc)
            return

        plugin_cls = getattr(module, "PLUGIN", None)
        if not (inspect.isclass(plugin_cls) and issubclass(plugin_cls, Plugin)):
            logger.warning(
                "plugin_rejected path=%s reason=missing_or_invalid_PLUGIN_attribute", path
            )
            return

        name = getattr(module, "PLUGIN_NAME", path.stem)
        self._plugins[name] = plugin_cls()

    def get(self, name: str) -> Plugin:
        try:
            return self._plugins[name]
        except KeyError:
            raise PluginNotFoundError(name) from None

    def names(self) -> set[str]:
        return set(self._plugins.keys())
