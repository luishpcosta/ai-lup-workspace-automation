import pytest

from workflow_engine.plugin_sdk import Plugin, PluginContext, TransientError


def test_plugin_is_abstract():
    with pytest.raises(TypeError):
        Plugin()  # cannot instantiate without implementing run()


def test_concrete_plugin_implements_run():
    class Concrete(Plugin):
        def run(self, context: PluginContext):
            return context.input

    ctx = PluginContext(input="x", params={}, run_id="r1", step_name="s1")
    assert Concrete().run(ctx) == "x"


def test_transient_error_is_exception():
    assert issubclass(TransientError, Exception)
