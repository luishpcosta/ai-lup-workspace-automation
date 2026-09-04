import pytest


@pytest.fixture
def plugins_dir(tmp_path):
    d = tmp_path / "plugins"
    d.mkdir()
    return d


def write_plugin(plugins_dir, filename, source: str) -> None:
    (plugins_dir / filename).write_text(source, encoding="utf-8")


ECHO_PLUGIN_SOURCE = """
from workflow_engine.plugin_sdk import Plugin, PluginContext


class EchoPlugin(Plugin):
    def run(self, context: PluginContext):
        return {"echo": context.input, "params": context.params}


PLUGIN = EchoPlugin
"""

FAILING_ONCE_PLUGIN_SOURCE = """
from workflow_engine.plugin_sdk import Plugin, PluginContext, TransientError

_calls = {"count": 0}


class FailOnceThenSucceed(Plugin):
    def run(self, context: PluginContext):
        _calls["count"] += 1
        if _calls["count"] < 2:
            raise TransientError("temporary glitch")
        return "ok"


PLUGIN = FailOnceThenSucceed
"""

ALWAYS_FAILS_PLUGIN_SOURCE = """
from workflow_engine.plugin_sdk import Plugin, PluginContext


class AlwaysFails(Plugin):
    def run(self, context: PluginContext):
        raise ValueError("permanent boom")


PLUGIN = AlwaysFails
"""

INVALID_PLUGIN_SOURCE = """
class NotAPlugin:
    pass


PLUGIN = NotAPlugin
"""

BROKEN_MODULE_SOURCE = """
raise RuntimeError("this module explodes on import")
"""
