"""Pure application logic for workflow templates (ADR-007, AT-02).

No infrastructure imports — only `domain` models. The driving adapter
(`adapters/http_api.py`) is responsible for turning `materialize_chain_raw`'s
output into an actual file on disk and handing it to the existing
`ChainLoaderPort`/`ServerState.trigger` path.
"""

from __future__ import annotations

from workflow_engine.domain.models import WorkflowTemplateDefinition


def validate_params(template: WorkflowTemplateDefinition, submitted: dict) -> list[str]:
    """Returns a list of human-readable errors; empty means the submission is
    valid against `template.params_schema` (only `required` is enforced —
    type/source are UI rendering hints, not validated server-side).
    """
    return [
        f"missing required param: {param.name}"
        for param in template.params
        if param.required and not submitted.get(param.name)
    ]


def materialize_chain_raw(
    template: WorkflowTemplateDefinition, submitted: dict, chain_name: str
) -> dict:
    """Builds the raw chain config (dict) for one run of `template`, ready to be
    serialized to YAML and loaded by `YamlJsonChainLoader` unmodified. Renames
    the chain (`chain_name` is unique per submission — see
    `ServerState.trigger_from_template`) and merges submitted params into
    `vars:`, so `{{ vars.<key> }}` inside the template's `steps:` resolves
    against what the user actually submitted.

    Every param declared in `template.params` gets an empty-string default
    first: an optional param the user left blank must still resolve (as `""`,
    falsy the same way an omitted param would be to a plugin's `params.get(...)`)
    instead of failing the Chain Loader's "unknown vars key" validation, which
    runs before any step executes.
    """
    raw = dict(template.raw)
    raw["name"] = chain_name
    defaults = {param.name: "" for param in template.params}
    raw["vars"] = {**defaults, **(raw.get("vars") or {}), **submitted}
    return raw
