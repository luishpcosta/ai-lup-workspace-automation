"""CLI: `workflow run <config>` (ADR-001, AC-01/AC-02; RF-1..RF-7) and
`workflow run-many <config...>` (ADR-003, AC-01..AC-10; RF-1..RF-4).

This is the composition root: the only place that imports concrete adapters
and wires them into the application core.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from workflow_engine.adapters.filesystem_plugin_registry import FileSystemPluginRegistry
from workflow_engine.adapters.json_event_logger import JsonEventLogger
from workflow_engine.adapters.sqlite_state_store import SqliteStateStore
from workflow_engine.adapters.yaml_json_chain_loader import YamlJsonChainLoader
from workflow_engine.application.workflow_engine import WorkflowEngine
from workflow_engine.domain.exceptions import ChainValidationError, WorkflowFailed
from workflow_engine.domain.models import ChainDefinition


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="workflow")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run or resume a workflow from a chain config")
    run_parser.add_argument("config", help="Path to the chain config (.yaml/.yml/.json)")
    run_parser.add_argument(
        "--plugins-dir",
        default="./plugins",
        help="Directory to scan for plugins (default: ./plugins)",
    )
    run_parser.add_argument(
        "--db",
        default="./workflow_state.db",
        help="SQLite state file (default: ./workflow_state.db)",
    )
    run_parser.add_argument(
        "--correlation-keys",
        default="historia_id,branch,pr_number,pr_url",
        help=(
            "Comma-separated field names surfaced under a 'correlacao' log key "
            "when present in a step's params/input/output (ADR-002, RNF-1). "
            "Empty string disables correlation. Default: %(default)s"
        ),
    )

    run_many_parser = subparsers.add_parser(
        "run-many",
        help="Run multiple independent chain configs concurrently (ADR-003)",
    )
    run_many_parser.add_argument(
        "configs", nargs="+", help="Paths to chain configs to run concurrently"
    )
    run_many_parser.add_argument(
        "--plugins-dir",
        default="./plugins",
        help="Directory to scan for plugins (default: ./plugins)",
    )
    run_many_parser.add_argument(
        "--db-dir",
        default="./run-many-state",
        help="Directory for per-run SQLite state files, one per chain name (default: %(default)s)",
    )
    run_many_parser.add_argument(
        "--max-parallel",
        type=int,
        default=3,
        help="Maximum number of concurrent executions (default: 3)",
    )
    run_many_parser.add_argument(
        "--correlation-keys",
        default="historia_id,branch,pr_number,pr_url",
        help="Same as `run --correlation-keys` (ADR-002, RNF-1). Default: %(default)s",
    )

    serve_parser = subparsers.add_parser(
        "serve", help="Run an HTTP server to trigger and monitor workflows (ADR-004)"
    )
    serve_parser.add_argument(
        "--port", type=int, default=8000, help="Port to listen on (default: 8000)"
    )
    serve_parser.add_argument(
        "--plugins-dir",
        default="./plugins",
        help="Directory to scan for plugins (default: ./plugins)",
    )
    serve_parser.add_argument(
        "--watch-dir",
        default="./run-many-state",
        help=(
            "Directory of per-chain SQLite state files to trigger into and monitor "
            "(same convention as `run-many --db-dir`; default: %(default)s)"
        ),
    )
    serve_parser.add_argument(
        "--max-parallel",
        type=int,
        default=3,
        help="Maximum number of concurrent executions this server will run (default: 3)",
    )
    serve_parser.add_argument(
        "--correlation-keys",
        default="historia_id,branch,pr_number,pr_url",
        help="Same as `run --correlation-keys` (ADR-002, RNF-1). Default: %(default)s",
    )
    return parser


@dataclass
class BatchResult:
    """One line of the `run-many` summary (ADR-003, AC-08)."""

    config_path: str
    chain_name: str | None
    run_id: str | None
    status: str  # "completed" | "failed"
    error: str | None = None


def cmd_run(args: argparse.Namespace) -> int:
    registry = FileSystemPluginRegistry(args.plugins_dir)
    registry.discover()

    chain_loader = YamlJsonChainLoader()
    try:
        chain = chain_loader.load(args.config, known_plugins=registry.names())
    except ChainValidationError as exc:
        print(f"Invalid config: {exc}", file=sys.stderr)
        return 1

    correlation_keys = frozenset(
        key.strip() for key in args.correlation_keys.split(",") if key.strip()
    )

    with SqliteStateStore(args.db) as state_store:
        engine = WorkflowEngine(
            registry,
            state_store,
            event_logger=JsonEventLogger(),
            correlation_keys=correlation_keys,
        )
        try:
            run_id = engine.run(chain, args.config)
        except WorkflowFailed as exc:
            print(f"Workflow failed: {exc}", file=sys.stderr)
            return 1

    print(f"Workflow '{chain.name}' completed. run_id={run_id}")
    return 0


def cmd_run_many(args: argparse.Namespace) -> int:
    registry = FileSystemPluginRegistry(args.plugins_dir)
    registry.discover()

    chain_loader = YamlJsonChainLoader()
    correlation_keys = frozenset(
        key.strip() for key in args.correlation_keys.split(",") if key.strip()
    )

    results: list[BatchResult] = []
    loaded: list[tuple[str, ChainDefinition]] = []
    for config_path in args.configs:
        try:
            chain = chain_loader.load(config_path, known_plugins=registry.names())
        except ChainValidationError as exc:
            # An individual bad config doesn't block the rest of the batch (AC-03) —
            # it's just reported as an immediate failure, without consuming a pool slot.
            results.append(BatchResult(config_path, None, None, "failed", f"invalid config: {exc}"))
        else:
            loaded.append((config_path, chain))

    # Whole-batch gate (AC-02): a chain.name collision aborts everything, before any
    # execution starts — different from the per-config isolation above, because a
    # collision is ambiguous (which config "owns" <name>.db?), not an isolated defect.
    names_to_configs: dict[str, list[str]] = {}
    for config_path, chain in loaded:
        names_to_configs.setdefault(chain.name, []).append(config_path)
    collisions = {name: paths for name, paths in names_to_configs.items() if len(paths) > 1}
    if collisions:
        for name, paths in collisions.items():
            print(
                f"run-many: duplicate chain name '{name}' used by: {', '.join(paths)}",
                file=sys.stderr,
            )
        return 1

    db_dir = Path(args.db_dir)
    db_dir.mkdir(parents=True, exist_ok=True)

    def run_one(config_path: str, chain: ChainDefinition) -> BatchResult:
        db_path = db_dir / f"{chain.name}.db"
        with SqliteStateStore(db_path) as state_store:
            engine = WorkflowEngine(
                registry,
                state_store,
                event_logger=JsonEventLogger(),
                correlation_keys=correlation_keys,
            )
            try:
                run_id = engine.run(chain, config_path)
            except WorkflowFailed as exc:
                return BatchResult(config_path, chain.name, exc.run_id, "failed", str(exc))
        return BatchResult(config_path, chain.name, run_id, "completed")

    if loaded:
        with ThreadPoolExecutor(max_workers=args.max_parallel) as pool:
            futures: list[tuple[str, Future]] = [
                (config_path, pool.submit(run_one, config_path, chain))
                for config_path, chain in loaded
            ]
            # .result() here just controls collection order for a deterministic
            # summary — every job was already submitted above, so this doesn't
            # serialize the actual work (AC-10: one failing doesn't cancel the rest,
            # each future independently carries its own outcome).
            for _config_path, future in futures:
                results.append(future.result())

    print("Batch summary:")
    for result in results:
        if result.status == "completed":
            print(f"  [OK]     {result.chain_name} (run_id={result.run_id})")
        else:
            label = result.chain_name or result.config_path
            print(f"  [FAILED] {label}: {result.error}")

    completed = sum(1 for r in results if r.status == "completed")
    print(f"{completed}/{len(results)} completed.")
    return 0 if completed == len(results) else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "run-many":
        return cmd_run_many(args)
    if args.command == "serve":
        from workflow_engine.adapters.http_api import cmd_serve

        return cmd_serve(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
