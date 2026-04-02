#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


def _load_skill_sync_api() -> tuple[
    str,
    Callable[[Any], str],
    Callable[..., Any],
    Callable[..., Any],
]:
    from rl_developer_memory.skill_bundle_sync import (  # pylint: disable=import-outside-toplevel
        PLUGIN_NAME,
        report_as_json,
        resolve_surface_paths,
        sync_global_skill_surfaces,
    )

    return PLUGIN_NAME, report_as_json, resolve_surface_paths, sync_global_skill_surfaces


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install or sync the repo's canonical RL skill bundle into global surfaces.")
    parser.add_argument("--mode", choices=("copy", "symlink", "generated"), default="copy")
    parser.add_argument("--codex-home", default=None, help="Optional override for the global Codex home. Defaults to CODEX_HOME or ~/.codex.")
    parser.add_argument("--agents-home", default=None, help="Optional override for the global agents bridge home. Defaults to AGENTS_HOME or ~/.agents.")
    parser.add_argument("--dry-run", action="store_true", help="Resolve and print target surfaces without writing files.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    repo_root = REPO_ROOT
    plugin_name, report_as_json, resolve_surface_paths, sync_global_skill_surfaces = _load_skill_sync_api()
    if args.dry_run:
        surfaces = resolve_surface_paths(codex_home=args.codex_home, agents_home=args.agents_home)
        payload = {
            "mode": args.mode,
            "plugin_name": plugin_name,
            "repo_root": str(repo_root),
            "codex_home": str(surfaces.codex_home),
            "agents_home": str(surfaces.agents_home),
            "codex_target": str(surfaces.codex_plugin_root),
            "agents_target": str(surfaces.agents_plugins_root),
            "marketplace_json": str(surfaces.agents_marketplace_json),
            "live_runtime_authority": "~/.codex/config.toml",
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            for key, value in payload.items():
                print(f"{key}: {value}")
        return

    report = sync_global_skill_surfaces(
        repo_root,
        mode=args.mode,
        codex_home=args.codex_home,
        agents_home=args.agents_home,
    )
    if args.json:
        print(report_as_json(report), end="")
        return

    print(f"plugin_name: {report.plugin_name}")
    print(f"mode: {report.mode}")
    print(f"codex_home: {report.codex_home}")
    print(f"agents_home: {report.agents_home}")
    print(f"codex_target: {report.codex_target}")
    print(f"agents_target: {report.agents_target}")
    print(f"marketplace_json: {report.marketplace_json}")
    print(f"marketplace_updated: {report.marketplace_updated}")
    print(f"copied_entries: {len(report.copied_entries)}")
    print(f"generated_files: {len(report.generated_files)}")


if __name__ == "__main__":
    main()
