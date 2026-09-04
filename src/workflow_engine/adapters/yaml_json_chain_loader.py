"""YAML/JSON adapter for ChainLoaderPort (ADR-001, AC-03/AC-04; RF-1).

Also resolves the optional `vars:` block (ADR-002, AC-18/AC-19/AC-20; RF-5):
`{{ vars.<key> }}` inside a step's `params` is substituted before the step
reaches the Engine. This is purely a Chain Loader concern — plugins never see
`vars:` and the `Plugin.run(context) -> output` contract is unchanged.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml

from workflow_engine.domain.exceptions import ChainValidationError
from workflow_engine.domain.models import ChainDefinition, RetryPolicy, StepDefinition
from workflow_engine.domain.ports import ChainLoaderPort

#: Matches `{{ vars.<key> }}` only — a bare `{{ summary }}` (no `vars.` prefix) is left
#: untouched, since that syntax is resolved later, by a plugin, from `context.input`.
_VARS_REF = re.compile(r"\{\{\s*vars\.(\w+)\s*\}\}")


class YamlJsonChainLoader(ChainLoaderPort):
    """Loads a chain definition from a `.yaml`/`.yml`/`.json` file."""

    def load(self, source: str, known_plugins: set[str] | None = None) -> ChainDefinition:
        """Load and validate a chain definition file.

        If `known_plugins` is given, every step's `plugin` must be a member of
        it — otherwise raises ChainValidationError naming the missing plugin
        (AC-04), before any step runs.
        """
        path = Path(source)
        raw = self._read_raw(path)
        if not isinstance(raw, dict):
            raise ChainValidationError(f"{path}: top-level config must be a mapping")

        name = raw.get("name")
        if not name or not isinstance(name, str):
            raise ChainValidationError(f"{path}: 'name' is required and must be a string")

        raw_vars = raw.get("vars") or {}
        if not isinstance(raw_vars, dict):
            raise ChainValidationError(f"{path}: 'vars' must be a mapping")

        raw_steps = raw.get("steps")
        if not isinstance(raw_steps, list) or not raw_steps:
            raise ChainValidationError(f"{path}: 'steps' must be a non-empty list")

        steps: list[StepDefinition] = []
        seen_names: set[str] = set()
        for i, raw_step in enumerate(raw_steps):
            if not isinstance(raw_step, dict):
                raise ChainValidationError(f"{path}: step #{i} must be a mapping")

            step_name = raw_step.get("name")
            if not step_name or not isinstance(step_name, str):
                raise ChainValidationError(f"{path}: step #{i} is missing a valid 'name'")
            if step_name in seen_names:
                raise ChainValidationError(f"{path}: duplicate step name '{step_name}'")
            seen_names.add(step_name)

            plugin_name = raw_step.get("plugin")
            if not plugin_name or not isinstance(plugin_name, str):
                raise ChainValidationError(
                    f"{path}: step '{step_name}' is missing a valid 'plugin'"
                )
            if known_plugins is not None and plugin_name not in known_plugins:
                raise ChainValidationError(
                    f"{path}: step '{step_name}' references unknown plugin '{plugin_name}'"
                )

            params = self._resolve_vars(raw_step.get("params") or {}, raw_vars, step_name, path)

            steps.append(
                StepDefinition(
                    name=step_name,
                    plugin=plugin_name,
                    params=params,
                    usa_output_anterior=bool(raw_step.get("usa_output_anterior", False)),
                    retry_policy=self._parse_retry(raw_step.get("retry"), step_name),
                )
            )

        return ChainDefinition(name=name, steps=tuple(steps))

    def _resolve_vars(self, value: Any, raw_vars: dict, step_name: str, path: Path) -> Any:
        """Recursively substitute `{{ vars.<key> }}` inside str/list/dict values.

        Raises ChainValidationError, naming the missing key, if a referenced
        key isn't present in the `vars:` block (AC-20) — this runs during
        `load()`, before any step executes.
        """
        if isinstance(value, str):

            def _sub(match: re.Match[str]) -> str:
                key = match.group(1)
                if key not in raw_vars:
                    raise ChainValidationError(
                        f"{path}: step '{step_name}' references unknown vars key '{key}'"
                    )
                return str(raw_vars[key])

            return _VARS_REF.sub(_sub, value)
        if isinstance(value, list):
            return [self._resolve_vars(item, raw_vars, step_name, path) for item in value]
        if isinstance(value, dict):
            return {
                key: self._resolve_vars(item, raw_vars, step_name, path)
                for key, item in value.items()
            }
        return value

    def _read_raw(self, path: Path) -> Any:
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() in (".yaml", ".yml"):
            return yaml.safe_load(text)
        if path.suffix.lower() == ".json":
            return json.loads(text)
        raise ChainValidationError(
            f"Unsupported config extension: {path.suffix} (use .yaml, .yml or .json)"
        )

    def _parse_retry(self, raw: dict | None, step_name: str) -> RetryPolicy | None:
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise ChainValidationError(f"Step '{step_name}': 'retry' must be a mapping")
        return RetryPolicy(
            max_attempts=int(raw.get("max_attempts", 3)),
            initial_delay=float(raw.get("initial_delay", 1.0)),
            multiplier=float(raw.get("multiplier", 2.0)),
        )
