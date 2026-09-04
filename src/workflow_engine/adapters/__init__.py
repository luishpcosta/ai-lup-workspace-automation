"""Adapters: concrete implementations of domain ports, plus the CLI composition root.

Driven adapters (infrastructure the hexagon talks out to): `sqlite_state_store`,
`filesystem_plugin_registry`, `yaml_json_chain_loader`, `json_event_logger`.
Driving adapter (translates the outside world into a call on the application
core): `cli`.
"""
