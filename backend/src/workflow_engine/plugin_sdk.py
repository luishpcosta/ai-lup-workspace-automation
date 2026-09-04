"""Public facade for plugin authors — the only import a plugin module needs.

    from workflow_engine.plugin_sdk import Plugin, PluginContext, TransientError

    class MyPlugin(Plugin):
        def run(self, context: PluginContext):
            ...

    PLUGIN = MyPlugin

Keeps plugin authors decoupled from the internal domain/application/adapters
package layout, which is free to change without breaking plugins.
"""

from workflow_engine.domain.exceptions import TransientError
from workflow_engine.domain.models import PluginContext, RetryPolicy
from workflow_engine.domain.ports import Plugin

__all__ = ["Plugin", "PluginContext", "RetryPolicy", "TransientError"]
