from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping

PLUGIN_NAME = "rl-developer-memory"
DEFAULT_CODEX_DIRNAME = ".codex"
DEFAULT_AGENTS_DIRNAME = ".agents"
MARKETPLACE_RELATIVE_PLUGIN_ROOT = Path("plugins")
CANONICAL_BUNDLE_PATHS = (
    ".codex-plugin",
    ".mcp.json",
    "AGENTS.md",
    "README.md",
    "docs/CODEX_MAIN_CONVERSATION_OWNERSHIP.md",
    "docs/CODEX_RL_AGENT_OPERATING_MODEL.md",
    "docs/MCP_RL_INTEGRATION_POLICY.md",
    "docs/MEMORY_SCOPE_OPERATIONS_NOTE.md",
    "docs/RL_BACKBONE.md",
    "docs/RL_CODING_STANDARDS.md",
    "docs/RL_QUALITY_GATE.md",
    "docs/SKILL_INSTALL_SYNC.md",
    "docs/VALIDATION_MATRIX.md",
    "docs/theory_to_code.md",
    "skills",
)
GENERATED_BUNDLE_PATHS = (
    ".codex-plugin",
    ".mcp.json",
    "AGENTS.md",
    "docs/MCP_RL_INTEGRATION_POLICY.md",
    "docs/MEMORY_SCOPE_OPERATIONS_NOTE.md",
    "docs/RL_CODING_STANDARDS.md",
    "docs/RL_QUALITY_GATE.md",
    "docs/SKILL_INSTALL_SYNC.md",
    "skills",
)


@dataclass(frozen=True, slots=True)
class SurfacePaths:
    """Resolved global integration surfaces for Codex and marketplace bridges."""

    home: Path
    codex_home: Path
    agents_home: Path
    codex_plugin_root: Path
    agents_plugins_root: Path
    agents_marketplace_json: Path


@dataclass(frozen=True, slots=True)
class SyncReport:
    """Structured result for one install/sync operation."""

    mode: str
    plugin_name: str
    codex_home: str
    agents_home: str
    codex_target: str
    agents_target: str
    marketplace_json: str
    copied_entries: list[str]
    generated_files: list[str]
    marketplace_updated: bool


def _resolve_home(env: Mapping[str, str] | None = None) -> Path:
    env_map = env or os.environ
    home = env_map.get("HOME")
    if home:
        return Path(home).expanduser().resolve()
    return Path.home().expanduser().resolve()


