"""Filesystem adapter for WorkflowTemplateRegistryPort (ADR-007, AT-01).

Mirrors `filesystem_plugin_registry.py`'s discovery convention: each `*.yaml`/
`*.yml` file in the templates directory is a candidate. A template file is,
deliberately, also a valid chain config (`name`/`steps`, optionally `vars`) —
`YamlJsonChainLoader.load()` can load it unmodified, ignoring the extra
`id`/`label`/`description`/`params_schema` keys. A malformed template is
skipped with a warning — it never prevents other valid templates from loading.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from workflow_engine.domain.exceptions import WorkflowTemplateNotFoundError
from workflow_engine.domain.models import WorkflowTemplateDefinition, WorkflowTemplateParam
from workflow_engine.domain.ports import WorkflowTemplateRegistryPort

logger = logging.getLogger("workflow_engine.workflow_template_registry")


class FileSystemWorkflowTemplateRegistry(WorkflowTemplateRegistryPort):
    def __init__(self, templates_dir: str | Path):
        self._templates_dir = Path(templates_dir)
        self._templates: dict[str, WorkflowTemplateDefinition] = {}

    def discover(self) -> dict[str, WorkflowTemplateDefinition]:
        self._templates = {}
        if not self._templates_dir.exists():
            return self._templates

        paths = sorted(self._templates_dir.glob("*.yaml")) + sorted(
            self._templates_dir.glob("*.yml")
        )
        for path in paths:
            self._load_file(path)
        return dict(self._templates)

    def _load_file(self, path: Path) -> None:
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            logger.warning("workflow_template_load_failed path=%s reason=%s", path, exc)
            return
        if not isinstance(raw, dict):
            logger.warning("workflow_template_rejected path=%s reason=not_a_mapping", path)
            return

        template_id = raw.get("id")
        label = raw.get("label")
        description = raw.get("description")
        raw_params = raw.get("params_schema") or []
        if not isinstance(template_id, str) or not template_id:
            logger.warning("workflow_template_rejected path=%s reason=missing_id", path)
            return
        if not isinstance(label, str) or not label:
            logger.warning("workflow_template_rejected path=%s reason=missing_label", path)
            return
        if not isinstance(description, str):
            logger.warning("workflow_template_rejected path=%s reason=missing_description", path)
            return
        if not isinstance(raw_params, list):
            logger.warning("workflow_template_rejected path=%s reason=invalid_params_schema", path)
            return
        if not isinstance(raw.get("name"), str) or not raw.get("name"):
            logger.warning("workflow_template_rejected path=%s reason=missing_chain_name", path)
            return
        if not isinstance(raw.get("steps"), list) or not raw.get("steps"):
            logger.warning("workflow_template_rejected path=%s reason=missing_chain_steps", path)
            return

        try:
            params = tuple(self._parse_param(p) for p in raw_params)
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("workflow_template_rejected path=%s reason=%s", path, exc)
            return

        self._templates[template_id] = WorkflowTemplateDefinition(
            id=template_id,
            label=label,
            description=description,
            params=params,
            raw=raw,
        )

    def _parse_param(self, raw: dict) -> WorkflowTemplateParam:
        return WorkflowTemplateParam(
            name=raw["name"],
            label=raw.get("label", raw["name"]),
            type=raw.get("type", "text"),
            required=bool(raw.get("required", False)),
            source=raw.get("source"),
        )

    def get(self, template_id: str) -> WorkflowTemplateDefinition:
        try:
            return self._templates[template_id]
        except KeyError:
            raise WorkflowTemplateNotFoundError(template_id) from None

    def list(self) -> list[WorkflowTemplateDefinition]:
        return list(self._templates.values())
