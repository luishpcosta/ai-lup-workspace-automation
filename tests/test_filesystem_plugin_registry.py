import pytest

from tests.conftest import (
    BROKEN_MODULE_SOURCE,
    ECHO_PLUGIN_SOURCE,
    INVALID_PLUGIN_SOURCE,
    write_plugin,
)
from workflow_engine.adapters.filesystem_plugin_registry import FileSystemPluginRegistry
from workflow_engine.domain.exceptions import PluginNotFoundError


def test_discovers_valid_plugin_ac06(plugins_dir):
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)

    registry = FileSystemPluginRegistry(plugins_dir)
    discovered = registry.discover()

    assert "echo" in discovered
    assert registry.names() == {"echo"}


def test_missing_plugin_raises(plugins_dir):
    registry = FileSystemPluginRegistry(plugins_dir)
    registry.discover()
    with pytest.raises(PluginNotFoundError):
        registry.get("nope")


def test_invalid_module_is_skipped_without_breaking_others_ac07(plugins_dir):
    write_plugin(plugins_dir, "echo.py", ECHO_PLUGIN_SOURCE)
    write_plugin(plugins_dir, "invalid.py", INVALID_PLUGIN_SOURCE)
    write_plugin(plugins_dir, "broken.py", BROKEN_MODULE_SOURCE)

    registry = FileSystemPluginRegistry(plugins_dir)
    discovered = registry.discover()

    assert registry.names() == {"echo"}
    assert "invalid" not in discovered
    assert "broken" not in discovered


def test_empty_plugins_dir_returns_no_plugins(plugins_dir):
    registry = FileSystemPluginRegistry(plugins_dir)
    assert registry.discover() == {}


def test_missing_plugins_dir_does_not_raise(tmp_path):
    registry = FileSystemPluginRegistry(tmp_path / "does-not-exist")
    assert registry.discover() == {}