def resolve_surface_paths(
    *,
    codex_home: str | Path | None = None,
    agents_home: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> SurfacePaths:
    """Resolve portable global targets without hardcoding machine-specific usernames."""

    env_map = env or os.environ
    home = _resolve_home(env_map)
    resolved_codex = Path(codex_home or env_map.get("CODEX_HOME") or (home / DEFAULT_CODEX_DIRNAME)).expanduser().resolve()
    resolved_agents = Path(
        agents_home or env_map.get("AGENTS_HOME") or (home / DEFAULT_AGENTS_DIRNAME)
    ).expanduser().resolve()
    return SurfacePaths(
        home=home,
        codex_home=resolved_codex,
        agents_home=resolved_agents,
        codex_plugin_root=resolved_codex / "local-plugins" / PLUGIN_NAME,
        agents_plugins_root=resolved_agents / "plugins" / "plugins" / PLUGIN_NAME,
        agents_marketplace_json=resolved_agents / "plugins" / "marketplace.json",
    )


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _safe_replace_dir(target: Path) -> None:
    if target.is_symlink() or target.is_file():
        target.unlink()
        return
    if target.exists():
        shutil.rmtree(target)


def _copy_entry(src: Path, dest: Path) -> list[str]:
    copied: list[str] = []
    _ensure_parent(dest)
    if src.is_dir():
        shutil.copytree(src, dest, dirs_exist_ok=True)
        copied.append(str(dest))
    else:
        shutil.copy2(src, dest)
        copied.append(str(dest))
    return copied


def _copy_bundle(repo_root: Path, target_root: Path, entries: Iterable[str]) -> list[str]:
    copied: list[str] = []
    target_root.mkdir(parents=True, exist_ok=True)
    for rel_path in entries:
        src = repo_root / rel_path
        if not src.exists():
            continue
        dest = target_root / rel_path
        copied.extend(_copy_entry(src, dest))
    return copied


def _write_generated_readme(target_root: Path, plugin_name: str) -> list[str]:
    readme_path = target_root / "README.md"
    readme_path.write_text(
        "\n".join(
            [
                f"# {plugin_name} generated plugin bundle",
                "",
                "This bundle was generated from the repository canonical skill sources.",
                "",
                "Runtime authority remains the live Codex config under `~/.codex/config.toml`.",
                "This bundle is only a discovery/install surface for skills and plugin metadata.",
                "",
                "Prefer re-running `python scripts/install_skill.py --mode copy` from the repository",
                "when you need to refresh the global plugin copy.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    manifest_path = target_root / ".codex-plugin" / "install-manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "plugin_name": plugin_name,
                "mode": "generated",
                "canonical_bundle_paths": list(GENERATED_BUNDLE_PATHS),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return [str(readme_path), str(manifest_path)]


def _relative_symlink(target_root: Path, source_root: Path) -> list[str]:
    _ensure_parent(target_root)
    _safe_replace_dir(target_root)
    relative_source = Path(os.path.relpath(source_root, start=target_root.parent))
    target_root.symlink_to(relative_source, target_is_directory=True)
    return [str(target_root)]


def _sync_target(repo_root: Path, target_root: Path, *, mode: str) -> tuple[list[str], list[str]]:
    copied: list[str] = []
    generated: list[str] = []
    if mode == "symlink":
        copied.extend(_relative_symlink(target_root, repo_root))
        return copied, generated

    _safe_replace_dir(target_root)
    bundle_paths = CANONICAL_BUNDLE_PATHS if mode == "copy" else GENERATED_BUNDLE_PATHS
    copied.extend(_copy_bundle(repo_root, target_root, bundle_paths))
    if mode == "generated":
        generated.extend(_write_generated_readme(target_root, PLUGIN_NAME))
    return copied, generated


def ensure_marketplace_entry(
    marketplace_path: Path,
    *,
    plugin_name: str = PLUGIN_NAME,
    category: str = "Productivity",
) -> bool:
    """Ensure the marketplace manifest exposes the plugin with a portable relative path."""

    marketplace_path.parent.mkdir(parents=True, exist_ok=True)
    if marketplace_path.exists():
        payload = json.loads(marketplace_path.read_text(encoding="utf-8"))
    else:
        payload = {
            "name": "local-plugins",
            "interface": {"displayName": "Local Codex Plugins"},
            "plugins": [],
        }

    plugins = payload.setdefault("plugins", [])
    expected = {
        "name": plugin_name,
        "source": {"source": "local", "path": f"./plugins/{plugin_name}"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": category,
    }

    updated = False
    for index, item in enumerate(plugins):
        if item.get("name") == plugin_name:
            if item != expected:
                plugins[index] = expected
                updated = True
            break
    else:
        plugins.append(expected)
        updated = True

    if updated:
        marketplace_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return updated


def sync_global_skill_surfaces(
    repo_root: Path,
    *,
    mode: str = "copy",
    codex_home: str | Path | None = None,
    agents_home: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> SyncReport:
    """Install or sync the canonical repo skill bundle into global discovery surfaces."""

    if mode not in {"copy", "symlink", "generated"}:
        raise ValueError(f"Unsupported sync mode: {mode}")

    surfaces = resolve_surface_paths(codex_home=codex_home, agents_home=agents_home, env=env)
    surfaces.codex_plugin_root.parent.mkdir(parents=True, exist_ok=True)
    surfaces.agents_plugins_root.parent.mkdir(parents=True, exist_ok=True)

    codex_copied, codex_generated = _sync_target(repo_root, surfaces.codex_plugin_root, mode=mode)
    agents_copied, agents_generated = _sync_target(repo_root, surfaces.agents_plugins_root, mode=mode)
    marketplace_updated = ensure_marketplace_entry(surfaces.agents_marketplace_json)

    return SyncReport(
        mode=mode,
        plugin_name=PLUGIN_NAME,
        codex_home=str(surfaces.codex_home),
        agents_home=str(surfaces.agents_home),
        codex_target=str(surfaces.codex_plugin_root),
        agents_target=str(surfaces.agents_plugins_root),
        marketplace_json=str(surfaces.agents_marketplace_json),
        copied_entries=sorted(codex_copied + agents_copied),
        generated_files=sorted(codex_generated + agents_generated),
        marketplace_updated=marketplace_updated,
    )


def report_as_json(report: SyncReport) -> str:
    """Serialize the sync result with portable fields only."""

    return json.dumps(asdict(report), indent=2) + "\n"
